"""Pipeline orchestrator: script -> TTS -> images -> video -> render -> upload.

Order matters: TTS runs before visuals so each scene's real narration length
drives its segment duration (audio/video sync). Every scene step is resumable:
completed assets are skipped on retry, so a failure at scene 4 never re-pays
providers for scenes 1-3.
"""
from __future__ import annotations

import logging
import math
import shutil
from pathlib import Path

import httpx

import budget
import media
import product_brief
import providers
import quality
import references as references_mod
import safe_mode
from config import COSTS, TMP_DIR, Config
import db as db_module
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


def _wants_real_video(shot: dict) -> bool:
    """Нужно ли этому кадру настоящее видео.

    Решение принято планировщиком: он один видит весь фильм и знает, сколько
    кадров помещается в цель покрытия. Дублировать правило здесь — значит
    получить два разных ответа на один вопрос.
    """
    return shot_plan.preferred_mode(shot) == "real_video"


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



# Сколько секунд отдаёт провайдер за один вызов image-to-video. Из этого
# числа складывается длина ролика в режиме «оживить фотографию».
PROVIDER_CLIP_SEC = 5.0


def _animate_photo(cfg: Config, db: Db, project: dict, reference: dict, work_dir, guard) -> None:
    """Режим B: фотография человека → настоящее движущееся видео.

    Отдельный путь, а не ветка внутри общего: здесь нет ни сценария, ни
    закадрового текста, а источник кадра — снимок пользователя, который
    запрещено подменять сгенерированным «похожим».

    Если платный путь закрыт, кадр остаётся движением по картинке. Выдавать
    это за настоящее видео нельзя (ТЗ §14), поэтому режим кадра честно
    остаётся `image_motion`, и покрытие будет нулевым.
    """
    project_id = project["id"]
    duration = float(project.get("duration_sec") or 10)
    aspect = project.get("aspect_ratio") or cfg.video_format
    brief = product_brief.VisualReferenceBrief(
        creative_direction=project.get("topic") or "",
        width=int(reference.get("width") or 0),
        height=int(reference.get("height") or 0),
    )
    motion = brief.motion_prompt()

    scenes = db.get_scenes(project_id)
    if not scenes:
        scenes = db.insert_scenes([{
            "project_id": project_id, "order_index": 0,
            # Озвучки нет: человек просил оживить кадр, а не рассказать историю.
            "narration": "", "image_prompt": motion,
        }])
    scene = scenes[0]

    shots = db.get_shots(project_id)
    if not shots:
        count = max(1, math.ceil(duration / PROVIDER_CLIP_SEC))
        per_shot = round(duration / count, 3)
        shots = db.insert_shots([{
            "project_id": project_id, "scene_id": scene["id"], "order_index": i,
            "purpose": "animate", "shot_type": "medium",
            "timeline_duration": per_shot, "generation_duration": PROVIDER_CLIP_SEC,
            "visual_prompt": motion, "video_prompt": motion,
            "camera_motion": "push_in", "motion_requirement": "critical",
            "visual_importance": 1.0, "narrative_importance": 1.0,
            "first_frame_reference": reference["public_url"],
            "image_url": reference["public_url"],
        } for i in range(count)])
        log.info("[%s] оживление фотографии: %d клип(ов) по %.1f с", project_id[:8], count, per_shot)

    total = len(shots)
    if safe_mode.is_paid_video_allowed(cfg):
        for i, shot in enumerate(shots):
            if shot.get("video_url"):
                continue
            db.set_progress(project_id, f"Оживляем фотографию: {i + 1}/{total}")
            clip_path = work_dir / f"shot_{i:02d}_clip.mp4"
            choice = providers.choose(
                "video", importance=1.0, shot_label=f"клип {i + 1}",
                needs_image_to_video=True, needs_reference=True, aspect=aspect,
                affordable_usd=guard.spendable_usd if guard.has_ceiling else None,
            )
            if choice is None:
                reason = providers.why_not(
                    "video",
                    affordable_usd=guard.spendable_usd if guard.has_ceiling else None,
                    needs_image_to_video=True, needs_reference=True, aspect=aspect,
                )
                log.info("[%s] клип %d не будет сделан: %s", project_id[:8], i, reason)
                db.update_shot(shot["id"], failure_reason=reason[:500])
                continue
            try:
                cost = video_step.generate_clip(
                    cfg, reference["public_url"], motion, clip_path,
                    model=choice.model, cost_usd=choice.cost_usd,
                )
            except (video_step.VideoError, budget.BudgetExceeded) as e:
                log.warning("[%s] клип %d не получился: %s", project_id[:8], i, e)
                db.update_shot(shot["id"], failure_reason=str(e)[:500])
                continue
            url = db.upload(f"projects/{project_id}/shot_{i:02d}/clip.mp4", clip_path.read_bytes(), "video/mp4")
            db.log_cost(project_id, "video", choice.provider, cost, f"shot {i}")
            guard.record(cost, f"клип {i}")
            db.update_shot(shot["id"], video_url=url, status="video_done",
                           generation_mode="real_video", actual_cost_usd=cost,
                           provider=choice.provider, model=choice.model)
            shot.update(video_url=url, generation_mode="real_video")
    else:
        log.info("[%s] платное видео закрыто: фотография получит движение камеры", project_id[:8])

    db.set_progress(project_id, "Монтаж…")
    render_shots = []
    for i, shot in enumerate(shots):
        entry = {"duration": float(shot["timeline_duration"]), "motion": shot.get("camera_motion")}
        if shot.get("video_url"):
            entry["clip_path"] = _download(shot["video_url"], work_dir / f"shot_{i:02d}_clip.mp4")
        else:
            entry["image_path"] = _download(shot["image_url"], work_dir / f"shot_{i:02d}.jpg")
        render_shots.append(entry)

    quiet = work_dir / "silence.m4a"
    media.silence(quiet, sum(e["duration"] for e in render_shots))
    final_path = render_step.render_final(
        [{"audio_path": quiet, "audio_duration": media.exact_duration_sec(quiet),
          "narration": "", "shots": render_shots}],
        work_dir, music_file=cfg.music_file or None, aspect=aspect,
        transition_sec=0.0, subtitles=False,
    )

    db.set_progress(project_id, "Проверка результата…")
    check = media.validate_final(final_path, media.frame_size(aspect))
    if not check["ok"]:
        raise RuntimeError("Проверка финального файла не пройдена: " + "; ".join(check["errors"]))

    db.set_progress(project_id, "Загрузка результата…")
    final_url = db.upload(f"projects/{project_id}/final.mp4", final_path.read_bytes(), "video/mp4")
    db.insert_render(project_id, final_url, check["duration_sec"])
    db.update_project(project_id, status="done", status_detail="Готово", error_message=None)
    coverage = real_video_coverage(shots)
    log.info("[%s] FINAL: %.2f с, клипов %d, настоящее видео %.0f%%",
             project_id[:8], check["duration_sec"], len(shots), coverage * 100)




