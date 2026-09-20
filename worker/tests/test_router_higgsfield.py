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


def test_important_shot_gets_the_pro_model(only_higgsfield):
    choice = providers.choose("video", importance=1.0, needs_image_to_video=True)
    assert "pro" in choice.model, f"на крючок взяли {choice.model}"


def test_background_shot_gets_the_cheaper_model(only_higgsfield):
    choice = providers.choose("video", importance=0.0, needs_image_to_video=True)
    assert choice.cost_usd < 0.35, f"на фон взяли дорогую {choice.model} за ${choice.cost_usd}"


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
