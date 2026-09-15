"""Два новых режима продукта, проверенные на настоящем конвейере.

Режим A — фото товара → готовая реклама. Главное, что здесь доказывается:
в кадр попадает **снимок пользователя**, а не похожая картинка от генератора,
и именно этот снимок уходит в image-to-video. Придуманный товар — брак, а не
приближение: ради узнавания товара реклама и снимается.

Режим B — фотография → настоящее движение. Здесь нет ни сценария, ни голоса;
источник кадра — снимок, длительность набирается клипами провайдера.

Провайдеры подменены заглушками: ни сети, ни ключей, ни денег.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import media  # noqa: E402
import pipeline  # noqa: E402
from test_pipeline_e2e import FakeDb  # noqa: E402

SIZE = (180, 320)

ENV = {
    "MVP_SAFE_MODE": "0", "SCRIPT_MODE": "mock", "VIDEO_MODE": "provider",
    "IMAGE_PROVIDER": "pollinations", "ELEVENLABS_API_KEY": "test",
    "SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test",
    "VIDEO_FORMAT": "9:16", "TRANSITION_SEC": "0", "SUBTITLES": "0",
}


class ReferenceDb(FakeDb):
    """FakeDb, которая умеет отдавать снимки пользователя."""

    def __init__(self, storage: Path, project: dict[str, Any], references: list[dict[str, Any]]) -> None:
        super().__init__(storage, project)
        self.references = references

    def get_references(self, project_id: str) -> list[dict[str, Any]]:
        return self.references


def local_download(url: str, dest: Path) -> Path:
    """Заглушка сети: file:// вместо http. Продакшен ходит по https."""
    if not dest.exists():
        shutil.copyfile(Path(unquote(urlparse(url).path)), dest)
    return dest


def make_photo(path: Path, width: int = 720, height: int = 1280) -> None:
    media.run_ffmpeg(["-f", "lavfi", "-i", f"testsrc2=size={width}x{height}",
                      "-frames:v", "1", str(path)])


class ModeSetup:
    """Общая обвязка: подменённые провайдеры и восстановление окружения."""

    @classmethod
    def prepare(cls) -> None:
        from steps import image_step, tts_step, video_step

        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        cls.storage = root / "storage"
        cls.storage.mkdir()
        cls.env_backup = {k: os.environ.get(k) for k in ENV}
        os.environ.update(ENV)

        cls.animated: list[str] = []
        cls.generated_prompts: list[str] = []

        def fake_clip(cfg, image_url, motion_prompt, out_path):
            cls.animated.append(image_url)
            media.run_ffmpeg(["-f", "lavfi",
                              "-i", f"testsrc2=size={SIZE[0]}x{SIZE[1]}:rate=30:duration=5",
                              "-pix_fmt", "yuv420p", str(out_path)])
            return 0.35

        def fake_image(cfg, prompt, out_path, index=0):
            cls.generated_prompts.append(prompt)
            media.run_ffmpeg(["-f", "lavfi", "-i", f"color=c=gray:size={SIZE[0]}x{SIZE[1]}",
                              "-frames:v", "1", str(out_path)])
            return 0.0

        def fake_tts(cfg, text, out_path):
            media.run_ffmpeg(["-f", "lavfi", "-i", "anoisesrc=d=3:c=pink:a=0.3",
                              "-ar", "44100", str(out_path)])
            return 0.0

        cls._originals = [
            (video_step, "generate_clip", video_step.generate_clip),
            (image_step, "generate_image", image_step.generate_image),
            (tts_step, "synthesize", tts_step.synthesize),
            (pipeline, "_download", pipeline._download),
        ]
        video_step.generate_clip = fake_clip
        image_step.generate_image = fake_image
        tts_step.synthesize = fake_tts
        pipeline._download = local_download
        cls._format = media.FORMATS["9:16"]
        media.FORMATS["9:16"] = SIZE

    @classmethod
    def restore(cls) -> None:
        for module, name, original in cls._originals:
            setattr(module, name, original)
        media.FORMATS["9:16"] = cls._format
        for key, value in cls.env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls._tmp.cleanup()

    @classmethod
    def reference_row(cls, name: str = "ref_0.png", primary: bool = True) -> dict[str, Any]:
        photo = cls.storage / name
        make_photo(photo)
        return {
            "id": str(uuid.uuid4()), "order_index": 0, "is_primary": primary,
            "storage_path": name, "public_url": photo.as_uri(),
            "mime_type": "image/png", "width": 720, "height": 1280,
        }


