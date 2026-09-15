"""Бриф товара и режиссура рекламы.

Главное, что здесь проверяется, — два запрета из ТЗ §9 и §10:
выдумывать свойства товара нельзя, и один шаблон на все цели тоже нельзя.

Ни сети, ни ключей, ни модели: структура и промпт считаются локально.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import product_brief  # noqa: E402
from product_brief import ProductBrief, VisualReferenceBrief, structure_for  # noqa: E402
from steps import script_step  # noqa: E402

BOTTLE = {
    "product_name": "Многоразовая бутылка",
    "product_description": "Стальная бутылка на 700 мл",
    "product_benefits": ["не течёт", "лёгкая"],
    "target_audience": "студенты",
    "ad_goal": "sales",
    "call_to_action": "Закажи на сайте",
}


class TestStructure(unittest.TestCase):
    def test_short_ad_still_shows_the_product(self) -> None:
        """Пятнадцать секунд режут всё, кроме крючка, товара и призыва."""
        for goal in product_brief.GOAL_PRIORITY:
            with self.subTest(goal=goal):
                beats = structure_for(goal, 15, benefit_count=2)
                self.assertIn("product", beats)
                self.assertEqual(beats[0], "hook")
                self.assertEqual(beats[-1], "cta")

    def test_longer_ad_gets_more_beats(self) -> None:
        self.assertLess(len(structure_for("sales", 15, 2)), len(structure_for("sales", 30, 2)))
        self.assertLessEqual(len(structure_for("sales", 90, 2)), product_brief.MAX_BEATS)

    def test_goal_changes_the_structure(self) -> None:
        """Один шаблон на все цели ТЗ §10 запрещает прямо."""
        sales = structure_for("sales", 30, 2)
        awareness = structure_for("awareness", 30, 2)
        self.assertNotEqual(sales, awareness)
        self.assertIn("problem", sales)
        self.assertIn("desire", awareness)

    def test_second_benefit_needs_a_second_benefit(self) -> None:
        self.assertNotIn("second_benefit", structure_for("launch", 45, benefit_count=1))
        self.assertIn("second_benefit", structure_for("launch", 45, benefit_count=2))

    def test_unknown_goal_falls_back_instead_of_failing(self) -> None:
        beats = structure_for("что-то своё", 30, 1)
        self.assertEqual(beats[0], "hook")
        self.assertIn("product", beats)


class TestBrief(unittest.TestCase):
    def test_project_without_a_product_is_not_an_ad(self) -> None:
        self.assertIsNone(ProductBrief.from_project({"brief": {}}))
        self.assertIsNone(ProductBrief.from_project({}))

    def test_brief_carries_only_what_the_owner_wrote(self) -> None:
        brief = ProductBrief.from_project({"brief": BOTTLE}, reference_count=3)
        self.assertEqual(brief.product_name, "Многоразовая бутылка")
        self.assertEqual(brief.benefits, ["не течёт", "лёгкая"])
        self.assertEqual(brief.reference_count, 3)

    def test_empty_benefits_are_dropped_not_kept_as_blanks(self) -> None:
        brief = ProductBrief.from_project({"brief": {**BOTTLE, "product_benefits": ["", "  ", "лёгкая"]}})
        self.assertEqual(brief.benefits, ["лёгкая"])

    def test_facts_block_lists_every_stated_fact(self) -> None:
        block = ProductBrief.from_project({"brief": BOTTLE}).facts_block()
        for fact in ("Многоразовая бутылка", "не течёт", "лёгкая", "студенты", "Закажи на сайте"):
            self.assertIn(fact, block)


class TestPromptForbidsInvention(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = ProductBrief.from_project({"brief": BOTTLE}, reference_count=3)
        self.prompt = product_brief.ad_prompt(self.brief, "cinematic", 30, 12)

    def test_invention_is_forbidden_in_plain_words(self) -> None:
        for banned in ("invent", "certifications", "prices", "discounts", "statistics"):
            self.assertIn(banned, self.prompt.lower())

    def test_prompt_names_the_uploaded_photos(self) -> None:
        self.assertIn("3 photo", self.prompt)

    def test_prompt_without_photos_says_so(self) -> None:
        bare = product_brief.ad_prompt(ProductBrief(product_name="X"), "cinematic", 30, 12)
        self.assertIn("No product photo", bare)

    def test_prompt_spells_out_the_beats(self) -> None:
        self.assertIn("HOOK", self.prompt)
        self.assertIn("CTA", self.prompt)


class TestScriptStepDispatch(unittest.TestCase):
    def test_ad_schema_demands_the_new_fields(self) -> None:
        scene = script_step.AD_SCENES_SCHEMA["properties"]["scenes"]["items"]
        self.assertIn("purpose", scene["required"])
        self.assertIn("product_required", scene["properties"]["shots"]["items"]["required"])

    def test_general_schema_is_left_alone(self) -> None:
        """Реклама не должна менять поведение обычных роликов."""
        scene = script_step.SCENES_SCHEMA["properties"]["scenes"]["items"]
        self.assertNotIn("purpose", scene["required"])
        self.assertNotIn("purpose", scene["properties"])

    def test_mock_ad_follows_the_real_structure(self) -> None:
        brief = ProductBrief.from_project({"brief": BOTTLE}, reference_count=2)
        script = script_step._mock_ad_script(brief, "cinematic", 30)
        self.assertEqual([s["purpose"] for s in script["scenes"]], brief.structure(30))
        self.assertTrue(any(shot["product_required"]
                            for scene in script["scenes"] for shot in scene["shots"]))
        self.assertEqual(script["cost_usd"], 0.0)


class TestAnimatePhoto(unittest.TestCase):
    def test_motion_prompt_protects_the_source_frame(self) -> None:
        brief = VisualReferenceBrief(creative_direction="камера медленно приближается", width=1080, height=1350)
        prompt = brief.motion_prompt()
        self.assertIn("камера медленно приближается", prompt)
        self.assertIn("unchanged", prompt)
        self.assertIn("vertical", prompt)

    def test_empty_direction_gets_a_safe_default(self) -> None:
        self.assertIn("subtle natural motion", VisualReferenceBrief(creative_direction="  ").motion_prompt())

    def test_landscape_photo_is_recognised(self) -> None:
        self.assertEqual(VisualReferenceBrief("", width=1920, height=1080).aspect_hint, "horizontal")


if __name__ == "__main__":
    unittest.main()