# Метка готового снимка в имени файла. Отдельной колонки для этого не нужно:
# повторный запуск проекта должен видеть, что работа уже сделана, а лишний
# столбец ради одного булева значения — это миграция на ровном месте.
READY_MARK = "_ready"


def _prepare_references(db: Db, project_id: str, rows: list[dict], work_dir: Path) -> list[dict]:
    """Привести снимки пользователя к рабочему виду — один раз за проект.

    Поворот по EXIF здесь не формальность: телефон пишет ориентацию в
    метаданные, и без этого шага товар уезжает боком, причём молча.

    Снимок, который не удалось обработать, остаётся исходным: отказываться от
    заказа из-за неудачного поворота было бы хуже, чем собрать ролик из
    оригинала.
    """
    prepared = []
    for row in rows:
        order = int(row.get("order_index") or 0)
        if READY_MARK in Path(row.get("storage_path") or "").stem:
            prepared.append(row)
            continue
        try:
            source = _download(row["public_url"], work_dir / f"ref_src_{order:02d}")
            info = references_mod.normalize(
                source, work_dir, f"ref_{order:02d}{READY_MARK}", row.get("mime_type") or "image/jpeg"
            )
        except Exception as e:  # noqa: BLE001 — исходник лучше отказа
            log.warning("[%s] снимок %d не удалось подготовить: %s", project_id[:8], order, e)
            prepared.append(row)
            continue

        ready: Path = info["path"]
        destination = f"projects/{project_id}/references/{order:02d}{READY_MARK}{ready.suffix}"
        url = db.upload(destination, ready.read_bytes(), info["mime_type"])
        db.update_reference(
            row["id"], public_url=url, storage_path=destination,
            width=info["width"], height=info["height"],
        )
        row = {**row, "public_url": url, "storage_path": destination,
               "width": info["width"], "height": info["height"], "note": info["note"]}
        if info["note"]:
            log.warning("[%s] снимок %d: %s", project_id[:8], order, info["note"])
        prepared.append(row)
    return prepared


