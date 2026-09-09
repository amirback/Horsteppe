"""Поведение при зависшем внешнем вызове.

Артефакт задачи «таймауты» по CLAUDE.md §6.

Сеть не используется: модуль `fal_client` подменяется заглушкой, которая
имитирует зависание. Тест проверяет не то, что код «выглядит правильно», а то,
что управление возвращается воркеру за отведённое время.

Запуск (из каталога worker):
    PYTHONUTF8=1 python -m unittest discover -s tests -v
"""
from __future__ import annotations

import sys
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

from steps._timeout import CallTimeout, call_with_timeout  # noqa: E402

# Запас, за который тест обязан уложиться. Если вызов не прерывается, тест
# не «медленный» — он провален по существу.
BUDGET_SEC = 5.0
HANG_SEC = 60.0
SHORT_TIMEOUT = 0.3


def _hang(*_args: object, **_kwargs: object) -> None:
    """Имитация зависшего провайдера: спит дольше любого разумного таймаута."""
    time.sleep(HANG_SEC)


class FakeConfig:
    """Минимальный конфиг: только поля, которые читают шаги.

    `mvp_safe_mode = False` здесь обязателен: иначе барьер безопасного режима
    подменит вызов локальной заглушкой и проверять таймаут будет нечего.
    """

    mvp_safe_mode = False
    video_mode = "provider"
    # Тест проверяет именно платный путь fal, поэтому провайдер задан явно.
    image_provider = "fal"
    fal_key = "test-key-not-a-secret"
    fal_image_model = "fake/image-model"
    fal_video_model = "fake/video-model"


def _install_fake_fal(subscribe) -> mock._patch:
    """Подменить модуль fal_client заглушкой на время теста."""
    fake = types.ModuleType("fal_client")
    fake.subscribe = subscribe  # type: ignore[attr-defined]
    return mock.patch.dict(sys.modules, {"fal_client": fake})


class BoundedCallTest(unittest.TestCase):
    def test_hung_call_aborts_within_budget(self) -> None:
        started = time.monotonic()
        with self.assertRaises(CallTimeout) as ctx:
            call_with_timeout(_hang, timeout=SHORT_TIMEOUT, label="fake.provider")
        elapsed = time.monotonic() - started

        self.assertLess(
            elapsed, BUDGET_SEC,
            f"управление вернулось за {elapsed:.1f} с — вызов не был прерван",
        )
        self.assertIn("fake.provider", str(ctx.exception))

    def test_normal_call_returns_value(self) -> None:
        result = call_with_timeout(lambda a, b: a + b, 2, b=3, timeout=5, label="fake.ok")
        self.assertEqual(result, 5)

    def test_original_exception_is_not_swallowed(self) -> None:
        def boom() -> None:
            raise ValueError("провайдер вернул ошибку")

        with self.assertRaises(ValueError):
            call_with_timeout(boom, timeout=5, label="fake.err")

    def test_worker_thread_is_daemon(self) -> None:
        """Брошенный поток не должен задерживать завершение процесса."""
        seen: list[bool] = []

        def probe() -> None:
            seen.append(threading.current_thread().daemon)

        call_with_timeout(probe, timeout=5, label="fake.daemon")
        self.assertEqual(seen, [True])


class ImageStepTimeoutTest(unittest.TestCase):
    def test_hang_becomes_image_error(self) -> None:
        from steps import image_step

        with _install_fake_fal(_hang), mock.patch.object(image_step, "TIMEOUT_SEC", SHORT_TIMEOUT):
            started = time.monotonic()
            with self.assertRaises(image_step.ImageError) as ctx:
                image_step.generate_image(
                    FakeConfig(), "тестовый промпт", WORKER_DIR / "tests" / "_never_written.png"
                )
            elapsed = time.monotonic() - started

        self.assertLess(elapsed, BUDGET_SEC, "шаг генерации кадра не прервался")
        self.assertIn("fal.image", str(ctx.exception))
        self.assertFalse(
            (WORKER_DIR / "tests" / "_never_written.png").exists(),
            "при таймауте файл создаваться не должен",
        )


class VideoStepTimeoutTest(unittest.TestCase):
    def test_hang_becomes_video_error(self) -> None:
        from steps import video_step

        with _install_fake_fal(_hang), mock.patch.object(video_step, "TIMEOUT_SEC", SHORT_TIMEOUT):
            started = time.monotonic()
            with self.assertRaises(video_step.VideoError) as ctx:
                video_step.generate_clip(
                    FakeConfig(),
                    "https://example.invalid/frame.png",
                    "медленный наезд камеры",
                    WORKER_DIR / "tests" / "_never_written.mp4",
                )
            elapsed = time.monotonic() - started

        self.assertLess(elapsed, BUDGET_SEC, "шаг генерации клипа не прервался")
        self.assertIn("fal.video", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
