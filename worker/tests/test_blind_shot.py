"""Один кадр без картинки не должен стоить целого фильма.

Асимметрия, из-за которой появился файл. Сбой дорогого видео конвейер
переживал: кадр оставался движением по фотографии, ролик собирался,
покрытие честно падало. Сбой дешёвой картинки ронял проект целиком — а
картинки делают бесплатные и самые капризные провайдеры.

Выбросить кадр просто так тоже нельзя: сцена длится ровно столько, сколько
говорит диктор, и пропавшее время оставило бы дыру, сдвинув весь ролик.
Поэтому время уходит соседу по сцене.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pipeline  # noqa: E402


def _shot(scene: str, order: int, duration: float, *, image=None, video=None) -> dict:
    return {
        "id": f"s{order}", "scene_id": scene, "order_index": order,
        "timeline_duration": duration,
        "image_url": image, "video_url": video,
    }


def _total(shots: list[dict]) -> float:
    return round(sum(float(s["timeline_duration"]) for s in shots), 3)


def test_everything_intact_is_left_alone():
    shots = [_shot("a", 0, 2.0, image="i0"), _shot("a", 1, 3.0, image="i1")]
    assert pipeline._drop_blind_shots(shots) == shots


def test_blind_shot_is_dropped():
    shots = [_shot("a", 0, 2.0, image="i0"), _shot("a", 1, 3.0)]
    alive = pipeline._drop_blind_shots(shots)
    assert [s["order_index"] for s in alive] == [0]


def test_scene_keeps_its_exact_length():
    """Главное: длина сцены не меняется, иначе поедет весь монтаж."""
    shots = [_shot("a", 0, 2.0, image="i0"), _shot("a", 1, 3.0), _shot("a", 2, 1.5, image="i2")]
    before = _total(shots)
    alive = pipeline._drop_blind_shots(shots)
    assert _total(alive) == before


def test_time_goes_to_the_neighbour_on_the_left():
    shots = [_shot("a", 0, 2.0, image="i0"), _shot("a", 1, 3.0), _shot("a", 2, 1.5, image="i2")]
    alive = pipeline._drop_blind_shots(shots)
    by_order = {s["order_index"]: s["timeline_duration"] for s in alive}
    assert by_order[0] == 5.0, "время пропавшего кадра должно достаться предыдущему"
    assert by_order[2] == 1.5


def test_first_shot_lost_gives_its_time_forward():
    """Слева соседа нет — берёт следующий."""
    shots = [_shot("a", 0, 2.0), _shot("a", 1, 3.0, image="i1")]
    alive = pipeline._drop_blind_shots(shots)
    assert len(alive) == 1
    assert alive[0]["timeline_duration"] == 5.0


def test_a_real_clip_counts_as_usable():
    shots = [_shot("a", 0, 2.0, video="v0"), _shot("a", 1, 3.0)]
    alive = pipeline._drop_blind_shots(shots)
    assert alive[0]["video_url"] == "v0"
    assert alive[0]["timeline_duration"] == 5.0


def test_scenes_do_not_borrow_from_each_other():
    """Время пропавшего кадра остаётся внутри своей сцены.

    Иначе одна сцена стала бы длиннее своей озвучки, а другая короче.
    """
    shots = [
        _shot("a", 0, 2.0, image="i0"), _shot("a", 1, 3.0),
        _shot("b", 2, 4.0, image="i2"),
    ]
    alive = pipeline._drop_blind_shots(shots)
    by_scene = {}
    for s in alive:
        by_scene.setdefault(s["scene_id"], 0.0)
        by_scene[s["scene_id"]] += float(s["timeline_duration"])
    assert by_scene["a"] == 5.0
    assert by_scene["b"] == 4.0


def test_a_scene_that_lost_everything_is_reported_not_hidden():
    """Здесь чинить нечего — вызывающий обязан считать это отказом."""
    shots = [_shot("a", 0, 2.0), _shot("a", 1, 3.0)]
    assert pipeline._drop_blind_shots(shots) == []


def test_dropped_shots_do_not_shift_temp_file_names():
    """Имя временного файла берётся из самого кадра, а не из позиции.

    После выпадения кадра позиции съезжают, и следующий кадр забрал бы себе
    уже скачанный файл соседа — молча и не тот.
    """
    source = (Path(__file__).resolve().parents[1] / "pipeline.py").read_text(encoding="utf-8")
    plan = source[source.index("def _render_plan"):source.index("def _scene_shots") if "def _scene_shots" in source else len(source)]
    assert "for shot in _drop_blind_shots(shots):" in plan, "позиция снова используется как номер"
    assert 'i = int(shot.get("order_index") or 0)' in plan