def _render_plan(shots: list[dict], scenes: list[dict], work_dir) -> list[dict]:
    """Собрать задание монтажу из текущих решений по кадрам.

    Вынесено отдельно, потому что после починки план строится заново: решения
    изменились, а скачанные ассеты — нет.
    """
    by_scene: dict[str, list[dict]] = {}
    for i, shot in enumerate(shots):
        entry = {
            "duration": float(shot["timeline_duration"]),
            "motion": shot.get("camera_motion"),
            # Крупность плана. Для товарных кадров это единственный способ
            # сделать из одного снимка несколько разных кадров.
            "framing": shot.get("shot_type"),
        }
        # Готовое настоящее видео используется всегда, каким бы ни был текущий
        # режим. Прежнее условие требовало ещё и режима provider, и оплаченный
        # клип молча заменялся зумом по картинке — то самое «real provider
        # files are generated but ignored».
        if shot.get("video_url"):
            entry["clip_path"] = _download(shot["video_url"], work_dir / f"shot_{i:02d}_clip.mp4")
        else:
            entry["image_path"] = _download(shot["image_url"], work_dir / f"shot_{i:02d}.png")
        by_scene.setdefault(shot["scene_id"], []).append(entry)

    plan = []
    for i, scene in enumerate(scenes):
        plan.append({
            "audio_path": _download(scene["audio_url"], work_dir / f"scene_{i:02d}.mp3"),
            "audio_duration": scene["audio_duration_sec"],
            "narration": scene.get("narration", ""),
            "shots": by_scene.get(scene["id"], []),
        })
    return plan



# Жёсткий потолок кругов починки (ТЗ §25). Больше двух — это уже не починка,
# а бесконечная пересборка за счёт человека.
MAX_REPAIR_ROUNDS = 2

# Чем заменить движение, которое не спасло кадр. Панорама заметнее наезда:
# наезд на однотонной картинке почти не читается.
LIVELIER_MOTION = {
    "push_in": "pan_right",
    "pull_out": "pan_left",
    "tilt_up": "pan_right",
    "tilt_down": "pan_left",
    "pan_right": "push_in",
    "pan_left": "pull_out",
}


def _fresh_motion(shots: list[dict], shot: dict) -> str:
    """Новое движение кадра — заметнее прежнего и не такое, как у соседей.

    Соседи важны не меньше заметности: два одинаковых движения подряд
    склеиваются в один длинный кадр, и починка одного дефекта создала бы
    другой. Это ровно то, что поймал сквозной тест.
    """
    index = shots.index(shot)
    taken = {
        (shots[i].get("camera_motion") or "")
        for i in (index - 1, index + 1)
        if 0 <= i < len(shots)
    }
    current = shot.get("camera_motion") or ""
    preferred = LIVELIER_MOTION.get(current, "pan_right")
    for candidate in (preferred, *shot_plan.CAMERA_MOTIONS):
        if candidate != current and candidate not in taken:
            return candidate
    return preferred


