"""Планировщик кадров.

Ни сети, ни денег: планировщик только режет время и текст. Проверяется то,
из-за чего ролик выглядел слайдшоу, и то, что легко сломать незаметно —
сумму длительностей.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from steps import shot_plan  # noqa: E402


def _plan(duration=6.7, narration="Первая фраза сцены. Вторая фраза сцены тоже здесь.", **kw):
    params = {
        "scene_index": 0,
        "scene_count": 4,
        "narration": narration,
        "audio_duration_sec": duration,
        "image_prompt": "cinematic vertical shot of two students in an empty classroom",
        "style": "cinematic",
    }
    params.update(kw)
    return shot_plan.plan_scene_shots(**params)


def test_scene_becomes_several_shots_instead_of_one_photo():
    """Прежняя сцена на 6.7 секунды была одной картинкой — отсюда слайдшоу."""
    shots = _plan(duration=6.7)
    assert len(shots) >= 2


def test_durations_sum_exactly_to_the_voice():
    """Голос — источник истины по длительности (CLAUDE.md §8).

    Расхождение здесь уводит таймлайн от озвучки, а субтитры — от таймлайна.
    Один раз это уже стоило проекту 0.217 с накопленного сдвига.
    """
    for duration in (2.0, 6.7, 9.123, 12.5, 30.0):
        shots = _plan(duration=duration)
        total = sum(s["timeline_duration"] for s in shots)
        assert abs(total - duration) < 0.001, f"{duration}: сумма {total}"


def test_every_shot_stays_within_readable_limits():
    for duration in (4.0, 6.7, 11.0, 20.0, 30.0):
        shots = _plan(duration=duration)
        for s in shots:
            assert s["timeline_duration"] <= shot_plan.MAX_SHOT_SEC + 0.001
            assert s["timeline_duration"] >= shot_plan.MIN_SHOT_SEC - 0.001


def test_thirty_second_film_lands_in_the_brief_range():
    """Бриф: на 30 секунд нужно 6-12 осмысленных кадров, а не 5 фотографий."""
    total = 0
    for i in range(4):
        total += len(_plan(duration=7.5, scene_index=i, scene_count=4))
    assert 6 <= total <= 12, f"кадров получилось {total}"


def test_shot_count_follows_pacing_not_a_constant():
    """Бриф прямо запрещает «всегда 10 кадров на любой проект»."""
    calm = shot_plan.shot_count(12.0, "documentary")
    fast = shot_plan.shot_count(12.0, "product")
    assert fast > calm


def test_very_short_scene_is_not_chopped_into_unreadable_pieces():
    shots = _plan(duration=2.4)
    assert len(shots) == 1
    assert shots[0]["timeline_duration"] == pytest.approx(2.4)


def test_first_shot_of_the_film_is_the_hook():
    """Зритель решает за первые секунды — этот кадр важнее всех."""
    shots = _plan(scene_index=0, scene_count=4)
    assert shots[0]["purpose"] == shot_plan.HOOK_PURPOSE
    assert shots[0]["visual_importance"] == 1.0


def test_last_shot_of_the_film_is_the_climax():
    shots = _plan(scene_index=3, scene_count=4)
    assert shots[-1]["purpose"] == shot_plan.CLIMAX_PURPOSE
    assert shots[-1]["visual_importance"] == shot_plan.PURPOSE_IMPORTANCE["climax"]


def test_neighbouring_shots_never_repeat_the_camera_move():
    """Одинаковое движение подряд превращает склейку в продолжение кадра."""
    shots = _plan(duration=20.0)
    moves = [s["camera_motion"] for s in shots]
    assert all(a != b for a, b in zip(moves, moves[1:])), moves


def test_shots_of_one_scene_share_a_continuity_group():
    shots = _plan(scene_index=2, scene_count=4, duration=10.0)
    assert {s["continuity_group"] for s in shots} == {"scene-2"}


def test_narration_is_split_without_losing_words():
    narration = "один два три четыре пять шесть семь восемь девять десять"
    shots = _plan(duration=12.0, narration=narration)
    joined = " ".join(s["video_prompt"] for s in shots).split()
    assert joined == narration.split()


def test_ken_burns_is_not_passed_off_as_real_video():
    """Бриф §18: IMAGE_MOTION нельзя выдавать за настоящее видео."""
    for s in _plan(duration=10.0):
        assert s["generation_mode"] == "image_motion"


def test_plan_rows_fit_the_shots_table():
    allowed = {
        "order_index", "purpose", "shot_type", "timeline_duration", "generation_duration",
        "visual_prompt", "video_prompt", "camera_motion", "motion_requirement",
        "visual_importance", "narrative_importance", "continuity_group",
        "generation_mode", "status",
    }
    for s in _plan(duration=10.0):
        assert set(s) <= allowed, set(s) - allowed


def _film(durations=(6.82, 7.24, 6.59, 6.08)):
    scenes = [
        {
            "narration": f"Фраза сцены {i + 1}. Вторая половина фразы сцены {i + 1}.",
            "audio_duration_sec": d,
            "image_prompt": f"cinematic vertical shot, scene {i + 1}",
        }
        for i, d in enumerate(durations)
    ]
    return scenes, shot_plan.plan_film_shots(scenes)


def test_camera_keeps_varying_across_scene_borders():
    """Камера не должна начинаться заново на каждой сцене.

    Без сквозного счётчика весь ролик шёл «наезд, панорама, наезд, панорама»:
    склейки формально есть, а камера одна и та же.
    """
    _, plans = _film()
    moves = [s["camera_motion"] for scene in plans for s in scene]
    assert all(a != b for a, b in zip(moves, moves[1:])), moves
    # На восьми кадрах однообразия быть не должно.
    assert len(set(moves)) >= 4, moves


def test_shot_sizes_also_vary_across_the_film():
    _, plans = _film()
    sizes = [s["shot_type"] for scene in plans for s in scene]
    assert all(a != b for a, b in zip(sizes, sizes[1:])), sizes


def test_film_keeps_every_scene_in_sync_with_its_voice():
    scenes, plans = _film()
    for scene, shots in zip(scenes, plans):
        total = sum(s["timeline_duration"] for s in shots)
        assert abs(total - scene["audio_duration_sec"]) < 0.001


def test_real_film_gets_more_shots_than_scenes():
    """Тот самый ролик «2 students businessmen»: было 4 фотографии."""
    _, plans = _film()
    count = sum(len(s) for s in plans)
    assert count >= 8, count


# --- постоянство героев и авторские кадры ---------------------------------

CAST = "ALEX, 16, short black hair, grey hoodie; SAM, 16, red curls, denim jacket"


def test_cast_description_goes_into_every_shot():
    """Без описания героев генератор рисует новых людей каждые три секунды.

    Замер на готовом ролике: соседние кадры одной сцены отличались на 48-60
    единиц из 100 — то есть на них были разные люди.
    """
    shots = _plan(duration=10.0, continuity=CAST)
    assert shots, "кадров не получилось"
    for s in shots:
        assert s["visual_prompt"].startswith(CAST), s["visual_prompt"][:80]


def test_narration_never_leaks_into_the_image_prompt():
    """Закадровый текст на языке зрителя, а генератор картинок понимает
    английский: смешение языков портит кадр."""
    narration = "Два подростка собрали первое приложение за одну ночь"
    for s in _plan(duration=10.0, narration=narration, continuity=CAST):
        assert "подростка" not in s["visual_prompt"]
        assert "ночь" not in s["visual_prompt"]


def test_shots_written_by_the_scriptwriter_are_used():
    """Сценарист задаёт минимум кадров, темп стиля может добавить ещё.

    Раньше авторское число побеждало целиком, и стиль вообще ни на что не
    влиял: размеренный документальный и быстрый продуктовый ролик резались
    одинаково.
    """
    authored = [
        {"framing": "wide establishing shot", "action": "both boys hunch over one laptop"},
        {"framing": "close-up on hands", "action": "fingers hammering the keyboard"},
    ]
    shots = _plan(duration=9.0, continuity=CAST, authored_shots=authored)
    assert len(shots) >= len(authored)
    assert "hunch over one laptop" in shots[0]["visual_prompt"]
    assert "fingers hammering" in shots[1]["visual_prompt"]


def test_authored_shots_are_dropped_when_they_would_be_too_short():
    """Три кадра на четыре секунды — нечитаемая нарезка."""
    authored = [{"framing": f"shot {i}", "action": f"action {i}"} for i in range(3)]
    shots = _plan(duration=4.0, authored_shots=authored)
    assert len(shots) == 2
    assert all(s["timeline_duration"] >= shot_plan.MIN_SHOT_SEC - 0.001 for s in shots)


def test_mechanics_still_work_without_a_scriptwriter():
    """Безопасный режим и старые проекты идут прежним путём."""
    shots = _plan(duration=10.0)
    assert len(shots) >= 2
    assert all(s["visual_prompt"] for s in shots)


def test_film_passes_the_cast_through_every_scene():
    scenes = [
        {"narration": "фраза сцены", "audio_duration_sec": 7.0,
         "image_prompt": f"cinematic shot, scene {i}",
         "shots": [{"framing": "wide shot", "action": f"action {i}a"},
                   {"framing": "close-up", "action": f"action {i}b"}]}
        for i in range(3)
    ]
    plans = shot_plan.plan_film_shots(scenes, continuity=CAST)
    flat = [s for scene in plans for s in scene]
    assert len(flat) == 6
    assert all(s["visual_prompt"].startswith(CAST) for s in flat)


def test_authored_shots_are_split_further_when_too_long():
    """Сценарист дал 3 кадра на 17 секунд — вышли куски по 5.8 с при потолке 5.

    Так возвращается слайдшоу: кадр длиннее пяти секунд снова читается как
    фотография с зумом.
    """
    authored = [{"framing": f"shot {i}", "action": f"action {i}"} for i in range(3)]
    shots = _plan(duration=17.4, authored_shots=authored)
    assert len(shots) >= 4, f"кадров {len(shots)}"
    for s in shots:
        assert s["timeline_duration"] <= shot_plan.MAX_SHOT_SEC + 0.001, s["timeline_duration"]
    assert abs(sum(s["timeline_duration"] for s in shots) - 17.4) < 0.001


# --- план на 30 секунд: количество, роли, покрытие -------------------------


def _thirty(style="cinematic", mode="smart", authored=2, duration=30.0, scenes_n=4):
    per = duration / scenes_n
    scenes = [
        {"narration": "фраза " * 20, "audio_duration_sec": per, "image_prompt": f"scene {i}",
         "shots": [{"framing": f"f{j}", "action": f"a{j}"} for j in range(authored)]}
        for i in range(scenes_n)
    ]
    plans = shot_plan.plan_film_shots(scenes, style=style, mode=mode, requested_sec=duration)
    return [s for p in plans for s in p]


def test_thirty_second_film_has_six_to_ten_shots():
    """Бриф: примерно 6-10 осмысленных кадров, а не пять длинных фотографий."""
    flat = _thirty()
    assert 6 <= len(flat) <= 10, len(flat)


def test_every_shot_lands_in_the_readable_window():
    for style in ("documentary", "cinematic", "explainer", "product"):
        for s in _thirty(style=style):
            assert 2.0 <= s["timeline_duration"] <= 5.0, (style, s["timeline_duration"])


def test_shot_count_is_not_hardcoded_to_eight():
    """Бриф прямо запрещает «всегда восемь кадров на любой проект»."""
    counts = {
        len(_thirty(style=style, duration=d))
        for style in ("documentary", "product")
        for d in (20.0, 30.0, 45.0)
    }
    assert len(counts) > 1, counts


def test_faster_style_cuts_more_often():
    assert len(_thirty(style="product", duration=45.0)) > len(_thirty(style="documentary", duration=45.0))


def test_order_index_is_continuous_across_the_film():
    """Индексы обязаны быть сквозными: по ним кадры собираются в таймлайн."""
    flat = _thirty()
    assert [s["order_index"] for s in flat] == list(range(len(flat)))


def test_the_priority_ladder_is_actually_used():
    flat = _thirty(authored=3, scenes_n=4, duration=40.0)
    purposes = {s["purpose"] for s in flat}
    assert shot_plan.HOOK_PURPOSE in purposes
    assert shot_plan.CLIMAX_PURPOSE in purposes
    assert purposes & {"action", "character"}, purposes
    assert "background" in purposes


def test_hook_and_climax_outrank_background():
    flat = _thirty()
    hook = next(s for s in flat if s["purpose"] == shot_plan.HOOK_PURPOSE)
    climax = next(s for s in flat if s["purpose"] == shot_plan.CLIMAX_PURPOSE)
    background = [s for s in flat if s["purpose"] == "background"]
    assert background, "фоновых кадров не оказалось"
    for low in background:
        assert hook["visual_importance"] > low["visual_importance"]
        assert climax["visual_importance"] > low["visual_importance"]


def _coverage(flat):
    total = sum(s["timeline_duration"] for s in flat)
    real = sum(s["timeline_duration"] for s in flat if shot_plan.preferred_mode(s) == "real_video")
    return real / total


def test_smart_mode_aims_at_seventy_percent_real_video():
    """Цель брифа для SMART — около 70% таймлайна настоящим видео."""
    assert 0.65 <= _coverage(_thirty(mode="smart")) <= 0.80


def test_cinematic_mode_aims_higher_and_preview_asks_for_nothing():
    assert _coverage(_thirty(mode="cinematic")) >= 0.85
    assert _coverage(_thirty(mode="preview")) == 0.0


def test_the_hook_is_always_first_in_the_queue_for_real_video():
    """Статичная заставка в первых секундах запрещена брифом."""
    for mode in ("draft", "smart", "cinematic"):
        flat = _thirty(mode=mode)
        hook = next(s for s in flat if s["purpose"] == shot_plan.HOOK_PURPOSE)
        assert shot_plan.preferred_mode(hook) == "real_video", mode


def test_expensive_generation_goes_to_important_shots_first():
    """Бюджет делится не поровну: дорогое достаётся тому, что заметят."""
    flat = _thirty(mode="draft")
    chosen = [s for s in flat if shot_plan.preferred_mode(s) == "real_video"]
    skipped = [s for s in flat if shot_plan.preferred_mode(s) == "image_motion"]
    assert chosen and skipped
    assert min(s["visual_importance"] for s in chosen) >= max(s["visual_importance"] for s in skipped)


def test_planning_never_marks_a_shot_as_already_generated():
    """План — это намерение. Настоящим видео кадр становится только у провайдера."""
    for s in _thirty(mode="cinematic"):
        assert s["generation_mode"] == "image_motion"


def test_plan_rows_still_fit_the_shots_table():
    allowed = {
        "order_index", "purpose", "shot_type", "timeline_duration", "generation_duration",
        "visual_prompt", "video_prompt", "camera_motion", "motion_requirement",
        "visual_importance", "narrative_importance", "continuity_group",
        "generation_mode", "status",
    }
    for s in _thirty():
        assert set(s) <= allowed, set(s) - allowed


def test_plan_is_logged_in_the_agreed_format(caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="worker.shot_plan"):
        _thirty()
    text = caplog.text
    assert "[SHOT PLAN]" in text
    assert "Requested duration: 30.0s" in text
    assert "Total shots:" in text
    assert "purpose=HOOK" in text
    assert "preferred_mode=REAL_VIDEO" in text
    assert "Planned REAL_VIDEO coverage target:" in text
