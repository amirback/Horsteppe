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
import safe_mode
from config import TMP_DIR, Config
from db import Db
from steps import image_step, render_step, script_step, shot_plan, tts_step, video_step

log = logging.getLogger("worker.pipeline")


def _download(url: str, dest: Path) -> Path:
    if not dest.exists():
        with httpx.Client(timeout=120) as client:
            resp = client.get(url)
            resp.raise_for_status()
        dest.write_bytes(resp.content)
    return dest


# Кадры, которым настоящее движение нужно в первую очередь. Низкая важность
# НЕ означает «поставить картинку»: она означает «взять видео подешевле»,
# а движение по картинке остаётся последним средством.
REAL_VIDEO_REQUIREMENTS = ("critical", "high", "normal")


def _wants_real_video(shot: dict) -> bool:
    """Нужно ли этому кадру настоящее видео."""
    return (shot.get("motion_requirement") or "normal") in REAL_VIDEO_REQUIREMENTS


def real_video_coverage(shots: list[dict]) -> float:
    """Доля таймлайна, закрытая настоящим видео.

    Зумящаяся фотография сюда не попадает никогда — на этом различении стоит
    всё обещание продукта.
    """
    total = sum(float(s.get("timeline_duration") or 0) for s in shots)
    if total <= 0:
        return 0.0
    real = sum(
        float(s.get("timeline_duration") or 0)
        for s in shots
        if s.get("video_url") and s.get("generation_mode") == "real_video"
    )
    return round(real / total, 4)


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
            # Описание героев и мира вшивается в промпт каждой сцены прямо
            # здесь. Так оно переживает повтор: на второй попытке сценарий
            # заново не пишется, и хранить описание больше негде. Без него
            # генератор рисует новых людей в каждом кадре.
            cast = (script.get("continuity") or "").strip()
            head = f"{cast}. " if cast else ""
            scenes = db.insert_scenes(
                [
                    {
                        "project_id": project_id,
                        "order_index": i,
                        "narration": s["narration"],
                        "image_prompt": f"{head}{s['image_prompt']}",
                    }
                    for i, s in enumerate(script["scenes"])
                ]
            )
            # Кадры, придуманные сценаристом, нужны только на этой попытке:
            # дальше они уже лежат в таблице кадров.
            for scene, authored in zip(scenes, script["scenes"]):
                scene["shots"] = authored.get("shots") or []

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

        # ---- 3. Планирование кадров: сцена разбивается на кадры камеры.
        # Без этого шага сцена остаётся одной картинкой на 6-7 секунд, и ролик
        # читается как слайдшоу. Как и сцены, кадры планируются один раз:
        # при повторе уже готовые пропускаются.
        shots = db.get_shots(project_id)
        if not shots:
            db.set_progress(project_id, "Раскадровка…")
            rows = []
            for i, (scene, plan) in enumerate(
                zip(scenes, shot_plan.plan_film_shots(scenes, project.get("style") or "cinematic"))
            ):
                for shot in plan:
                    rows.append(
                        {**shot, "project_id": project_id, "scene_id": scene["id"],
                         "order_index": len(rows)}
                    )
            shots = db.insert_shots(rows)
            log.info("[%s] раскадровка: %d кадров из %d сцен", project_id[:8], len(shots), total)

        # ---- 4. Картинка на каждый кадр
        shot_total = len(shots)
        for i, shot in enumerate(shots):
            if shot.get("image_url"):
                continue
            db.set_progress(project_id, f"Кадры: {i + 1}/{shot_total}")
            image_path = work_dir / f"shot_{i:02d}.png"
            cost = image_step.generate_image(cfg, shot["visual_prompt"], image_path, index=i)
            url = db.upload(f"projects/{project_id}/shot_{i:02d}/image.png", image_path.read_bytes(), "image/png")
            db.log_cost(project_id, "image", cfg.image_providers[0], cost, f"shot {i}")
            db.update_shot(shot["id"], image_url=url, status="image_done", actual_cost_usd=cost)
            shot.update(image_url=url)

        # ---- 5. Настоящее видео на кадр.
        #
        # Решение принимается по каждому кадру, а не одним переключателем на
        # весь ролик: важному кадру настоящее движение нужнее, чем фону.
        # Провал одного кадра не понижает весь фильм — он откатывается на
        # движение по картинке в одиночку, и это записывается в лог.
        if safe_mode.is_paid_video_allowed(cfg):
            for i, shot in enumerate(shots):
                if shot.get("video_url") or not _wants_real_video(shot):
                    continue
                db.set_progress(
                    project_id, f"Видео: кадр {i + 1}/{shot_total} (может занять несколько минут)"
                )
                clip_path = work_dir / f"shot_{i:02d}_clip.mp4"
                try:
                    cost = video_step.generate_clip(
                        cfg, shot["image_url"],
                        shot.get("video_prompt") or shot["visual_prompt"], clip_path,
                    )
                except video_step.VideoError as e:
                    # Падение провайдера не должно уносить проект: кадр
                    # остаётся движением по картинке, остальные идут дальше.
                    log.warning("[%s] кадр %d без настоящего видео: %s", project_id[:8], i, e)
                    db.update_shot(shot["id"], failure_reason=str(e)[:500])
                    continue
                url = db.upload(f"projects/{project_id}/shot_{i:02d}/clip.mp4", clip_path.read_bytes(), "video/mp4")
                db.log_cost(project_id, "video", "fal", cost, f"shot {i}")
                # Только здесь кадр становится настоящим видео: движение по
                # картинке засчитывать в real_video нельзя.
                db.update_shot(
                    shot["id"], video_url=url, status="video_done",
                    generation_mode="real_video", actual_cost_usd=cost,
                )
                shot.update(video_url=url, generation_mode="real_video")

        # ---- 6. Render: make sure all assets are local (retries may start cold)
        db.set_progress(project_id, "Монтаж…")
        by_scene: dict[str, list[dict]] = {}
        for i, shot in enumerate(shots):
            entry = {
                "duration": float(shot["timeline_duration"]),
                "motion": shot.get("camera_motion"),
            }
            # Готовое настоящее видео используется всегда, каким бы ни был
            # текущий режим. Прежнее условие требовало ещё и режима provider,
            # и оплаченный клип молча заменялся зумом по картинке — то самое
            # «real provider files are generated but ignored».
            if shot.get("video_url"):
                entry["clip_path"] = _download(shot["video_url"], work_dir / f"shot_{i:02d}_clip.mp4")
            else:
                entry["image_path"] = _download(shot["image_url"], work_dir / f"shot_{i:02d}.png")
            by_scene.setdefault(shot["scene_id"], []).append(entry)

        render_scenes = []
        for i, scene in enumerate(scenes):
            audio_path = _download(scene["audio_url"], work_dir / f"scene_{i:02d}.mp3")
            render_scenes.append({
                "audio_path": audio_path,
                "audio_duration": scene["audio_duration_sec"],
                "narration": scene.get("narration", ""),
                "shots": by_scene.get(scene["id"], []),
            })

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
        coverage = real_video_coverage(shots)
        real_count = sum(1 for s in shots if s.get("generation_mode") == "real_video")
        log.info(
            "[%s] FINAL: %.2f с, кадров %d, настоящее видео %d (%.0f%% таймлайна), "
            "движение по картинке %d",
            project_id[:8], final_duration, len(shots), real_count,
            coverage * 100, len(shots) - real_count,
        )
        log.info("[%s] done: %s", project_id[:8], final_url)

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
