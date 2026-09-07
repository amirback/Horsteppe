"""Pipeline orchestrator: script -> TTS -> images -> video -> render -> upload.

Order matters: TTS runs before visuals so each scene's real narration length
drives its segment duration (audio/video sync). Every scene step is resumable:
completed assets are skipped on retry, so a failure at scene 4 never re-pays
providers for scenes 1-3.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import httpx

import media
from config import TMP_DIR, Config
from db import Db
from steps import image_step, render_step, script_step, tts_step, video_step

log = logging.getLogger("worker.pipeline")


def _download(url: str, dest: Path) -> Path:
    if not dest.exists():
        with httpx.Client(timeout=120) as client:
            resp = client.get(url)
            resp.raise_for_status()
        dest.write_bytes(resp.content)
    return dest


def run_project(cfg: Config, db: Db, project_id: str) -> None:
    project = db.get_project(project_id)
    work_dir = TMP_DIR / project_id
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ---- 1. Script (skipped if scenes already exist from a previous attempt)
        scenes = db.get_scenes(project_id)
        if not scenes:
            db.set_progress(project_id, "Пишем сценарий…")
            script = script_step.generate_script(
                cfg, project["topic"], project["style"], project["duration_sec"]
            )
            db.log_cost(project_id, "script", "anthropic", script["cost_usd"], cfg.llm_model)
            scenes = db.insert_scenes(
                [
                    {
                        "project_id": project_id,
                        "order_index": i,
                        "narration": s["narration"],
                        "image_prompt": s["image_prompt"],
                    }
                    for i, s in enumerate(script["scenes"])
                ]
            )

        total = len(scenes)

        # ---- 2. TTS per scene (before visuals: narration length = segment length)
        for i, scene in enumerate(scenes):
            if scene.get("audio_url"):
                continue
            db.set_progress(project_id, f"Озвучка: сцена {i + 1}/{total}")
            audio_path = work_dir / f"scene_{i:02d}.mp3"
            cost = tts_step.synthesize(cfg, scene["narration"], audio_path)
            # Точная длительность, а не оценка из заголовка mp3: по этому же
            # числу строится таймлайн и субтитры, и оно показывается
            # пользователю. Расхождение в 40 мс на сцену накапливается и делает
            # длину в интерфейсе не равной длине файла.
            duration = media.exact_duration_sec(audio_path)
            url = db.upload(f"projects/{project_id}/scene_{i:02d}/audio.mp3", audio_path.read_bytes(), "audio/mpeg")
            db.log_cost(project_id, "tts", "elevenlabs", cost, f"scene {i}")
            db.update_scene(
                scene["id"],
                audio_url=url,
                audio_duration_sec=round(duration, 3),
                status="audio_done",
            )
            scene.update(audio_url=url, audio_duration_sec=duration)

        # ---- 3. Image per scene
        for i, scene in enumerate(scenes):
            if scene.get("image_url"):
                continue
            db.set_progress(project_id, f"Кадры: сцена {i + 1}/{total}")
            image_path = work_dir / f"scene_{i:02d}.png"
            cost = image_step.generate_image(cfg, scene["image_prompt"], image_path, index=i)
            url = db.upload(f"projects/{project_id}/scene_{i:02d}/image.png", image_path.read_bytes(), "image/png")
            db.log_cost(project_id, "image", "fal", cost, f"scene {i}")
            db.update_scene(scene["id"], image_url=url, status="image_done")
            scene.update(image_url=url)

        # ---- 4. Image-to-video per scene (only in provider mode)
        if cfg.effective_video_mode == "provider":
            for i, scene in enumerate(scenes):
                if scene.get("video_url"):
                    continue
                db.set_progress(project_id, f"Видео: сцена {i + 1}/{total} (может занять несколько минут)")
                clip_path = work_dir / f"scene_{i:02d}_clip.mp4"
                cost = video_step.generate_clip(
                    cfg, scene["image_url"], scene["image_prompt"], clip_path
                )
                url = db.upload(f"projects/{project_id}/scene_{i:02d}/clip.mp4", clip_path.read_bytes(), "video/mp4")
                db.log_cost(project_id, "video", "fal", cost, f"scene {i}")
                db.update_scene(scene["id"], video_url=url, status="video_done")
                scene.update(video_url=url)

        # ---- 5. Render: make sure all assets are local (retries may start cold)
        db.set_progress(project_id, "Монтаж…")
        render_scenes = []
        for i, scene in enumerate(scenes):
            audio_path = _download(scene["audio_url"], work_dir / f"scene_{i:02d}.mp3")
            entry = {
                "audio_path": audio_path,
                "audio_duration": scene["audio_duration_sec"],
                "narration": scene.get("narration", ""),
            }
            if cfg.effective_video_mode == "provider" and scene.get("video_url"):
                entry["clip_path"] = _download(scene["video_url"], work_dir / f"scene_{i:02d}_clip.mp4")
            else:
                entry["image_path"] = _download(scene["image_url"], work_dir / f"scene_{i:02d}.png")
            render_scenes.append(entry)

        aspect = project.get("aspect_ratio") or cfg.video_format
        final_path = render_step.render_final(
            render_scenes,
            work_dir,
            music_file=cfg.music_file or None,
            aspect=aspect,
            transition_sec=cfg.transition_sec,
            subtitles=cfg.subtitles,
        )

        # ---- 6. Проверка результата до отдачи пользователю.
        # Длительности мало: чёрное видео нужной длины с тишиной её проходит.
        db.set_progress(project_id, "Проверка результата…")
        check = media.validate_final(final_path, media.frame_size(aspect))
        for warning in check["warnings"]:
            log.warning("[%s] качество: %s", project_id[:8], warning)
        if not check["ok"]:
            raise RuntimeError("Проверка финального файла не пройдена: " + "; ".join(check["errors"]))
        final_duration = check["duration_sec"]
        log.info(
            "[%s] проверка пройдена: %.3f с, %dx%d, звук %s, яркость %.1f, пик %.1f dB",
            project_id[:8], final_duration, check["width"], check["height"],
            "есть" if check["has_audio"] else "нет", check["brightness"], check["peak_db"],
        )

        db.set_progress(project_id, "Загрузка результата…")
        final_url = db.upload(f"projects/{project_id}/final.mp4", final_path.read_bytes(), "video/mp4")
        db.insert_render(project_id, final_url, final_duration)
        db.update_project(project_id, status="done", status_detail="Готово", error_message=None)
        log.info("[%s] done: %s", project_id[:8], final_url)

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
