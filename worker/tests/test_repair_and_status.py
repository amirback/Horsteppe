"""Починка плохих кадров и честный итог сборки.

Два обещания ТЗ проверяются здесь на настоящем конвейере:

§25 — чинится **только** затронутый кадр, круги ограничены, исправные кадры
не трогаются;
§32 — ролик ниже цели по настоящему движению не выдаётся за чистый успех.

Провайдер подменён заглушкой, которая возвращает **застывший** клип: именно
так выглядит реальный отказ модели, который раньше уезжал к пользователю
незамеченным.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import media  # noqa: E402
import pipeline  # noqa: E402
import quality  # noqa: E402
from test_pipeline_e2e import FakeDb  # noqa: E402

SIZE = (180, 320)


class FakeCfg:
    def __init__(self, safe: bool = False, video_mode: str = "provider") -> None:
        self.mvp_safe_mode = safe
        self.video_mode = video_mode


class TestMotionChoice(unittest.TestCase):
    """Починка не должна создавать дефект вместо исправленного."""

    def test_new_motion_differs_from_both_neighbours(self) -> None:
        shots = [
            {"camera_motion": "pan_right"},
            {"camera_motion": "push_in"},
            {"camera_motion": "pull_out"},
        ]
        fresh = pipeline._fresh_motion(shots, shots[1])
        self.assertNotIn(fresh, {"pan_right", "pull_out", "push_in"})

    def test_first_shot_has_only_one_neighbour(self) -> None:
        shots = [{"camera_motion": "push_in"}, {"camera_motion": "pan_right"}]
        self.assertNotIn(pipeline._fresh_motion(shots, shots[0]), {"push_in", "pan_right"})

    def test_single_shot_still_gets_a_change(self) -> None:
        shots = [{"camera_motion": "push_in"}]
        self.assertNotEqual(pipeline._fresh_motion(shots, shots[0]), "push_in")


class TestDegradedReason(unittest.TestCase):
    def test_target_reached_means_no_excuse(self) -> None:
        self.assertIsNone(pipeline._degraded_reason(FakeCfg(), [], 0.8, 0.7))

    def test_safe_mode_is_named_as_the_reason(self) -> None:
        reason = pipeline._degraded_reason(FakeCfg(safe=True), [], 0.0, 0.7)
        self.assertIn("отключено", reason)

    def test_budget_is_named_as_the_reason(self) -> None:
        shots = [{"failure_reason": "бюджет проекта не позволяет: остаток $0.10 ниже цены самой дешёвой подходящей модели"}]
        self.assertIn("Бюджета", pipeline._degraded_reason(FakeCfg(), shots, 0.2, 0.7))

    def test_provider_failure_is_named_as_the_reason(self) -> None:
        shots = [{"failure_reason": "fal.ai video generation failed: 500"}]
        self.assertIn("ровайдер", pipeline._degraded_reason(FakeCfg(), shots, 0.2, 0.7))


class TestFrozenClipIsCaughtAndReplaced(unittest.TestCase):
    """Провайдер вернул застывший клип — конвейер обязан это заметить."""

    @classmethod
    def setUpClass(cls) -> None:
        from steps import image_step, tts_step, video_step

        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        cls.storage = root / "storage"
        cls.storage.mkdir()

        env = {
            "MVP_SAFE_MODE": "0", "SCRIPT_MODE": "mock", "VIDEO_MODE": "provider",
            "IMAGE_PROVIDER": "pollinations", "ELEVENLABS_API_KEY": "test", "FAL_KEY": "test",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test", "VIDEO_FORMAT": "9:16",
            "TRANSITION_SEC": "0", "SUBTITLES": "0",
        }
        cls.env_backup = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        from config import Config

        def frozen_clip(cfg, image_url, motion_prompt, out_path, model=None, cost_usd=None):
            """Пять секунд одного и того же кадра — брак, который платят."""
            media.run_ffmpeg([
                "-f", "lavfi", "-i", f"color=c=slategray:size={SIZE[0]}x{SIZE[1]}:rate=30",
                "-t", "5", "-pix_fmt", "yuv420p", str(out_path),
            ])
            return video_step.ClipResult("higgsfield", "kling-video/v2.5-turbo/pro/image-to-video", 0.35)

        def textured_image(cfg, prompt, out_path, index=0):
            """Картинка с фактурой: по ней движение камеры видно."""
            media.run_ffmpeg([
                "-f", "lavfi", "-i", f"testsrc2=size={SIZE[0] * 2}x{SIZE[1] * 2}",
                "-frames:v", "1", str(out_path),
            ])
            return 0.0

        def fake_tts(cfg, text, out_path):
            media.run_ffmpeg(["-f", "lavfi", "-i", "anoisesrc=d=4:c=pink:a=0.3",
                              "-ar", "44100", str(out_path)])
            return 0.0

        def local_download(url: str, dest: Path) -> Path:
            if not dest.exists():
                shutil.copyfile(Path(unquote(urlparse(url).path)), dest)
            return dest

        cls._originals = [
            (video_step, "generate_clip", video_step.generate_clip),
            (image_step, "generate_image", image_step.generate_image),
            (tts_step, "synthesize", tts_step.synthesize),
            (pipeline, "_download", pipeline._download),
        ]
        video_step.generate_clip = frozen_clip
        image_step.generate_image = textured_image
        tts_step.synthesize = fake_tts
        pipeline._download = local_download
        cls._format = media.FORMATS["9:16"]
        media.FORMATS["9:16"] = SIZE

        project_id = str(uuid.uuid4())
        cls.db = FakeDb(cls.storage, {
            "id": project_id, "topic": "founder builds a startup at night",
            "style": "cinematic", "duration_sec": 15, "aspect_ratio": "9:16",
            "status": "queued",
        })
        pipeline.run_project(Config(), cls.db, project_id)

    @classmethod
    def tearDownClass(cls) -> None:
        for module, name, original in cls._originals:
            setattr(module, name, original)
        media.FORMATS["9:16"] = cls._format
        for key, value in cls.env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls._tmp.cleanup()

    def test_project_finished(self) -> None:
        self.assertIn(self.db.project["status"], {"done", "done_degraded"},
                      self.db.project.get("error_message"))

    def test_frozen_clips_were_thrown_away(self) -> None:
        """Застывший клип хуже движения по картинке, и его место — в корзине."""
        repaired = [s for s in self.db.shots if int(s.get("retry_count") or 0) > 0]
        self.assertTrue(repaired, "инспектор обязан был заметить застывшие клипы")
        for shot in repaired:
            self.assertIsNone(shot.get("video_url"))
            self.assertEqual(shot.get("generation_mode"), "image_motion")

    def test_repair_is_capped(self) -> None:
        for shot in self.db.shots:
            self.assertLessEqual(int(shot.get("retry_count") or 0), pipeline.MAX_REPAIR_ROUNDS)

    def test_the_reason_is_recorded_not_hidden(self) -> None:
        if self.db.project["status"] == "done_degraded":
            self.assertTrue(self.db.project.get("degraded_reason"))

    def test_coverage_is_stored_for_the_user_to_see(self) -> None:
        self.assertIn("real_video_coverage", self.db.project)
        self.assertEqual(
            self.db.project["real_video_coverage"],
            pipeline.real_video_coverage(self.db.shots),
        )

    def test_quality_report_is_stored(self) -> None:
        report = self.db.project.get("quality")
        self.assertIsInstance(report, dict)
        self.assertIn("weak_motion_ratio", report)

    def test_final_file_is_still_valid(self) -> None:
        final = Path(self.db.renders[-1][0].replace("file://", ""))
        self.assertTrue(media.validate_final(final, SIZE)["ok"])


if __name__ == "__main__":
    unittest.main()
