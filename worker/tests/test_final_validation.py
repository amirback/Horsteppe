"""Проверка финального MP4 по критериям CLAUDE.md §8.

Артефакт задачи «валидация результата». Сеть не используется: файлы для
проверки собираются локально тем же ffmpeg, что и в продакшене.

Смысл теста — доказать, что валидация ловит именно тот случай, который
раньше проходил незамеченным: чёрное видео нужной длины с тишиной.

Запуск (из каталога worker):
    PYTHONUTF8=1 python -m unittest discover -s tests -v
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import media  # noqa: E402

SIZE = (320, 568)  # маленький вертикальный кадр — тесты должны быть быстрыми


def _ffmpeg(args: list[str]) -> None:
    cmd = [media.ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-800:])


def _make(path: Path, *, color: str, tone: bool, seconds: float = 3.0,
          size: tuple[int, int] = SIZE, moving: bool = True) -> Path:
    """Собрать тестовый ролик: цвет фона, наличие звука и движения."""
    w, h = size
    video = f"color=c={color}:s={w}x{h}:r=30"
    if moving:
        # Бегущая полоса — чтобы последний кадр отличался от предыдущих.
        video = f"testsrc=size={w}x{h}:rate=30"
    audio = "sine=frequency=440:sample_rate=44100" if tone else "anullsrc=r=44100:cl=stereo"
    _ffmpeg([
        "-f", "lavfi", "-i", video,
        "-f", "lavfi", "-i", audio,
        "-t", f"{seconds}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(path),
    ])
    return path


class FinalValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_good_video_passes(self) -> None:
        f = _make(self.dir / "good.mp4", color="white", tone=True)
        report = media.validate_final(f, SIZE)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["has_audio"])
        self.assertEqual((report["width"], report["height"]), SIZE)

    def test_black_and_silent_is_flagged(self) -> None:
        """Именно этот файл раньше проходил как готовый."""
        f = _make(self.dir / "black.mp4", color="black", tone=False, moving=False)
        report = media.validate_final(f, SIZE)
        joined = " | ".join(report["warnings"])
        self.assertIn("чёрный", joined, report)
        self.assertIn("тихий", joined, report)
        self.assertTrue(report["frozen_ending"], "застывший финал не замечен")

    def test_missing_audio_is_an_error(self) -> None:
        f = self.dir / "mute.mp4"
        _ffmpeg([
            "-f", "lavfi", "-i", f"testsrc=size={SIZE[0]}x{SIZE[1]}:rate=30",
            "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(f),
        ])
        report = media.validate_final(f, SIZE)
        self.assertFalse(report["ok"])
        self.assertIn("нет аудиопотока", report["errors"])

    def test_wrong_resolution_is_an_error(self) -> None:
        f = _make(self.dir / "wide.mp4", color="white", tone=True, size=(640, 360))
        report = media.validate_final(f, SIZE)
        self.assertFalse(report["ok"])
        self.assertTrue(
            any("разрешение" in e for e in report["errors"]), report["errors"]
        )

    def test_missing_file_is_an_error(self) -> None:
        report = media.validate_final(self.dir / "нет-такого.mp4", SIZE)
        self.assertFalse(report["ok"])
        self.assertIn("отсутствует", report["errors"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
