"""Сквозной прогон конвейера без единого ключа и без сети.

Артефакт задачи «сквозной прогон» по CLAUDE.md §6.

Что здесь проверяется: настоящий `pipeline.run_project` — тот самый код,
который выполняется в продакшене, — от постановки задачи до готового MP4.
Подменяется только база: вместо Supabase используется словарь в памяти,
а «загрузка в хранилище» пишет файл на диск.

Почему это возможно без ключей. При `MVP_SAFE_MODE=1` каждый платный шаг
заменяется локальным: сценарий берётся из шаблона, кадр рисуется FFmpeg,
вместо озвучки создаётся тишина нужной длины. Сеть при этом заблокирована
на уровне `socket.socket`, поэтому «зато оно тихо сходило в интернет» —
исключено.

Запуск (из каталога worker):
    PYTHONUTF8=1 python -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any
from unittest import mock

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import media  # noqa: E402
import pipeline  # noqa: E402
from config import Config  # noqa: E402

BASE_ENV = {
    "SUPABASE_URL": "https://example.invalid",
    "SUPABASE_SERVICE_ROLE_KEY": "not-a-real-key",
    "ELEVENLABS_API_KEY": "not-a-real-key",
    "FAL_KEY": "not-a-real-key",
    "ANTHROPIC_API_KEY": "not-a-real-key",
    "MVP_SAFE_MODE": "1",
}


class NetworkBlocked(AssertionError):
    """Попытка выйти в сеть во время сквозного прогона."""


class _BlockedSocket:
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NetworkBlocked("сквозной прогон в безопасном режиме не должен ходить в сеть")


class FakeDb:
    """База в памяти: ровно те методы, которые вызывает конвейер."""

    def __init__(self, storage_dir: Path, project: dict[str, Any]) -> None:
        self.storage = storage_dir
        self.project = project
        self.scenes: list[dict[str, Any]] = []
        self.shots: list[dict[str, Any]] = []
        self.progress: list[str] = []
        self.costs: list[tuple[str, str, float]] = []
        self.renders: list[tuple[str, float]] = []

    # --- проект ---
    def get_project(self, project_id: str) -> dict[str, Any]:
        return self.project

    def update_project(self, project_id: str, **fields: Any) -> None:
        self.project.update(fields)

    def set_progress(self, project_id: str, detail: str) -> None:
        self.progress.append(detail)

    # --- сцены ---
    def get_scenes(self, project_id: str) -> list[dict[str, Any]]:
        return self.scenes

    def insert_scenes(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for row in rows:
            self.scenes.append({"id": str(uuid.uuid4()), **row})
        return self.scenes

    def update_scene(self, scene_id: str, **fields: Any) -> None:
        for scene in self.scenes:
            if scene["id"] == scene_id:
                scene.update(fields)
                return
        raise AssertionError(f"сцена {scene_id} не найдена")

    # --- кадры ---
    def get_shots(self, project_id: str) -> list[dict[str, Any]]:
        return self.shots

    def insert_shots(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for row in rows:
            self.shots.append({"id": str(uuid.uuid4()), **row})
        return self.shots

    def update_shot(self, shot_id: str, **fields: Any) -> None:
        for shot in self.shots:
            if shot["id"] == shot_id:
                shot.update(fields)
                return
        raise AssertionError(f"кадр {shot_id} не найден")

    # --- побочные записи ---
    def log_cost(self, project_id: str, step: str, provider: str, amount_usd: float, detail: str = "") -> None:
        self.costs.append((step, provider, amount_usd))

    def insert_render(self, project_id: str, url: str, duration_sec: float) -> None:
        self.renders.append((url, duration_sec))

    def upload(self, path: str, data: bytes, content_type: str | None = None) -> str:
        dest = self.storage / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest.as_uri()


class PipelineEndToEndTest(unittest.TestCase):
    """Один прогон, много утверждений: пересобирать ролик на каждую проверку дорого."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        cls.storage = root / "storage"
        cls.storage.mkdir()

        with mock.patch.dict(os.environ, BASE_ENV, clear=False):
            cls.cfg = Config()

        cls.project_id = str(uuid.uuid4())
        cls.db = FakeDb(cls.storage, {
            "id": cls.project_id,
            "topic": "Последний астронавт на Земле слышит сигнал из пустого города",
            "style": "cinematic",
            "duration_sec": 20,
            "aspect_ratio": "9:16",
        })

        with mock.patch.object(socket, "socket", _BlockedSocket):
            pipeline.run_project(cls.cfg, cls.db, cls.project_id)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    # --- итог ---
    def test_project_marked_done(self) -> None:
        self.assertEqual(self.db.project["status"], "done", self.db.project.get("error_message"))
        self.assertIsNone(self.db.project.get("error_message"))

    def test_final_video_exists_and_is_valid(self) -> None:
        self.assertEqual(len(self.db.renders), 1, "рендер не записан")
        url, duration = self.db.renders[0]
        final = Path(self.storage / f"projects/{self.project_id}/final.mp4")
        self.assertTrue(final.exists(), f"файл не создан: {url}")
        self.assertGreater(final.stat().st_size, 10_000, "файл подозрительно мал")

        report = media.validate_final(final, media.frame_size("9:16"))
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual((report["width"], report["height"]), (1080, 1920))
        self.assertTrue(report["has_audio"])
        self.assertAlmostEqual(report["duration_sec"], duration, places=1)

    def test_duration_follows_the_voice_track(self) -> None:
        """CLAUDE.md §8: источник истины по длительности — голос, а не запрос."""
        _, duration = self.db.renders[0]
        voiced = sum(float(s["audio_duration_sec"]) for s in self.db.scenes)
        self.assertAlmostEqual(duration, voiced, places=1)

    def test_every_scene_produced_assets(self) -> None:
        """Озвучка живёт на сцене, картинка — на кадре."""
        self.assertGreaterEqual(len(self.db.scenes), 2)
        for scene in self.db.scenes:
            self.assertTrue(scene.get("audio_url"), f"нет озвучки: сцена {scene['order_index']}")
            self.assertEqual(scene["status"], "audio_done")

        self.assertGreaterEqual(len(self.db.shots), 2)
        for shot in self.db.shots:
            self.assertTrue(shot.get("image_url"), f"нет картинки: кадр {shot['order_index']}")
            self.assertEqual(shot["status"], "image_done")

    def test_film_is_cut_into_more_shots_than_scenes(self) -> None:
        """Главная защита от возврата слайдшоу: кадров больше, чем сцен."""
        self.assertGreater(len(self.db.shots), len(self.db.scenes))

    def test_shots_stay_in_sync_with_the_voice(self) -> None:
        """Сумма кадров сцены обязана равняться её озвучке."""
        for scene in self.db.scenes:
            planned = sum(
                float(s["timeline_duration"])
                for s in self.db.shots
                if s["scene_id"] == scene["id"]
            )
            self.assertAlmostEqual(planned, float(scene["audio_duration_sec"]), places=2)

    def test_local_motion_is_not_passed_off_as_real_video(self) -> None:
        """Бриф §18: движение по картинке нельзя выдавать за настоящее видео."""
        for shot in self.db.shots:
            self.assertEqual(shot["generation_mode"], "image_motion")

    def test_neighbouring_shots_differ_in_camera_move(self) -> None:
        moves = [s["camera_motion"] for s in self.db.shots]
        self.assertTrue(all(a != b for a, b in zip(moves, moves[1:])), moves)

    def test_nothing_was_paid_for(self) -> None:
        self.assertTrue(self.db.costs, "траты вообще не записывались — учёт сломан")
        total = sum(amount for _, _, amount in self.db.costs)
        self.assertEqual(total, 0.0, f"безопасный режим потратил {total}$: {self.db.costs}")

    def test_progress_was_reported_truthfully(self) -> None:
        """Прогресс должен приходить из конвейера, а не рисоваться фронтендом."""
        self.assertTrue(any("Озвучка" in p for p in self.db.progress), self.db.progress)
        self.assertTrue(any("Кадры" in p for p in self.db.progress), self.db.progress)
        self.assertTrue(any("Монтаж" in p for p in self.db.progress), self.db.progress)
        self.assertTrue(any("Проверка" in p for p in self.db.progress), self.db.progress)

    def test_work_directory_cleaned_up(self) -> None:
        from config import TMP_DIR
        self.assertFalse((TMP_DIR / self.project_id).exists(), "временные файлы не убраны")


if __name__ == "__main__":
    unittest.main(verbosity=2)
