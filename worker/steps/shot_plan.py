"""Планировщик кадров: сцена → несколько кадров камеры.

Сцена — смысловая часть истории, кадр — конкретный кадр камеры. Ровно это
различение убирает слайдшоу: раньше сцена была одной картинкой на 6-7 секунд.

Источник истины по длительности остаётся голосом (CLAUDE.md §8): сумма кадров
сцены равна её озвучке до миллисекунды. Планировщик ничего не генерирует и
никуда не ходит — он только режет время и текст, поэтому проверяется без сети
и без денег.
"""
from __future__ import annotations

import logging
import math

log = logging.getLogger("worker.shot_plan")

# Границы длины кадра в монтаже. Короче — глаз не успевает прочитать кадр,
# длиннее — возвращается ощущение фотографии с зумом.
MIN_SHOT_SEC = 2.0
MAX_SHOT_SEC = 5.0

# Темп монтажа по стилю: сколько секунд в среднем живёт кадр.
PACING_SEC: dict[str, float] = {
    "cinematic": 3.4,
    "documentary": 4.0,
    "explainer": 2.8,
    "product": 2.4,
    "anime": 2.6,
}
DEFAULT_PACING_SEC = 3.2

# Движения камеры идут по кругу, но соседям одинаковое не достаётся —
# иначе склейка перестаёт читаться как склейка.
CAMERA_MOTIONS = (
    "push_in",
    "pan_right",
    "pull_out",
    "tilt_up",
    "pan_left",
    "tilt_down",
)

# Крупность плана чередуется вместе с движением: общий план, средний, крупный,
# деталь. Одинаковая крупность подряд читается как один непрерывный кадр.
SHOT_TYPES = ("wide", "medium", "close_up", "detail")

# Лестница приоритетов: чем выше кадр, тем раньше ему достаётся дорогая
# генерация. Зритель решает за первые секунды, а финал закрывает историю —
# поэтому крючок и кульминация стоят выше всего.
HOOK_PURPOSE = "hook"
CLIMAX_PURPOSE = "climax"
PURPOSE_IMPORTANCE: dict[str, float] = {
    HOOK_PURPOSE: 1.00,
    CLIMAX_PURPOSE: 0.95,
    "action": 0.80,
    "character": 0.70,
    "supporting": 0.55,
    "background": 0.35,
}

# Доля таймлайна, которую в идеале закрывает настоящее видео. Бриф: SMART —
# около 70%, CINEMATIC — около 90% там, где это оправдано.
COVERAGE_TARGETS: dict[str, float] = {
    "preview": 0.0,
    "draft": 0.35,
    "smart": 0.70,
    "cinematic": 0.90,
}
DEFAULT_MODE = "smart"

REAL_VIDEO_REQUIREMENTS = ("critical", "high")


def preferred_mode(shot: dict) -> str:
    """Чем кадр стоит закрывать: настоящим видео или движением по картинке.

    Отдельной колонки в базе нет и не нужно: `motion_requirement` ровно это и
    означает — насколько кадру необходимо настоящее движение.
    """
    return (
        "real_video"
        if (shot.get("motion_requirement") or "normal") in REAL_VIDEO_REQUIREMENTS
        else "image_motion"
    )


def assign_generation_modes(shots: list[dict], mode: str = DEFAULT_MODE) -> float:
    """Раздать кадрам предпочтительный способ генерации под цель покрытия.

    Бюджет делится не поровну: сначала настоящее видео получают самые важные
    кадры — крючок, кульминация, действие. Низкая важность не означает
    «поставить картинку» автоматически, она означает «уступить очередь».

    Меняет кадры на месте, возвращает достигнутую долю покрытия.
    """
    target = COVERAGE_TARGETS.get(mode, COVERAGE_TARGETS[DEFAULT_MODE])
    total = sum(float(s["timeline_duration"]) for s in shots)
    if total <= 0:
        return 0.0

    for shot in shots:
        shot["motion_requirement"] = "low"

    chosen = 0.0
    # Порядок: важность, затем место в фильме — чтобы результат не зависел
    # от случайностей сортировки.
    for shot in sorted(shots, key=lambda s: (-float(s["visual_importance"]), s["order_index"])):
        if chosen >= target * total:
            break
        shot["motion_requirement"] = "critical" if shot["purpose"] == HOOK_PURPOSE else "high"
        chosen += float(shot["timeline_duration"])

    return round(chosen / total, 4)


