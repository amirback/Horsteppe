"""Безопасный режим: ноль платных вызовов при MVP_SAFE_MODE=1.

Артефакт задачи по CLAUDE.md §6.

Сеть блокируется физически: `socket.socket` подменяется на класс, который
бросает исключение при попытке создания. Поэтому тест доказывает не то, что
код «выглядит правильным», а то, что наружу не уходит ни одного соединения.
FFmpeg работает отдельным процессом и под запрет не попадает — именно так
и должно быть: локальные заменители обязаны работать без сети.

Запуск (из каталога worker):
    PYTHONUTF8=1 python -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import safe_mode  # noqa: E402
from config import Config  # noqa: E402
from steps import image_step, tts_step, video_step  # noqa: E402

# Значения-пустышки: настоящие ключи для безопасного режима не нужны,
# но Config без них не собирается.
BASE_ENV = {
    "SUPABASE_URL": "https://example.invalid",
    "SUPABASE_SERVICE_ROLE_KEY": "not-a-real-key",
    "ELEVENLABS_API_KEY": "not-a-real-key",
    "FAL_KEY": "not-a-real-key",
    # Нужен только для сборки конфига при MVP_SAFE_MODE=0: без него валидация
    # справедливо требует ключ для SCRIPT_MODE=llm.
    "ANTHROPIC_API_KEY": "not-a-real-key",
}


class NetworkBlocked(AssertionError):
    """Попытка выйти в сеть в безопасном режиме."""


class _BlockedSocket:
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NetworkBlocked("безопасный режим не должен открывать соединения")


def no_network() -> mock._patch:
    return mock.patch.object(socket, "socket", _BlockedSocket)


def make_config(**overrides: str) -> Config:
    env = {**BASE_ENV, **overrides}
    with mock.patch.dict(os.environ, env, clear=False):
        return Config()


class FlagDefaultsTest(unittest.TestCase):
    def test_safe_by_default(self) -> None:
        env = dict(BASE_ENV)
        env.pop("MVP_SAFE_MODE", None)
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("MVP_SAFE_MODE", None)
            self.assertTrue(Config().mvp_safe_mode, "по умолчанию режим обязан быть безопасным")

    def test_empty_value_stays_safe(self) -> None:
        """Ошибка в .env не должна открывать кошелёк."""
        self.assertTrue(make_config(MVP_SAFE_MODE="").mvp_safe_mode)
        self.assertTrue(make_config(MVP_SAFE_MODE="   ").mvp_safe_mode)

    def test_explicit_zero_opens_paid_path(self) -> None:
        self.assertFalse(make_config(MVP_SAFE_MODE="0").mvp_safe_mode)
        self.assertFalse(make_config(MVP_SAFE_MODE="false").mvp_safe_mode)


class DowngradeTest(unittest.TestCase):
    def test_premium_video_downgraded_to_local_motion(self) -> None:
        cfg = make_config(MVP_SAFE_MODE="1", VIDEO_MODE="provider")
        self.assertEqual(cfg.effective_video_mode, "kenburns")
        # Исходное решение сохраняется — понижается только исполнение.
        self.assertEqual(cfg.video_mode, "provider")

    def test_llm_downgraded_to_template(self) -> None:
        cfg = make_config(MVP_SAFE_MODE="1", SCRIPT_MODE="llm", ANTHROPIC_API_KEY="x")
        self.assertEqual(cfg.effective_script_mode, "mock")
        self.assertEqual(cfg.script_mode, "llm")

    def test_paid_mode_keeps_choice(self) -> None:
        cfg = make_config(MVP_SAFE_MODE="0", VIDEO_MODE="provider")
        self.assertEqual(cfg.effective_video_mode, "provider")


class ZeroOutgoingCallsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.cfg = make_config(MVP_SAFE_MODE="1", VIDEO_MODE="provider")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_image_step_uses_local_placeholder(self) -> None:
        out = self.dir / "frame.png"
        with no_network():
            cost = image_step.generate_image(self.cfg, "марсианская буря на рассвете", out, index=2)
        self.assertEqual(cost, 0.0)
        self.assertTrue(out.exists() and out.stat().st_size > 0, "кадр-заглушка не создан")

    def test_tts_step_uses_local_silence(self) -> None:
        out = self.dir / "voice.mp3"
        text = "Последний астронавт на Земле слышит сигнал из пустого города."
        with no_network():
            cost = tts_step.synthesize(self.cfg, text, out)
        self.assertEqual(cost, 0.0)
        self.assertTrue(out.exists() and out.stat().st_size > 0, "озвучка-заглушка не создана")

        import media
        seconds = media.exact_duration_sec(out)
        self.assertGreater(seconds, 2.0, "длительность должна зависеть от числа слов")

    def test_video_step_refuses_to_run(self) -> None:
        with no_network(), self.assertRaises(safe_mode.PaidCallBlocked):
            video_step.generate_clip(
                self.cfg, "https://example.invalid/f.png", "наезд", self.dir / "clip.mp4"
            )

    def test_guard_is_the_single_source_of_truth(self) -> None:
        self.assertFalse(safe_mode.is_paid_allowed(self.cfg))
        self.assertFalse(safe_mode.is_paid_video_allowed(self.cfg))
        paid = make_config(MVP_SAFE_MODE="0", VIDEO_MODE="provider")
        self.assertTrue(safe_mode.is_paid_allowed(paid))
        self.assertTrue(safe_mode.is_paid_video_allowed(paid))

    def test_network_block_itself_works(self) -> None:
        """Проверка самого предохранителя: без него тест выше ничего не доказывает."""
        with no_network(), self.assertRaises(NetworkBlocked):
            socket.socket()


if __name__ == "__main__":
    unittest.main(verbosity=2)
