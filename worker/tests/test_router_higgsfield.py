"""Маршрутизатор должен знать того провайдера, который реально делает клипы.

Дефект, из-за которого появился этот файл: в реестре были только модели fal,
а клипы делал Higgsfield — первый в цепочке. «Умный выбор модели» не влиял
ни на что, а в учёт затрат шла цена чужой модели.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import providers  # noqa: E402


@pytest.fixture
def only_higgsfield(monkeypatch):
    """Ключ есть только у Higgsfield — как на машине основателя."""
    for name in ("FAL_KEY", "TOGETHER_API_KEY", "REPLICATE_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HF_KEY", "id:secret-not-real")


def test_higgsfield_is_in_the_registry():
    models = {c.model for c in providers.REGISTRY if c.provider == "higgsfield"}
    assert "kling-video/v2.5-turbo/pro/image-to-video" in models
    assert "kling-video/v2.5-turbo/standard/image-to-video" in models


def test_paths_match_their_openapi():
    """Пути сверены с openapi.json 2.0.0: без ведущей косой, без хоста."""
    for cap in providers.REGISTRY:
        if cap.provider != "higgsfield":
            continue
        assert not cap.model.startswith("/"), cap.model
        assert "api.higgsfield.ai" not in cap.model, cap.model
        assert cap.model.endswith("image-to-video"), cap.model


def test_router_finds_a_model_with_only_higgsfield_key(only_higgsfield):
    """Раньше здесь было пусто, и кадр молча оставался фотографией."""
    choice = providers.choose("video", importance=1.0, needs_image_to_video=True)
    assert choice is not None
    assert choice.provider == "higgsfield"


KLING_4 = "kling-video/v4.0/image-to-video"
SEEDANCE_25 = "bytedance/seedance-2.5/image-to-video"
KLING_3_PRO = "kling-video/v3.0/pro/image-to-video"
WAN_3 = "alibaba/wan-3.0/image-to-video"
KLING_3_STD = "kling-video/v3.0/std/image-to-video"


@pytest.mark.parametrize("importance, expected", [
    (1.00, KLING_4),       # крючок
    (0.95, KLING_4),       # кульминация
    (0.80, KLING_4),       # действие
    (0.70, KLING_3_PRO),   # персонаж
    (0.55, KLING_3_PRO),   # второстепенный
    (0.35, WAN_3),         # фон
])
def test_shot_gets_the_model_of_its_level(only_higgsfield, importance, expected):
    """Уровни основателя (2026-11-14): главным кадрам — главные модели."""
    choice = providers.choose("video", importance=importance, needs_image_to_video=True)
    assert choice.model == expected


def test_background_shot_is_cheaper_than_the_hook(only_higgsfield):
    hook = providers.choose("video", importance=1.0, needs_image_to_video=True)
    background = providers.choose("video", importance=0.0, needs_image_to_video=True)
    assert background.cost_usd < hook.cost_usd


def test_background_never_climbs_to_the_hook_models(only_higgsfield):
    """Сколько бы денег ни было, фон не получает модель крючка."""
    choice = providers.choose("video", importance=0.35, needs_image_to_video=True, affordable_usd=100.0)
    assert choice.model not in (KLING_4, SEEDANCE_25)


def test_short_budget_steps_down_a_level(only_higgsfield):
    """На Kling 4.0 не хватает — крючок получает модель уровнем ниже, а не фото."""
    choice = providers.choose("video", importance=1.0, needs_image_to_video=True, affordable_usd=0.50)
    assert choice.model == KLING_3_PRO


def test_second_model_of_the_level_only_within_budget(only_higgsfield):
    """Seedance 2.5 дороже Kling 4.0: запасом она становится, только если бюджет кадра её покрывает."""
    assert [c.model for c in providers.next_models("higgsfield", KLING_4, budget_usd=5.0)] == [SEEDANCE_25]
    assert providers.next_models("higgsfield", KLING_4, budget_usd=1.0) == []
    assert providers.next_models("higgsfield", KLING_4) == [], "без бюджета — не дороже выбранной"
    assert [c.model for c in providers.next_models("higgsfield", WAN_3)] == [KLING_3_STD]


def test_old_models_have_no_queue(only_higgsfield):
    """Kling 2.5 Turbo вне уровней: после его отказа цепочка идёт к следующему провайдеру, как раньше."""
    assert providers.next_models("higgsfield", "kling-video/v2.5-turbo/pro/image-to-video", budget_usd=5.0) == []


def test_hailuo_is_refused_at_five_seconds(only_higgsfield):
    """У hailuo набор длительностей (6, 10) — пятёрку он отвергает.

    Без нижней границы модель проходила бы отбор и отказывала после
    вызова, то есть за деньги.
    """
    pool = providers.candidates("video", needs_image_to_video=True, duration_sec=5.0)
    assert not any("hailuo" in c.model for c in pool)

    pool_six = providers.candidates("video", needs_image_to_video=True, duration_sec=6.0)
    assert any("hailuo" in c.model for c in pool_six), "на шести секундах hailuo подходит"


def test_tight_budget_still_leaves_a_working_model(only_higgsfield):
    """Двадцати центов должно хватать на настоящее видео, а не на слайд-шоу."""
    pool = providers.candidates("video", needs_image_to_video=True, affordable_usd=0.20)
    assert pool, "при остатке $0.20 не нашлось ни одной модели"
