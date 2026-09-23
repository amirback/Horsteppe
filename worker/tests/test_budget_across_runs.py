"""Потолок бюджета — это потолок проекта, а не одной сборки.

Дефект, из-за которого появился файл. Страж создавался с нулевой тратой при
каждом запуске. Упавшая задача автоматически повторяется, а на сайте есть
кнопка «Попробовать снова» — и каждый такой запуск начинал счёт заново.
Потолок в $1 превращался в $1 за каждую попытку.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import budget  # noqa: E402


@pytest.fixture(autouse=True)
def _clean():
    yield
    budget.unbind()


def test_previous_spend_counts_against_the_ceiling():
    guard = budget.bind(1.00, already_spent_usd=0.70)
    assert guard.spent_usd == pytest.approx(0.70)
    assert guard.remaining_usd == pytest.approx(0.30)


def test_a_retry_cannot_spend_the_ceiling_again():
    """Тот самый случай: второй запуск видит, что денег почти не осталось."""
    guard = budget.bind(1.00, already_spent_usd=0.90)
    with pytest.raises(budget.BudgetExceeded):
        guard.authorize(0.35, "видео кадра 3")


def test_fresh_project_starts_from_zero():
    guard = budget.bind(1.00)
    assert guard.spent_usd == 0.0
    guard.authorize(0.35, "видео кадра 0")  # не должно отказать


def test_no_ceiling_still_means_no_ceiling():
    guard = budget.bind(None, already_spent_usd=12.0)
    guard.authorize(5.0, "что угодно")


def test_garbage_in_the_spent_column_does_not_open_the_wallet():
    """Отрицательная сумма не должна прибавлять денег к потолку."""
    guard = budget.bind(1.00, already_spent_usd=-5.0)
    assert guard.spent_usd == 0.0
    assert guard.remaining_usd == pytest.approx(1.00)


def test_pipeline_passes_what_was_already_spent():
    source = (Path(__file__).resolve().parents[1] / "pipeline.py").read_text(encoding="utf-8")
    assert 'already_spent_usd=float(project.get("cost_usd") or 0.0)' in source