def _repair_shots(db: Db, shots: list[dict], report, project_id: str) -> int:
    """Починить только те кадры, на которые указал инспектор.

    Перегенерировать весь фильм из-за одного замершего кадра запрещено (§25):
    это дорого, долго и портит то, что уже получилось. Каждый кадр чинится
    не больше одного раза за круг — иначе цикл никогда не сойдётся.
    """
    by_id = {s.get("id"): s for s in shots}
    fixed = 0
    for issue in report.repairable:
        shot = by_id.get(issue.shot_id)
        if shot is None or int(shot.get("retry_count") or 0) >= MAX_REPAIR_ROUNDS:
            continue

        if issue.kind in ("FROZEN_VIDEO", "STATIC_OPENING"):
            if shot.get("video_url"):
                # Провайдер вернул застывший клип. Честный выход — отказаться
                # от него: движение по фотографии хотя бы движется, а покрытие
                # упадёт и об этом будет сказано.
                db.update_shot(
                    shot["id"], video_url=None, generation_mode="image_motion",
                    retry_count=int(shot.get("retry_count") or 0) + 1,
                    failure_reason=f"клип замер на {issue.at_sec or 0:.1f} с, заменён движением камеры",
                )
                shot.update(video_url=None, generation_mode="image_motion")
            else:
                new_motion = _fresh_motion(shots, shot)
                db.update_shot(
                    shot["id"], camera_motion=new_motion,
                    retry_count=int(shot.get("retry_count") or 0) + 1,
                )
                shot.update(camera_motion=new_motion)
            shot["retry_count"] = int(shot.get("retry_count") or 0) + 1
            fixed += 1
            log.info("[REPAIR] [%s] кадр %s: %s",
                     project_id[:8], str(issue.shot_id)[:8], issue.kind)

    if fixed:
        log.info("[REPAIR] починено кадров: %d", fixed)
    return fixed


def _degraded_reason(cfg: Config, shots: list[dict], coverage: float, target: float) -> str | None:
    """Почему ролик не дотянул до цели. None — дотянул."""
    if coverage + 1e-6 >= target:
        return None
    if not safe_mode.is_paid_video_allowed(cfg):
        return "Настоящее видео отключено в этом режиме — движение сделано камерой по кадру."
    denied = [s for s in shots if s.get("failure_reason")]
    if any("бюджет" in (s.get("failure_reason") or "").lower() for s in denied):
        return "Бюджета хватило не на все кадры — часть осталась движением камеры."
    if denied:
        return "Провайдер видео ответил отказом на часть кадров."
    return "Настоящим видео закрыта меньшая часть ролика, чем планировалось."


