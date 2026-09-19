"""Выбор «с голосом или без».

Диктор нужен не всякой рекламе: у многих роликов только картинка и музыка.
Проверяется то, что легко сломать незаметно — источник длительности. Обычно
это голос; без него единственный ориентир — заказ человека, и ошибка здесь
схлопывает ролик в ноль.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pipeline  # noqa: E402


class FakeDb:
    def __init__(self):
        self.updates: list[tuple] = []

    def update_scene(self, scene_id, **fields):
        self.updates.append((scene_id, fields))


def test_voiceover_is_on_unless_switched_off():
    """Прежние проекты не должны молча онеметь."""
    assert pipeline._wants_voiceover({}) is True
    assert pipeline._wants_voiceover({"brief": {}}) is True
    assert pipeline._wants_voiceover({"brief": {"voiceover": True}}) is True


def test_voiceover_off_is_respected():
    assert pipeline._wants_voiceover({"brief": {"voiceover": False}}) is False


def test_silent_scenes_split_the_requested_duration():
    """Без голоса время делится поровну между сценами."""
    db = FakeDb()
    scenes = [{"id": f"s{i}"} for i in range(3)]
    pipeline._plan_silent_scenes(db, "p", scenes, 15.0)
    assert [s["audio_duration_sec"] for s in scenes] == [5.0, 5.0, 5.0]
    assert all(f["status"] == "audio_done" for _, f in db.updates)


def test_silent_scenes_never_get_zero_length():
    """Ноль длительности схлопнул бы раскадровку и оставил пустой файл."""
    db = FakeDb()
    scenes = [{"id": "s0"}, {"id": "s1"}]
    pipeline._plan_silent_scenes(db, "p", scenes, 0.0)
    assert all(s["audio_duration_sec"] > 0 for s in scenes)


def test_already_timed_scenes_are_left_alone():
    """Повтор проекта не должен переписывать готовые длительности."""
    db = FakeDb()
    scenes = [{"id": "s0", "audio_duration_sec": 7.5}]
    pipeline._plan_silent_scenes(db, "p", scenes, 30.0)
    assert scenes[0]["audio_duration_sec"] == 7.5
    assert db.updates == []


def test_render_plan_puts_silence_where_the_voice_would_be(tmp_path):
    """Монтаж считает длительность по звуку: без дорожки сцена станет нулевой."""
    scene = {"id": "s0", "audio_duration_sec": 4.0, "narration": "текст, который не прозвучит"}
    shots = [{
        "scene_id": "s0", "order_index": 0, "timeline_duration": 4.0,
        "camera_motion": "push_in", "shot_type": "wide",
        "image_url": "https://example/i.png",
    }]

    saved = pipeline._download
    pipeline._download = lambda url, dest: dest
    try:
        plan = pipeline._render_plan(shots, [scene], tmp_path)
    finally:
        pipeline._download = saved

    audio = Path(plan[0]["audio_path"])
    assert audio.exists(), "дорожка тишины не создана"
    # Закадровый текст в план не попадает: субтитрам нечего показывать.
    assert plan[0]["narration"] == ""


def test_render_plan_keeps_the_voice_when_it_exists(tmp_path):
    scene = {"id": "s0", "audio_duration_sec": 4.0, "narration": "фраза",
             "audio_url": "https://example/a.mp3"}
    shots = [{
        "scene_id": "s0", "order_index": 0, "timeline_duration": 4.0,
        "camera_motion": "push_in", "shot_type": "wide",
        "image_url": "https://example/i.png",
    }]
    saved = pipeline._download
    pipeline._download = lambda url, dest: dest
    try:
        plan = pipeline._render_plan(shots, [scene], tmp_path)
    finally:
        pipeline._download = saved
    assert plan[0]["narration"] == "фраза"