def log_plan(shots: list[dict], requested_sec: float, coverage: float) -> None:
    """Печать плана в формате, принятом в техзадании."""
    log.info("[SHOT PLAN]")
    log.info("Requested duration: %.1fs", requested_sec)
    log.info("Total shots: %d", len(shots))
    for shot in shots:
        log.info(
            "Shot %02d duration=%.1f purpose=%s preferred_mode=%s importance=%s",
            shot["order_index"] + 1,
            float(shot["timeline_duration"]),
            shot["purpose"].upper(),
            preferred_mode(shot).upper(),
            _importance_word(float(shot["visual_importance"])),
        )
    log.info("Planned REAL_VIDEO coverage target: %.0f%%", coverage * 100)


def _importance_word(value: float) -> str:
    if value >= 0.8:
        return "high"
    return "medium" if value >= 0.5 else "low"


def shot_count(duration_sec: float, style: str) -> int:
    """Сколько кадров заслуживает сцена такой длины.

    Число выводится из длительности и темпа, а не ставится константой:
    бриф прямо запрещает «всегда 10 кадров на любой проект».
    """
    if duration_sec <= 0:
        return 0
    target = PACING_SEC.get(style, DEFAULT_PACING_SEC)
    ideal = max(1, round(duration_sec / target))
    # Ни один кадр не должен оказаться короче минимума или длиннее максимума.
    most = max(1, int(duration_sec // MIN_SHOT_SEC))
    least = max(1, math.ceil(duration_sec / MAX_SHOT_SEC))
    return max(least, min(ideal, most))


def split_durations(duration_sec: float, count: int) -> list[float]:
    """Разделить длительность сцены на `count` кадров ровно, без потери хвоста.

    Последний кадр забирает остаток от округления: сумма обязана совпадать с
    озвучкой, иначе таймлайн уедет от голоса, а субтитры — от таймлайна.
    """
    if count <= 0:
        return []
    even = round(duration_sec / count, 3)
    parts = [even] * (count - 1)
    parts.append(round(duration_sec - sum(parts), 3))
    return parts


def split_narration(narration: str, count: int) -> list[str]:
    """Разложить текст сцены по кадрам примерно поровну, не разрывая слов."""
    words = narration.split()
    if count <= 1 or not words:
        return [narration] + [""] * max(0, count - 1)
    per = len(words) / count
    chunks: list[str] = []
    for i in range(count):
        start = round(i * per)
        end = round((i + 1) * per) if i < count - 1 else len(words)
        chunks.append(" ".join(words[start:end]))
    return chunks


def plan_scene_shots(
    *,
    scene_index: int,
    scene_count: int,
    narration: str,
    audio_duration_sec: float,
    image_prompt: str,
    style: str = "cinematic",
    motion_offset: int = 0,
    continuity: str = "",
    authored_shots: list[dict] | None = None,
) -> list[dict]:
    """Разбить одну сцену на кадры.

    Возвращает список словарей под колонки таблицы `shots`. Ассеты и
    провайдер здесь не выбираются — это работа маршрутизатора.

    `motion_offset` — сколько кадров уже спланировано в фильме. Без него
    каждая сцена начинала движение заново, и весь ролик шёл «наезд, панорама,
    наезд, панорама»: формально склейки есть, а камера одна и та же.
    """
    # Кадры, придуманные сценаристом, лучше механической нарезки: он знает,
    # что происходит в сцене, и держит одних и тех же героев. Механика
    # остаётся запасным путём — например, в безопасном режиме.
    authored = [s for s in (authored_shots or []) if (s.get("framing") or s.get("action"))]
    # Сценарист задаёт минимум кадров, темп стиля может добавить ещё. Раньше
    # авторское число побеждало целиком, и стиль вообще ни на что не влиял:
    # и размеренный документальный, и быстрый продуктовый ролик резались
    # одинаково.
    count = max(len(authored), shot_count(audio_duration_sec, style))
    if count == 0:
        return []
    # Слишком мелкая нарезка ломает читаемость кадра.
    while count > 1 and audio_duration_sec / count < MIN_SHOT_SEC:
        count -= 1
        authored = authored[:count]
    # Слишком крупная возвращает слайдшоу: сценарист дал три кадра на сцену в
    # 17 секунд, и вышли куски по 5.8 секунды при потолке в 5. Недостающим
    # кадрам крупность подбирает механика.
    while audio_duration_sec / count > MAX_SHOT_SEC:
        count += 1

    durations = split_durations(audio_duration_sec, count)
    texts = split_narration(narration, count)

    is_first_scene = scene_index == 0
    is_last_scene = scene_index == scene_count - 1

    shots: list[dict] = []
    for i, (seconds, text) in enumerate(zip(durations, texts)):
        first_of_film = is_first_scene and i == 0
        last_of_film = is_last_scene and i == count - 1

        purpose = _purpose_for(i, count, first_of_film, last_of_film)
        # Предпочтительный режим раздаётся позже, по всему фильму сразу:
        # здесь ещё не видно, сколько кадров поместится в цель покрытия.
        requirement = "normal"

        shots.append(
            {
                "order_index": i,
                "purpose": purpose,
                "shot_type": SHOT_TYPES[(motion_offset + i) % len(SHOT_TYPES)],
                "timeline_duration": seconds,
                # Сколько заказывать у провайдера — решается позже; пока
                # равно длине в монтаже.
                "generation_duration": seconds,
                "visual_prompt": _shot_prompt(
                    image_prompt, text, i, count, continuity,
                    authored[i] if i < len(authored) else None,
                ),
                "video_prompt": (authored[i].get("action") if i < len(authored) else None) or text or narration,
                "camera_motion": CAMERA_MOTIONS[(motion_offset + i) % len(CAMERA_MOTIONS)],
                "motion_requirement": requirement,
                # Важность решает, куда уйдёт дорогая генерация: по ней кадры
                # выстраиваются в очередь за настоящим видео.
                "visual_importance": PURPOSE_IMPORTANCE[purpose],
                "narrative_importance": 0.9 if (first_of_film or last_of_film) else PURPOSE_IMPORTANCE[purpose],
                # Кадры одной сцены обязаны выглядеть одним местом.
                "continuity_group": f"scene-{scene_index}",
                "generation_mode": "image_motion",
                "status": "planned",
            }
        )
    return shots


def _purpose_for(index: int, count: int, first_of_film: bool, last_of_film: bool) -> str:
    """Роль кадра в истории.

    Первый кадр фильма — крючок, последний — кульминация. Внутри сцены первый
    кадр ставит место действия, дальше чередуются действие и герой: именно на
    них зритель смотрит, и именно им достаётся дорогая генерация.
    """
    if first_of_film:
        return HOOK_PURPOSE
    if last_of_film:
        return CLIMAX_PURPOSE
    if index == 0 and count > 1:
        return "background"
    # «Подпирающий» кадр имеет смысл только там, где сцена длиннее двух кадров:
    # иначе вся сцена состоит из завязки и подпорки, а действия в ней нет.
    if count > 2 and index == count - 1:
        return "supporting"
    return "action" if index % 2 else "character"


def _shot_prompt(
    scene_prompt: str, shot_text: str, index: int, count: int,
    continuity: str = "", authored: dict | None = None,
) -> str:
    """Промпт кадра.

    Описание героев идёт первым и повторяется в каждом кадре — иначе генератор
    рисует новых людей каждые три секунды, и фильм разваливается на фотографии
    незнакомцев. Замер на готовом ролике: соседние кадры одной сцены отличались
    друг от друга на 48-60 единиц из 100, то есть на них были разные люди.

    Закадровый текст в промпт не попадает: он на языке зрителя, а генератор
    картинок понимает английский, и смешение языков портит кадр.
    """
    head = f"{continuity.strip()}. " if continuity.strip() else ""

    if authored:
        framing = (authored.get("framing") or "").strip()
        action = (authored.get("action") or "").strip()
        body = ", ".join(x for x in (framing, action) if x)
        return f"{head}{scene_prompt}. {body}"

    if count == 1:
        return f"{head}{scene_prompt}"
    framing = ("wide establishing shot", "medium shot", "close-up", "detail shot")
    return f"{head}{scene_prompt}. {framing[index % len(framing)]}"


def plan_film_shots(
    scenes: list[dict], style: str = "cinematic", continuity: str = "",
    mode: str = DEFAULT_MODE, requested_sec: float | None = None,
) -> list[list[dict]]:
    """Спланировать кадры всего фильма подряд.

    Движение камеры и крупность планов продолжаются сквозь границы сцен, а не
    начинаются заново: иначе ролик идёт «наезд, панорама, наезд, панорама».
    """
    plans: list[list[dict]] = []
    offset = 0
    for i, scene in enumerate(scenes):
        shots = plan_scene_shots(
            scene_index=i,
            scene_count=len(scenes),
            narration=scene.get("narration", ""),
            audio_duration_sec=float(scene.get("audio_duration_sec") or 0),
            image_prompt=scene.get("image_prompt", ""),
            style=style,
            motion_offset=offset,
            continuity=continuity,
            authored_shots=scene.get("shots"),
        )
        offset += len(shots)
        plans.append(shots)

    # Очередь за настоящим видео выстраивается по всему фильму сразу: внутри
    # одной сцены не видно, сколько кадров поместится в цель покрытия.
    flat = [s for scene_shots in plans for s in scene_shots]
    for position, shot in enumerate(flat):
        shot["order_index"] = position
    coverage = assign_generation_modes(flat, mode)

    total = sum(float(s["timeline_duration"]) for s in flat)
    log_plan(flat, requested_sec if requested_sec is not None else total, coverage)
    return plans
