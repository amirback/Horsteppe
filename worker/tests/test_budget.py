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
