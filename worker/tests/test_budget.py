"""Потолок расходов: страж обязан отказывать, а не вести статистику.

Разница принципиальная. Метаданные о бюджете, которые никто не проверяет
перед вызовом, — это отчёт о перерасходе, а не защита от него.

Ни сети, ни ключей, ни денег.

Запуск (из каталога worker):
    PYTHONUTF8=1 python -m pytest tests/test_budget.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import budget  # noqa: E402
import safe_mode  # noqa: E402
from budget import BudgetExceeded, BudgetGuard  # noqa: E402

CLIP = 0.35  # цена пятисекундного клипа Kling


class FakeCfg:
    """Ровно те поля, которые читает safe_mode."""

    def __init__(self, safe: bool = False, video_mode: str = "provider") -> None:
        self.mvp_safe_mode = safe
        self.video_mode = video_mode


class TestCeiling(unittest.TestCase):
    def test_no_ceiling_allows_everything(self) -> None:
        guard = BudgetGuard(max_budget_usd=None)
        guard.authorize(1000.0, "клип")  # не бросает
        self.assertEqual(guard.remaining_usd, float("inf"))

    def test_zero_is_not_the_same_as_no_ceiling(self) -> None:
        guard = BudgetGuard(max_budget_usd=0.0)
        with self.assertRaises(BudgetExceeded):
            guard.authorize(0.01, "клип")

    def test_denies_before_the_call_not_after(self) -> None:
        guard = BudgetGuard(max_budget_usd=1.0)
        guard.record(0.9, "клипы")
        with self.assertRaises(BudgetExceeded):
            guard.authorize(CLIP, "ещё клип")
        self.assertEqual(guard.spent_usd, 0.9, "отказ не должен ничего списывать")

    def test_reserve_is_kept_for_repairs(self) -> None:
        """Обычная генерация не должна съедать деньги, отложенные на починку."""
        guard = BudgetGuard(max_budget_usd=1.0, reserve_ratio=0.15)
        self.assertEqual(guard.repair_reserve_usd, 0.15)
        self.assertEqual(guard.spendable_usd, 0.85)
        guard.record(0.85, "первая сборка")
        with self.assertRaises(BudgetExceeded):
            guard.authorize(0.10, "обычный кадр")
        guard.authorize(0.10, "починка кадра", repair=True)  # резерв доступен

    def test_spending_is_counted_by_fact_not_by_estimate(self) -> None:
        guard = BudgetGuard(max_budget_usd=3.0)
        guard.authorize(CLIP, "клип")
        guard.record(0.41, "клип вышел дороже оценки")
        self.assertAlmostEqual(guard.spent_usd, 0.41)
        self.assertAlmostEqual(guard.remaining_usd, 2.59)

    def test_denial_reason_names_the_numbers(self) -> None:
        guard = BudgetGuard(max_budget_usd=0.20)
        with self.assertRaises(BudgetExceeded) as raised:
            guard.authorize(CLIP, "клип кадра 3")
        message = str(raised.exception)
        self.assertIn("клип кадра 3", message)
        self.assertIn("0.35", message)
        self.assertEqual(len(guard.denials), 1)

    def test_summary_reports_what_the_user_paid(self) -> None:
        guard = BudgetGuard(max_budget_usd=2.0)
        guard.record(0.7)
        self.assertEqual(
            guard.summary(),
            {"max_budget_usd": 2.0, "spent_usd": 0.7, "remaining_usd": 1.3,
             "repair_reserve_usd": 0.3, "denials": 0},
        )


class TestCheckpoint(unittest.TestCase):
    """Потолок обязан жить в общем чекпойнте, иначе его обойдут."""

    def test_checkpoint_denies_when_budget_is_out(self) -> None:
        with budget.for_project(0.10) as guard:
            with self.assertRaises(BudgetExceeded):
                safe_mode.require_paid(FakeCfg(), "генерация видео", CLIP)
            self.assertEqual(len(guard.denials), 1)

    def test_checkpoint_allows_within_budget(self) -> None:
        with budget.for_project(3.0):
            safe_mode.require_paid(FakeCfg(), "генерация видео", CLIP)

    def test_safe_mode_wins_over_budget(self) -> None:
        """Даже с деньгами на счету безопасный режим не пропускает вызов."""
        with budget.for_project(100.0):
            with self.assertRaises(safe_mode.PaidCallBlocked):
                safe_mode.require_paid(FakeCfg(safe=True), "генерация видео", CLIP)

    def test_without_a_project_nothing_changes(self) -> None:
        """Старые вызовы без оценки и без стража работают как прежде."""
        self.assertIsNone(budget.current())
        safe_mode.require_paid(FakeCfg(), "озвучка")

    def test_guard_is_released_after_the_project(self) -> None:
        with budget.for_project(1.0):
            self.assertIsNotNone(budget.current())
        self.assertIsNone(budget.current())


if __name__ == "__main__":
    unittest.main()


class TestPipelineRespectsTheCeiling(unittest.TestCase):
    """Потолок на настоящем конвейере: отказ обязан быть мягким.

    Кончились деньги — ролик всё равно собирается, кадр остаётся движением по
    картинке, причина записана, покрытие честно равно нулю. Падение проекта
    из-за исчерпанного бюджета было бы худшим из возможных поведений: человек
    остался бы и без денег, и без результата.
    """

    @classmethod
    def setUpClass(cls) -> None:
        import os
        import tempfile
        import uuid

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import media
        import pipeline
        from steps import image_step, tts_step, video_step
        from test_pipeline_e2e import FakeDb

        cls.size = (180, 320)
        cls._tmp = tempfile.TemporaryDirectory()
        storage = Path(cls._tmp.name) / "storage"
        storage.mkdir()

        # Переменные обязательно вернуть: этот файл идёт по алфавиту раньше
        # остальных, и «на время теста» открытый платный режим доставался
        # соседям, которые проверяют поведение без ключей.
        env = {
            "MVP_SAFE_MODE": "0", "SCRIPT_MODE": "mock", "VIDEO_MODE": "provider",
            "IMAGE_PROVIDER": "pollinations", "ELEVENLABS_API_KEY": "test", "FAL_KEY": "test",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test", "VIDEO_FORMAT": "9:16",
            "TRANSITION_SEC": "0", "SUBTITLES": "0",
        }
        cls._env_backup = {key: os.environ.get(key) for key in env}
        os.environ.update(env)
        from config import COSTS, Config

        cls.attempts: list[str] = []

        def fake_provider(cfg, image_url, motion_prompt, out_path, model=None, cost_usd=None, provider=None):
            """Заглушка, которая честно спрашивает разрешения, как настоящий шаг."""
            cls.attempts.append(image_url)
            safe_mode.require_paid(cfg, "генерация видео", COSTS["fal_video_per_clip"])
            media.run_ffmpeg([
                "-f", "lavfi",
                "-i", f"testsrc2=size={cls.size[0]}x{cls.size[1]}:rate=30:duration=5",
                "-pix_fmt", "yuv420p", str(out_path),
            ])
            return video_step.ClipResult(
                "higgsfield", "kling-video/v2.5-turbo/pro/image-to-video",
                COSTS["fal_video_per_clip"],
            )

        def fake_image(cfg, prompt, out_path, index=0):
            media.run_ffmpeg(["-f", "lavfi", "-i", f"color=c=gray:size={cls.size[0]}x{cls.size[1]}",
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
        ]
        video_step.generate_clip = fake_provider
        image_step.generate_image = fake_image
        tts_step.synthesize = fake_tts
        cls._format = media.FORMATS["9:16"]
        media.FORMATS["9:16"] = cls.size

        # Потолка хватает ровно на один клип: 0.50 минус резерв 15% = 0.425.
        project_id = str(uuid.uuid4())
        cls.db = FakeDb(storage, {
            "id": project_id, "topic": "founder builds a startup at night",
            "style": "cinematic", "duration_sec": 15, "aspect_ratio": "9:16",
            "status": "queued", "max_budget_usd": 0.50,
        })
        pipeline.run_project(Config(), cls.db, project_id)
        cls.shots = cls.db.shots
        cls.pipeline = pipeline

    @classmethod
    def tearDownClass(cls) -> None:
        import os

        import media
        for module, name, original in cls._originals:
            setattr(module, name, original)
        media.FORMATS["9:16"] = cls._format
        for key, value in cls._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls._tmp.cleanup()

    def test_project_finished_despite_running_out_of_money(self) -> None:
        """Ролик собран — но результат назван своим именем.

        Раньше здесь ожидался статус «Готово». Это была слабая проверка:
        ролик, где на настоящее видео не хватило денег, выглядел таким же
        успехом, как полностью оплаченный (ТЗ §32).
        """
        self.assertEqual(self.db.project["status"], "done_degraded")
        self.assertIn("Бюджета", self.db.project["degraded_reason"])
        self.assertTrue(self.db.renders, "ролик должен быть собран")

    def test_only_what_the_ceiling_allowed_was_paid_for(self) -> None:
        paid = [s for s in self.shots if s.get("generation_mode") == "real_video"]
        self.assertEqual(len(paid), 1, "потолка $0.50 хватает ровно на один клип")

    def test_the_rest_were_denied_before_the_call(self) -> None:
        denied = [s for s in self.shots if s.get("failure_reason")]
        self.assertTrue(denied, "отказ должен быть записан в кадре")
        self.assertIn("бюджет", " ".join(s["failure_reason"] for s in denied).lower())

    def test_provider_is_not_even_called_when_money_is_out(self) -> None:
        """Лучший отказ — до вызова: ни задержки в несколько минут, ни денег.

        Раньше здесь ожидалось обратное: провайдера звали и отказывали на
        чекпойнте. Маршрутизатор отсекает недоступную по деньгам модель
        раньше, и это строго лучше — но причина всё равно обязана попасть
        в кадр, иначе отказ становится молчаливым.
        """
        paid = [s for s in self.db.shots if s.get("generation_mode") == "real_video"]
        self.assertEqual(len(self.attempts), len(paid))

    def test_coverage_counts_only_what_was_actually_generated(self) -> None:
        coverage = self.pipeline.real_video_coverage(self.shots)
        self.assertGreater(coverage, 0.0)
        self.assertLess(coverage, 0.7, "покрытие не приписывается отказанным кадрам")
