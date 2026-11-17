"""Уровень пакета — потолок моделей для кадра.

Покупатель пакета «Эконом» не получает Kling 4.0 за свой кредит, «Медиум» —
не выше Kling 3.0 Pro / Seedance 2.0, «Премиум» — всё по сложности кадра.
Проект без уровня (создан до кредитов) выбирает модели как раньше.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pipeline  # noqa: E402
import providers  # noqa: E402

TOP = set(providers.VIDEO_TIERS[0][1])
MIDDLE = set(providers.VIDEO_TIERS[1][1])
LIGHT = set(providers.VIDEO_TIERS[2][1])


@pytest.mark.parametrize("importance, tier, expected", [
    (0.92, "economy", 0.0),
    (0.92, "medium", 0.5),
    (0.92, "premium", 0.92),
    (0.35, "medium", 0.35),
    (0.92, None, 0.92),
    (0.92, "", 0.92),
    (0.92, "unknown", 0.92),
])
def test_ceiling(importance, tier, expected):
    assert pipeline.capped_importance(importance, tier) == expected


def test_economy_gets_only_light_models():
    order = providers.video_order(pipeline.capped_importance(0.92, "economy"))
    assert order and set(order) <= LIGHT


def test_medium_never_reaches_the_top_models():
    order = providers.video_order(pipeline.capped_importance(0.92, "medium"))
    assert not set(order) & TOP
    assert order[0] in MIDDLE


def test_premium_complex_shot_starts_with_the_top_models():
    order = providers.video_order(pipeline.capped_importance(0.92, "premium"))
    assert order[0] in TOP


def test_project_without_a_tier_is_unchanged():
    assert providers.video_order(pipeline.capped_importance(0.92, None)) == providers.video_order(0.92)