class TestProductAd(ModeSetup, unittest.TestCase):
    """Режим A: фотографии товара → готовый рекламный ролик."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.prepare()
        from config import Config

        reference = cls.reference_row()
        cls.reference_url = reference["public_url"]
        project_id = str(uuid.uuid4())
        cls.db = ReferenceDb(cls.storage, {
            "id": project_id, "topic": "реклама бутылки", "style": "product",
            "duration_sec": 20, "aspect_ratio": "9:16", "status": "queued",
            "project_type": "product_ad",
            "brief": {
                "product_name": "Многоразовая бутылка",
                "product_description": "Стальная бутылка на 700 мл",
                "product_benefits": ["не течёт", "лёгкая"],
                "target_audience": "студенты",
                "ad_goal": "sales",
                "call_to_action": "Закажи на сайте",
            },
        }, [reference])
        pipeline.run_project(Config(), cls.db, project_id)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.restore()

    def test_the_ad_was_built(self) -> None:
        self.assertEqual(self.db.project["status"], "done", self.db.project.get("error_message"))
        self.assertTrue(self.db.renders)

    def test_script_follows_the_ad_structure_not_a_story(self) -> None:
        purposes = [s["purpose"] for s in self.db.shots]
        self.assertIn("hook", purposes)
        self.assertTrue(self.db.scenes, "сцены рекламы должны существовать")

    def test_product_shots_use_the_real_photo(self) -> None:
        """Ключевая проверка вехи: товар в кадре — снимок человека."""
        product_shots = [s for s in self.db.shots if s.get("first_frame_reference")]
        self.assertTrue(product_shots, "ни один кадр не получил снимок товара")
        for shot in product_shots:
            self.assertEqual(shot["image_url"], self.reference_url)

    def test_the_photo_was_never_regenerated(self) -> None:
        """Генератор картинок не должен рисовать «похожий товар»."""
        self.assertEqual(
            len([s for s in self.db.shots if s.get("first_frame_reference")]) +
            len(self.generated_prompts),
            len(self.db.shots),
        )

    def test_provider_animated_the_product_photo(self) -> None:
        self.assertIn(self.reference_url, self.animated)

    def test_product_shot_went_first_in_the_queue_for_real_video(self) -> None:
        product_shots = [s for s in self.db.shots if s.get("first_frame_reference")]
        self.assertTrue(any(s.get("generation_mode") == "real_video" for s in product_shots))

    def test_final_file_is_valid(self) -> None:
        final = Path(self.db.renders[-1][0].replace("file://", ""))
        check = media.validate_final(final, SIZE)
        self.assertTrue(check["ok"], check["errors"])


class TestAnimatePhoto(ModeSetup, unittest.TestCase):
    """Режим B: одна фотография → настоящее движущееся видео."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.prepare()
        from config import Config

        reference = cls.reference_row("animate.png")
        cls.reference_url = reference["public_url"]
        project_id = str(uuid.uuid4())
        cls.db = ReferenceDb(cls.storage, {
            "id": project_id,
            "topic": "камера медленно приближается, человек поворачивается к окну",
            "style": "cinematic", "duration_sec": 10, "aspect_ratio": "9:16",
            "status": "queued", "project_type": "image_to_video",
        }, [reference])
        pipeline.run_project(Config(), cls.db, project_id)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.restore()

    def test_video_was_built_without_a_script(self) -> None:
        self.assertEqual(self.db.project["status"], "done", self.db.project.get("error_message"))
        self.assertEqual(len(self.db.scenes), 1)
        self.assertEqual(self.db.scenes[0]["narration"], "")

    def test_nothing_was_generated_from_text(self) -> None:
        self.assertEqual(self.generated_prompts, [], "картинки генерировать незачем — снимок уже есть")

    def test_every_clip_came_from_the_uploaded_photo(self) -> None:
        self.assertTrue(self.animated)
        self.assertEqual(set(self.animated), {self.reference_url})

    def test_requested_length_is_covered_by_real_clips(self) -> None:
        self.assertEqual(pipeline.real_video_coverage(self.db.shots), 1.0)

    def test_duration_matches_the_request(self) -> None:
        final = Path(self.db.renders[-1][0].replace("file://", ""))
        self.assertAlmostEqual(media.media_duration_sec(final), 10.0, delta=1.0)

    def test_file_has_sound_even_without_narration(self) -> None:
        """Немой файл часть плееров считает битым — тишина честнее отсутствия дорожки."""
        final = Path(self.db.renders[-1][0].replace("file://", ""))
        self.assertTrue(media.validate_final(final, SIZE)["has_audio"])


if __name__ == "__main__":
    unittest.main()
