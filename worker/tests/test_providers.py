"""Реестр возможностей и маршрутизатор моделей.

Проверяется то, ради чего маршрутизатор и появился: выбор зависит от кадра.
Крючку и кадру товара достаётся лучшее, фону — дешёвое, а модель, которой
нечем оживить фотографию, не попадает в кандидаты ни при какой цене.

Ни сети, ни ключей, ни денег: решения принимаются по таблице.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import providers  # noqa: E402
from providers import Capability  # noqa: E402


# Все ключи, которые упоминает реестр. Список берётся из самого реестра, а
# не переписывается руками: тест, перечисляющий ключи по памяти, однажды уже
# соврал — он гасил FAL_KEY, читал настоящий HF_KEY из окружения машины и
# уверял, что «без ключа моделей нет».
KEY_NAMES = sorted({c.key_env for c in providers.REGISTRY if c.key_env})


class WithKey(unittest.TestCase):
    """Ключи провайдеров считаются настроенными — и только они."""

    def setUp(self) -> None:
        self._backup = {k: os.environ.get(k) for k in KEY_NAMES}
        for key in KEY_NAMES:
            os.environ[key] = "test"

    def tearDown(self) -> None:
        for key, value in self._backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def forget_all_keys(self) -> None:
        """Машина без единого настроенного провайдера."""
        for key in KEY_NAMES:
            os.environ[key] = ""


class TestHardFilter(WithKey):
    def test_model_without_image_to_video_never_gets_a_product_shot(self) -> None:
        pool = providers.candidates("video", needs_image_to_video=True)
        self.assertTrue(pool)
        for cap in pool:
            self.assertTrue(cap.supports_image_to_video)

    def test_price_above_the_remaining_budget_is_excluded(self) -> None:
        pool = providers.candidates("video", needs_image_to_video=True, affordable_usd=0.40)
        self.assertTrue(pool)
        for cap in pool:
            self.assertLessEqual(cap.cost_usd, 0.40)

    def test_unsupported_aspect_is_excluded(self) -> None:
        self.assertEqual(providers.candidates("video", aspect="21:9"), [])

    def test_without_a_key_nothing_is_available(self) -> None:
        self.forget_all_keys()
        self.assertEqual(providers.candidates("video", needs_image_to_video=True), [])

    def test_free_image_provider_needs_no_key_at_all(self) -> None:
        os.environ["FAL_KEY"] = ""
        os.environ["TOGETHER_API_KEY"] = ""
        pool = providers.candidates("image")
        self.assertTrue(pool, "бесплатный путь обязан оставаться доступным без ключей")
        self.assertTrue(all(cap.cost_usd == 0 for cap in pool))


class TestChoice(WithKey):
    def test_important_shot_gets_the_stronger_model(self) -> None:
        best = providers.choose("video", importance=1.0, needs_image_to_video=True)
        cheap = providers.choose("video", importance=0.2, needs_image_to_video=True)
        self.assertGreater(best.quality_prior, cheap.quality_prior)
        self.assertGreater(best.cost_usd, cheap.cost_usd)

    def test_tight_budget_wins_over_importance(self) -> None:
        """Важность не печатает деньги."""
        choice = providers.choose(
            "video", importance=1.0, needs_image_to_video=True, affordable_usd=0.40
        )
        self.assertLessEqual(choice.cost_usd, 0.40)

    def test_no_money_at_all_is_not_an_error(self) -> None:
        self.assertIsNone(
            providers.choose("video", importance=1.0, needs_image_to_video=True, affordable_usd=0.0)
        )

    def test_cheap_but_unreliable_loses_to_dearer_but_solid(self) -> None:
        """Цена за пригодный кадр, а не цена вызова."""
        flaky = Capability(provider="a", model="flaky", kind="video",
                           cost_usd=0.10, reliability_prior=0.2)
        solid = Capability(provider="b", model="solid", kind="video",
                           cost_usd=0.25, reliability_prior=0.9)
        self.assertGreater(flaky.cost_per_usable, solid.cost_per_usable)


class TestWhyNot(WithKey):
    def test_money_and_capability_are_told_apart(self) -> None:
        """Одно человек может исправить сам, другое — нет."""
        money = providers.why_not("video", affordable_usd=0.01, needs_image_to_video=True)
        self.assertIn("бюджет", money)

    def test_missing_key_is_named(self) -> None:
        self.forget_all_keys()
        self.assertIn("ключ", providers.why_not("video", needs_image_to_video=True))


class TestRegistrySanity(WithKey):
    def test_every_video_model_can_animate_an_image(self) -> None:
        """Текстовое видео продукту не нужно: у нас всегда есть кадр."""
        for cap in providers.REGISTRY:
            if cap.kind == "video":
                self.assertTrue(cap.supports_image_to_video, cap.model)

    def test_priors_are_within_bounds(self) -> None:
        for cap in providers.REGISTRY:
            self.assertGreaterEqual(cap.cost_usd, 0.0, cap.model)
            self.assertTrue(0 <= cap.quality_prior <= 1, cap.model)
            self.assertTrue(0 < cap.reliability_prior <= 1, cap.model)

    def test_registry_stays_small(self) -> None:
        """ТЗ §15 прямо запрещает заводить двадцать провайдеров впрок."""
        self.assertLessEqual(len(providers.REGISTRY), 8)


if __name__ == "__main__":
    unittest.main()
