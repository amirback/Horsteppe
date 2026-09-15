"""Инспектор качества на настоящих файлах.

Проверяется главное различие: файл может быть технически безупречным и при
этом оставаться слайдшоу. `validate_final` такой ролик пропускает — она для
этого и не предназначена, — а инспектор обязан его назвать.

Ни сети, ни ключей, ни денег: все ролики строятся FFmpeg на месте.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import media  # noqa: E402
import quality  # noqa: E402

SIZE = (180, 320)


def build(path: Path, source: str, seconds: float) -> None:
    """Собрать ролик из фильтра lavfi со звуком: без звука проверка не пройдёт."""
    media.run_ffmpeg([
        "-f", "lavfi", "-i", source,
        "-f", "lavfi", "-i", "anoisesrc=c=pink:a=0.3",
        "-t", f"{seconds}", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-shortest", str(path),
    ])


def still(path: Path, seconds: float) -> None:
    """Неподвижная картинка — тот самый случай, ради которого всё затевалось."""
    build(path, f"color=c=slategray:size={SIZE[0]}x{SIZE[1]}:rate=30", seconds)


def moving(path: Path, seconds: float) -> None:
    build(path, f"testsrc2=size={SIZE[0]}x{SIZE[1]}:rate=30", seconds)


def shots(count: int, seconds: float, real: int = 0) -> list[dict]:
    return [
        {
            "id": f"shot-{i}", "timeline_duration": seconds / count,
            "image_url": "https://example/img.png",
            **({"video_url": "https://example/clip.mp4", "generation_mode": "real_video"}
               if i < real else {"generation_mode": "image_motion"}),
        }
        for i in range(count)
    ]


class TestSlideshowIsNamed(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        cls.still_video = root / "still.mp4"
        still(cls.still_video, 8)
        cls.report = quality.inspect(cls.still_video, SIZE, shots(3, 8))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_technically_valid_file_still_fails_the_eye(self) -> None:
        """`validate_final` такой ролик пропускает — в этом и была проблема."""
        base = media.validate_final(self.still_video, SIZE)
        self.assertTrue(base["ok"])
        self.assertIn("SLIDESHOW", [i.kind for i in self.report.issues])

    def test_dead_opening_is_called_out(self) -> None:
        kinds = [i.kind for i in self.report.issues]
        self.assertIn("STATIC_OPENING", kinds)

    def test_frozen_sections_are_located_in_time(self) -> None:
        self.assertTrue(self.report.frozen_sections)
        start, length = self.report.frozen_sections[0]
        self.assertGreaterEqual(length, quality.MAX_STATIC_HOLD_SEC)
        self.assertGreaterEqual(start, 0.0)

    def test_frozen_section_points_at_a_shot_to_repair(self) -> None:
        frozen = [i for i in self.report.issues if i.kind == "FROZEN_VIDEO"]
        self.assertTrue(frozen)
        self.assertIn(frozen[0].shot_id, {"shot-0", "shot-1", "shot-2"})
        self.assertTrue(self.report.repairable)


class TestMovingVideoPasses(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.video = Path(cls._tmp.name) / "moving.mp4"
        moving(cls.video, 8)
        cls.report = quality.inspect(cls.video, SIZE, shots(3, 8, real=3))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_no_slideshow_complaint(self) -> None:
        self.assertNotIn("SLIDESHOW", [i.kind for i in self.report.issues])
        self.assertLess(self.report.weak_motion_ratio, quality.MAX_WEAK_RATIO)

    def test_opening_has_life_in_it(self) -> None:
        self.assertGreater(self.report.opening_motion, quality.WEAK_MOTION)

    def test_nothing_freezes(self) -> None:
        self.assertEqual(self.report.frozen_sections, [])

    def test_coverage_is_counted_from_the_shots(self) -> None:
        self.assertEqual(self.report.real_video_coverage, 1.0)


class TestCoverageAndAssets(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.video = Path(self._tmp.name) / "v.mp4"
        moving(self.video, 6)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missed_coverage_target_is_reported_not_hidden(self) -> None:
        report = quality.inspect(self.video, SIZE, shots(4, 6, real=1), coverage_target=0.70)
        self.assertEqual(report.real_video_coverage, 0.25)
        self.assertIn("LOW_COVERAGE", [i.kind for i in report.issues])

    def test_reached_target_raises_no_complaint(self) -> None:
        report = quality.inspect(self.video, SIZE, shots(4, 6, real=3), coverage_target=0.70)
        self.assertNotIn("LOW_COVERAGE", [i.kind for i in report.issues])

    def test_ken_burns_never_counts_as_real_video(self) -> None:
        """Зумящаяся фотография с клипом в базе, но режимом image_motion."""
        rows = shots(2, 6)
        rows[0]["video_url"] = "https://example/clip.mp4"
        report = quality.inspect(self.video, SIZE, rows)
        self.assertEqual(report.real_video_coverage, 0.0)

    def test_shot_without_assets_is_an_error(self) -> None:
        rows = shots(2, 6)
        rows[1].pop("image_url")
        report = quality.inspect(self.video, SIZE, rows)
        self.assertFalse(report.ok)
        self.assertIn("MISSING_MEDIA", [i.kind for i in report.errors])

    def test_wrong_duration_is_flagged_within_the_agreed_tolerance(self) -> None:
        inside = quality.inspect(self.video, SIZE, shots(2, 6), requested_sec=7)
        self.assertNotIn("WRONG_DURATION", [i.kind for i in inside.issues])
        outside = quality.inspect(self.video, SIZE, shots(2, 6), requested_sec=30)
        self.assertIn("WRONG_DURATION", [i.kind for i in outside.issues])

    def test_broken_file_stops_everything_else(self) -> None:
        broken = Path(self._tmp.name) / "broken.mp4"
        broken.write_bytes(b"not a video")
        report = quality.inspect(broken, SIZE, shots(2, 6))
        self.assertFalse(report.ok)
        self.assertTrue(report.errors)


if __name__ == "__main__":
    unittest.main()