def run_project(cfg: Config, db: Db, project_id: str) -> None:
    project = db.get_project(project_id)
    work_dir = TMP_DIR / project_id
    work_dir.mkdir(parents=True, exist_ok=True)

    # Потолок расходов проекта. None — потолка нет, поведение как раньше.
    # Страж живёт ровно эту сборку и отказывает платным вызовам до того, как
    # они сделаны: перерасход нельзя заметить задним числом.
    guard = budget.bind(project.get("max_budget_usd"))

    # Снимки, которые принёс человек. Для обычного ролика их нет, и всё
    # работает как раньше.
    project_type = project.get("project_type") or "general_video"
    references = db.get_references(project_id) if project_type != "general_video" else []

    try:
        if references:
            db.set_progress(project_id, "Готовим фотографии…")
            references = _prepare_references(db, project_id, references, work_dir)
        reference_urls = [r["public_url"] for r in references]

        if project_type == "image_to_video":
            primary = db_module.primary_of(references)
            if primary is None:
                raise RuntimeError("режим «оживить фотографию» требует загруженный снимок")
            _animate_photo(cfg, db, project, primary, work_dir, guard)
            return

        # ---- 1. Script (skipped if scenes already exist from a previous attempt)
        scenes = db.get_scenes(project_id)
        if not scenes:
            db.set_progress(project_id, "Пишем сценарий…")
            brief = (
                product_brief.ProductBrief.from_project(project, len(references))
                if project_type == "product_ad" else None
            )
            if brief is not None:
                log.info("[%s] реклама: «%s», снимков %d", project_id[:8],
                         brief.product_name, len(references))
            script = script_step.generate_script(
                cfg, project["topic"], project["style"], project["duration_sec"], brief=brief
            )
            # В учёт идёт тот, кто действительно написал сценарий, а не тот,
            # кто стоит первым в настройке: цепочка могла уйти к запасному.
            db.log_cost(
                project_id, "script", script.get("provider") or cfg.llm_provider,
                script["cost_usd"], script.get("model") or cfg.active_llm_model,
            )
            guard.record(script["cost_usd"], "сценарий")
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
            guard.record(cost, f"озвучка сцены {i}")
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
                zip(scenes, shot_plan.plan_film_shots(
                    scenes, project.get("style") or "cinematic",
                    references=reference_urls,
                ))
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
            reference_url = shot.get("first_frame_reference")
            if reference_url:
                # Кадр товара — это снимок пользователя, а не «похожая»
                # картинка от генератора. Ни один из доступных генераторов
                # не держит форму и упаковку по образцу, и придуманный товар
                # обесценивает рекламу целиком.
                db.update_shot(shot["id"], image_url=reference_url, status="image_done")
                shot.update(image_url=reference_url)
                continue

            db.set_progress(project_id, f"Кадры: {i + 1}/{shot_total}")
            image_path = work_dir / f"shot_{i:02d}.png"
            cost = image_step.generate_image(cfg, shot["visual_prompt"], image_path, index=i)
            url = db.upload(f"projects/{project_id}/shot_{i:02d}/image.png", image_path.read_bytes(), "image/png")
            db.log_cost(project_id, "image", cfg.image_providers[0], cost, f"shot {i}")
            guard.record(cost, f"кадр {i}")
            db.update_shot(shot["id"], image_url=url, status="image_done", actual_cost_usd=cost)
            shot.update(image_url=url)

        aspect_hint = project.get("aspect_ratio") or cfg.video_format

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
                # Модель выбирается на кадр: крючку и кадру товара достаётся
                # лучшее, фону — дешёвое. Остаток бюджета участвует в отсечке,
                # поэтому дорогая модель просто не попадёт в кандидаты, когда
                # денег на неё нет.
                choice = providers.choose(
                    "video",
                    importance=float(shot.get("visual_importance") or 0.5),
                    shot_label=f"кадр {i + 1}",
                    needs_image_to_video=True,
                    needs_reference=bool(shot.get("first_frame_reference")),
                    aspect=aspect_hint,
                    affordable_usd=guard.spendable_usd if guard.has_ceiling else None,
                )
                if choice is None:
                    # Отказ до вызова — лучший вид отказа: ни задержки, ни
                    # денег. Но причину обязан увидеть человек, иначе кадр
                    # молча остаётся фотографией.
                    reason = providers.why_not(
                        "video",
                        affordable_usd=guard.spendable_usd if guard.has_ceiling else None,
                        needs_image_to_video=True,
                        needs_reference=bool(shot.get("first_frame_reference")),
                        aspect=aspect_hint,
                    )
                    log.info("[%s] кадр %d без настоящего видео: %s", project_id[:8], i, reason)
                    db.update_shot(shot["id"], failure_reason=reason[:500])
                    continue
                try:
                    cost = video_step.generate_clip(
                        cfg, shot["image_url"],
                        shot.get("video_prompt") or shot["visual_prompt"], clip_path,
                        model=choice.model, cost_usd=choice.cost_usd,
                    )
                except (video_step.VideoError, budget.BudgetExceeded) as e:
                    # Падение провайдера и конец денег кончаются одинаково:
                    # кадр остаётся движением по картинке, остальные идут
                    # дальше, причина записывается. Проект из-за одного кадра
                    # не падает — но и покрытие не приписывается.
                    log.warning("[%s] кадр %d без настоящего видео: %s", project_id[:8], i, e)
                    db.update_shot(shot["id"], failure_reason=str(e)[:500])
                    continue
                url = db.upload(f"projects/{project_id}/shot_{i:02d}/clip.mp4", clip_path.read_bytes(), "video/mp4")
                db.log_cost(project_id, "video", choice.provider, cost, f"shot {i}")
                guard.record(cost, f"видео кадра {i}")
                # Только здесь кадр становится настоящим видео: движение по
                # картинке засчитывать в real_video нельзя.
                db.update_shot(
                    shot["id"], video_url=url, status="video_done",
                    generation_mode="real_video", actual_cost_usd=cost,
                    provider=choice.provider, model=choice.model,
                )
                shot.update(video_url=url, generation_mode="real_video")

        # ---- 6. Render: make sure all assets are local (retries may start cold)
        db.set_progress(project_id, "Монтаж…")
        render_scenes = _render_plan(shots, scenes, work_dir)

        aspect = project.get("aspect_ratio") or cfg.video_format
        size = media.frame_size(aspect)
        target = shot_plan.COVERAGE_TARGETS.get(
            shot_plan.DEFAULT_MODE, 0.0
        ) if safe_mode.is_paid_video_allowed(cfg) else 0.0

        # ---- 6. Первая сборка → проверка → починка только плохих кадров.
        # Проверка длительности и потоков мало что значит: чёрное видео нужной
        # длины с тишиной её проходит, и слайдшоу проходит тоже.
        for attempt in range(MAX_REPAIR_ROUNDS + 1):
            final_path = render_step.render_final(
                render_scenes,
                work_dir,
                music_file=cfg.music_file or None,
                aspect=aspect,
                transition_sec=cfg.transition_sec,
                subtitles=cfg.subtitles,
            )
            db.set_progress(project_id, "Проверка результата…")
            report = quality.inspect(
                final_path, size, shots,
                requested_sec=float(project.get("duration_sec") or 0) or None,
                coverage_target=target,
            )
            if not report.ok:
                raise RuntimeError(
                    "Проверка финального файла не пройдена: "
                    + "; ".join(str(i) for i in report.errors)
                )
            if attempt == MAX_REPAIR_ROUNDS or not report.repairable:
                break
            if cfg.mvp_safe_mode:
                # Кадр-заглушка однотонный: двигать в нём нечего, и любое
                # измерение движения покажет ноль. Чинить нечего — вторая
                # сборка потратила бы минуты и вернула тот же результат.
                log.info("[REPAIR] безопасный режим: измерять движение на заглушках нечем")
                break
            db.set_progress(project_id, f"Починка кадров (круг {attempt + 1})…")
            if not _repair_shots(db, shots, report, project_id):
                break
            # Пересобирать нужно из тех же ассетов, но с новыми решениями по
            # кадрам: заново скачивать и генерировать ничего не надо.
            render_scenes = _render_plan(shots, scenes, work_dir)

        final_duration = report.duration_sec

        db.set_progress(project_id, "Загрузка результата…")
        final_url = db.upload(f"projects/{project_id}/final.mp4", final_path.read_bytes(), "video/mp4")
        db.insert_render(project_id, final_url, final_duration)
        coverage = real_video_coverage(shots)
        reason = _degraded_reason(cfg, shots, coverage, target)
        # Ролик ниже цели по настоящему движению — готов, играется, но
        # выдавать его за чистый успех нельзя (ТЗ §32).
        db.update_project(
            project_id,
            status="done_degraded" if reason else "done",
            status_detail="Готово" if not reason else "Готово с оговоркой",
            error_message=None,
            real_video_coverage=coverage,
            degraded_reason=reason,
            quality={
                "duration_sec": round(report.duration_sec, 2),
                "weak_motion_ratio": report.weak_motion_ratio,
                "opening_motion": report.opening_motion,
                "frozen_sections": len(report.frozen_sections),
                "issues": [str(i) for i in report.issues][:10],
            },
        )
        real_count = sum(1 for s in shots if s.get("generation_mode") == "real_video")
        log.info(
            "[%s] FINAL: %.2f с, кадров %d, настоящее видео %d (%.0f%% таймлайна), "
            "движение по картинке %d",
            project_id[:8], final_duration, len(shots), real_count,
            coverage * 100, len(shots) - real_count,
        )
        log.info("[%s] done: %s", project_id[:8], final_url)

    finally:
        budget.unbind()
        shutil.rmtree(work_dir, ignore_errors=True)
