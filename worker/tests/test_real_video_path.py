"""Настоящее видео обязано доходить до финального таймлайна.

Провайдер подменяется локально сгенерированным клипом с опознаваемым
содержимым: денег не тратим, а путь «провайдер → кадр → монтаж → финальный
MP4» проверяется целиком. Именно здесь ломалось главное обещание продукта —
оплаченные клипы молча заменялись зумом по фотографии.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import media  # noqa: E402
import pipeline  # noqa: E402
from test_pipeline_e2e import FakeDb  # noqa: E402

SIZE = (180, 320)
GRID = 32


def _make_clip(path: Path, seconds: float = 5.0) -> None:
    """Клип с движущейся заливкой: его ни с чем не спутать."""
    media.run_ffmpeg([
        "-f", "lavfi", "-i", f"testsrc2=size={SIZE[0]}x{SIZE[1]}:rate=30:duration={seconds}",
        "-pix_fmt", "yuv420p", str(path),
    ])


def _frames(video: Path, count: int) -> list[bytes]:
    dur = media.media_duration_sec(video)
    raw = subprocess.run(
        [media.ffmpeg_path(), "-v", "error", "-i", str(video),
         "-vf", f"fps={count / dur},scale={GRID}:{GRID},format=gray", "-f", "rawvideo", "-"],
        capture_output=True,
    ).stdout
    n = GRID * GRID
    return [raw[i * n:(i + 1) * n] for i in range(len(raw) // n)]


class RealVideoReachesTimelineTest(unittest.TestCase):
    """Один прогон, много утверждений: пересобирать ролик дорого."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        cls.storage = root / "storage"
        cls.storage.mkdir()
        cls.clip = root / "provider_clip.mp4"
        _make_clip(cls.clip)

        import os
        os.environ.update({
            "MVP_SAFE_MODE": "0", "SCRIPT_MODE": "mock", "VIDEO_MODE": "provider",
            "IMAGE_PROVIDER": "pollinations", "ELEVENLABS_API_KEY": "test",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test", "VIDEO_FORMAT": "9:16",
            "TRANSITION_SEC": "0.4", "SUBTITLES": "0",
        })
        from config import Config

        cls.project_id = str(uuid.uuid4())
        cls.db = FakeDb(cls.storage, {
            "id": cls.project_id, "topic": "founder builds a startup at night",
            "style": "cinematic", "duration_sec": 20, "aspect_ratio": "9:16",
            "status": "queued",
        })

        cls.calls: list[str] = []

        def fake_provider(cfg, image_url, motion_prompt, out_path):
            """Стоит как настоящий вызов, но ничего не платит."""
            cls.calls.append(image_url)
            out_path.write_bytes(cls.clip.read_bytes())
            return 0.35

        def fake_image(cfg, prompt, out_path, index=0):
            media.run_ffmpeg([
                "-f", "lavfi", "-i", f"color=c=gray:size={SIZE[0]}x{SIZE[1]}",
                "-frames:v", "1", str(out_path),
            ])
            return 0.0

        def fake_tts(cfg, text, out_path):
            media.run_ffmpeg([
                "-f", "lavfi", "-i", "anoisesrc=d=4:c=pink:a=0.3",
                "-ar", "44100", str(out_path),
            ])
            return 0.0

        from steps import image_step, tts_step, video_step

        # Оригиналы обязательно вернуть: подмена на уровне модуля видна всем
        # остальным тестам, и без восстановления соседний тест безопасного
        # режима начинал звать эту заглушку вместо настоящего шага.
        cls._originals = [
            (video_step, "generate_clip", video_step.generate_clip),
            (image_step, "generate_image", image_step.generate_image),
            (tts_step, "synthesize", tts_step.synthesize),
        ]
        video_step.generate_clip = fake_provider
        image_step.generate_image = fake_image
        tts_step.synthesize = fake_tts
        # Кадр теста крошечный: рендерить 1080x1920 ради проверки пути незачем.
        media.FORMATS["9:16"] = SIZE

        pipeline.run_project(Config(), cls.db, cls.project_id)
        cls.final = Path(cls.db.renders[-1][0].replace("file://", ""))

    @classmethod
    def tearDownClass(cls) -> None:
        for module, name, original in cls._originals:
            setattr(module, name, original)
        media.FORMATS["9:16"] = (1080, 1920)
        cls._tmp.cleanup()

    def test_provider_was_asked_exactly_for_the_planned_shots(self) -> None:
        """Провайдера зовут не на все кадры, а на те, что выбрал планировщик.

        Раньше настоящее видео просили для каждого кадра — это стоило бы
        вдвое дороже цели покрытия и противоречило бы Smart Budget.
        """
        from steps import shot_plan

        planned = [s for s in self.db.shots if shot_plan.preferred_mode(s) == "real_video"]
        self.assertEqual(len(self.calls), len(planned))
        self.assertLess(len(planned), len(self.db.shots), "фоновым кадрам видео не нужно")

    def test_planned_shots_became_real_video(self) -> None:
        from steps import shot_plan

        for shot in self.db.shots:
            if shot_plan.preferred_mode(shot) == "real_video":
                self.assertEqual(shot["generation_mode"], "real_video")
                self.assertTrue(shot.get("video_url"), f"кадр {shot['order_index']} без клипа")
            else:
                self.assertEqual(shot["generation_mode"], "image_motion")

    def test_coverage_reaches_the_smart_target(self) -> None:
        """Цель брифа для SMART — около 70% таймлайна настоящим видео."""
        self.assertGreaterEqual(pipeline.real_video_coverage(self.db.shots), 0.65)

    def test_final_file_is_valid(self) -> None:
        check = media.validate_final(self.final, SIZE)
        self.assertTrue(check["ok"], check["errors"])

    def test_provider_footage_actually_reached_the_final_file(self) -> None:
        """Главная проверка: в финальном ролике именно клип, а не зум по фото.

        Кадры провайдера двигаются сильно, серая заглушка — почти нет.
        Если монтаж подменил клип картинкой, движение обвалится.
        """
        frames = _frames(self.final, 12)
        diffs = [
            sum(abs(a - b) for a, b in zip(frames[i], frames[i + 1])) / len(frames[i])
            for i in range(len(frames) - 1)
        ]
        moving = sum(1 for d in diffs if d > 3.0)
        self.assertGreater(moving, len(diffs) * 0.7, f"движение пропало: {diffs}")

    def test_clip_is_cut_to_the_timeline_not_to_the_provider_length(self) -> None:
        """Провайдер отдаёт 5 секунд, в монтаж уходит столько, сколько нужно."""
        self.assertAlmostEqual(media.media_duration_sec(self.clip), 5.0, places=1)
        for shot in self.db.shots:
            self.assertLess(float(shot["timeline_duration"]), 5.0)

    def test_paid_video_was_accounted_for(self) -> None:
        video_costs = [a for step, _, a in self.db.costs if step == "video"]
        self.assertEqual(len(video_costs), len(self.calls))
        self.assertAlmostEqual(sum(video_costs), 0.35 * len(self.calls), places=4)


class ExistingClipIsNeverReplacedTest(unittest.TestCase):
    """Оплаченный клип нельзя молча заменить зумом по картинке.

    Прежнее условие в монтаже требовало ещё и текущего режима `provider`.
    Стоило переключить режим — и готовое настоящее видео игнорировалось.
    """

    def test_shot_with_a_clip_is_rendered_from_the_clip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            clip = work / "clip.mp4"
            _make_clip(clip, seconds=3.0)
            still = work / "still.png"
            media.run_ffmpeg([
                "-f", "lavfi", "-i", f"color=c=gray:size={SIZE[0]}x{SIZE[1]}",
                "-frames:v", "1", str(still),
            ])
            out = work / "segment.mp4"
            media.make_clip_segment(clip, out, 2.0, SIZE)
            frames = _frames(out, 8)
            diffs = [
                sum(abs(a - b) for a, b in zip(frames[i], frames[i + 1])) / len(frames[i])
                for i in range(len(frames) - 1)
            ]
            self.assertGreater(max(diffs), 3.0, "клип провайдера потерял движение")


if __name__ == "__main__":
    unittest.main()
