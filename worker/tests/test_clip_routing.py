"""Выбор маршрутизатора должен доходить до провайдера.

До этой правки он не доходил: кадр всегда получал первый провайдер из
настройки, имя выбранной модели терялось по дороге, а в базу писалась
модель, которая в работе не участвовала.

Сети здесь нет — проверяется порядок обхода и состав запроса.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from steps import video_step  # noqa: E402


class FakeConfig:
    mvp_safe_mode = False
    video_mode = "provider"
    video_providers = ["higgsfield", "fal", "replicate"]
    higgsfield_credential = "id:secret-not-real"
    higgsfield_video_model = "kling-video/v2.5-turbo/pro/image-to-video"
    fal_key = "not-a-real-key"
    fal_video_model = "fal-ai/kling-video/v2.1/standard/image-to-video"
    replicate_api_token = "not-a-real-token"
    replicate_video_model = "some/model"


# ------------------------------------------------------- порядок обхода --

def test_chosen_provider_goes_first():
    cfg = FakeConfig()
    assert video_step._chain_for(cfg, "replicate")[0] == "replicate"
    assert video_step._chain_for(cfg, "fal")[0] == "fal"


def test_rest_of_the_chain_survives_as_backup():
    """Выбор меняет порядок, а не отменяет запасных."""
    chain = video_step._chain_for(FakeConfig(), "replicate")
    assert sorted(chain) == sorted(FakeConfig.video_providers)


def test_provider_outside_the_setting_is_ignored():
    """Настройка главнее подсказки: чего человек не включал, то не зовём."""
    chain = video_step._chain_for(FakeConfig(), "runway")
    assert chain == FakeConfig.video_providers


def test_no_hint_keeps_the_old_order():
    assert video_step._chain_for(FakeConfig(), None) == FakeConfig.video_providers


# ---------------------------------------------- модель не уходит чужому --

def test_model_name_is_not_handed_to_a_different_provider(monkeypatch):
    """Путь Higgsfield в fal — это отказ за деньги.

    Маршрутизатор предложил Higgsfield, тот упал. Запасной fal обязан
    взять СВОЮ модель из настройки, а не чужой путь.
    """
    seen: list = []

    def fail_higgsfield(cfg, url, prompt, out, model=None):
        seen.append(("higgsfield", model))
        raise video_step.VideoError("притворяемся, что упал")

    def record_fal(cfg, url, prompt, out, model, price):
        seen.append(("fal", model))
        return video_step.ClipResult("fal", model or cfg.fal_video_model, price)

    monkeypatch.setattr(video_step, "_via_higgsfield", fail_higgsfield)
    monkeypatch.setattr(video_step, "_via_fal", record_fal)

    done = video_step.generate_clip(
        FakeConfig(), "https://example.invalid/a.png", "push in", Path("/tmp/none.mp4"),
        provider="higgsfield", model="kling-video/v2.5-turbo/pro/image-to-video",
        cost_usd=0.35,
    )

    assert seen[0] == ("higgsfield", "kling-video/v2.5-turbo/pro/image-to-video")
    assert seen[1] == ("fal", None), "запасному провайдеру ушёл чужой путь модели"
    assert done.provider == "fal"
    assert done.model == FakeConfig.fal_video_model


def test_old_call_without_a_provider_still_reaches_fal(monkeypatch):
    """Регрессия: вызов с `model=`, но без `provider=`, терял модель.

    До появления маршрутизатора аргумент `model` всегда означал модель fal.
    Новая адресация подсказки чуть не сломала это молча.
    """
    seen: list = []

    def record_fal(cfg, url, prompt, out, model, price):
        seen.append(model)
        return video_step.ClipResult("fal", model or cfg.fal_video_model, price)

    cfg = FakeConfig()
    cfg.video_providers = ["fal"]
    monkeypatch.setattr(video_step, "_via_fal", record_fal)

    done = video_step.generate_clip(
        cfg, "https://example.invalid/a.png", "push in", Path("/tmp/none.mp4"),
        model="fal-ai/kling-video/v2.1/pro/image-to-video", cost_usd=0.95,
    )
    assert seen == ["fal-ai/kling-video/v2.1/pro/image-to-video"]
    assert done.model.endswith("v2.1/pro/image-to-video")


def test_failed_provider_is_named_correctly(monkeypatch):
    """В сообщении об ошибке должен стоять тот, кто упал."""
    def always_fail(*a, **k):
        raise video_step.VideoError("нет связи")

    for name in ("_via_higgsfield", "_via_fal", "_via_replicate"):
        monkeypatch.setattr(video_step, name, always_fail)

    with pytest.raises(video_step.VideoError) as err:
        video_step.generate_clip(
            FakeConfig(), "https://example.invalid/a.png", "push in",
            Path("/tmp/none.mp4"), provider="replicate",
        )
    text = str(err.value)
    for name in ("higgsfield", "fal", "replicate"):
        assert name in text, f"в отчёте нет {name}: {text}"


# ------------------------------------------- рычаги качества в запросе --

def test_request_carries_the_unused_quality_levers(monkeypatch):
    """`cfg_scale` и `negative_prompt` у Kling есть, а мы их не слали.

    Проверяется тело запроса, а не наличие переменных: константа, которую
    забыли положить в payload, выглядит в коде совершенно так же.
    """
    captured: dict = {}

    def fake_submit(client, url, headers, payload):
        captured["url"] = url
        captured["payload"] = payload
        raise video_step.VideoError("дальше не идём — тело запроса уже снято")

    monkeypatch.setattr(video_step, "_higgsfield_submit", fake_submit)

    with pytest.raises(video_step.VideoError):
        video_step._via_higgsfield(
            FakeConfig(), "https://example.invalid/a.png", "slow push in",
            Path("/tmp/none.mp4"), "kling-video/v2.5-turbo/standard/image-to-video",
        )

    payload = captured["payload"]
    assert payload["prompt"] == "slow push in"
    assert payload["image_url"] == "https://example.invalid/a.png"
    assert 0.0 <= payload["cfg_scale"] <= 1.0
    assert payload["negative_prompt"].strip(), "негативный промпт пуст"
    assert payload["duration"] in (5, 10)
    # Модель от маршрутизатора, а не из настройки.
    assert captured["url"].endswith("kling-video/v2.5-turbo/standard/image-to-video")


def test_setting_is_used_when_the_router_says_nothing(monkeypatch):
    captured: dict = {}

    def fake_submit(client, url, headers, payload):
        captured["url"] = url
        raise video_step.VideoError("стоп")

    monkeypatch.setattr(video_step, "_higgsfield_submit", fake_submit)
    with pytest.raises(video_step.VideoError):
        video_step._via_higgsfield(
            FakeConfig(), "https://example.invalid/a.png", "x", Path("/tmp/none.mp4"),
        )
    assert captured["url"].endswith(FakeConfig.higgsfield_video_model)


def test_no_secret_reaches_the_request_body(monkeypatch):
    """Ключ живёт в заголовке. В теле ему делать нечего."""
    captured: dict = {}

    def fake_submit(client, url, headers, payload):
        captured["payload"] = payload
        raise video_step.VideoError("стоп")

    monkeypatch.setattr(video_step, "_higgsfield_submit", fake_submit)
    with pytest.raises(video_step.VideoError):
        video_step._via_higgsfield(
            FakeConfig(), "https://example.invalid/a.png", "x", Path("/tmp/none.mp4"),
        )
    assert "secret-not-real" not in str(captured["payload"])
