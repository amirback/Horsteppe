"""Кадры рисуются в формате проекта, а не всегда вертикально.

Было: при любом `aspect_ratio` сценарий просил «vertical 9:16», а генераторы
рисовали 576×1024 / 1024×1792 / 1080×1920. В ролике 16:9 монтаж отрезал
больше половины такого кадра. Сеть не используется.
"""
from __future__ import annotations

import base64
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from steps import image_step, script_step  # noqa: E402
from test_image_provider import FakeClient, FakeResponse  # noqa: E402


@pytest.fixture
def cfg(monkeypatch):
    for key, value in {
        "SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test",
        "MVP_SAFE_MODE": "0", "SCRIPT_MODE": "mock", "ELEVENLABS_API_KEY": "test",
        "TOGETHER_API_KEY": "test-key", "FAL_KEY": "test", "POLLINATIONS_BACKOFF_SEC": "0",
    }.items():
        monkeypatch.setenv(key, value)

    def make(provider: str):
        monkeypatch.setenv("IMAGE_PROVIDER", provider)
        from config import Config

        return Config()

    return make


def _sent(monkeypatch, responses):
    state = {"responses": list(responses), "calls": []}
    monkeypatch.setattr(image_step.httpx, "Client", lambda **kw: FakeClient(state))
    return state


@pytest.mark.parametrize("aspect, size", [
    ("9:16", (576, 1024)), ("16:9", (1024, 576)), ("1:1", (768, 768)), ("4:5", (704, 880)),
])
def test_pollinations_draws_in_the_project_format(cfg, monkeypatch, tmp_path, aspect, size):
    state = _sent(monkeypatch, [FakeResponse(content=b"x" * 5000)])
    with image_step.frame(aspect):
        image_step.generate_image(cfg("pollinations"), "steppe", tmp_path / "s.png")
    params = state["calls"][0][1]
    assert (params["width"], params["height"]) == size


@pytest.mark.parametrize("aspect, size", [
    ("9:16", (1024, 1792)), ("16:9", (1792, 1024)), ("1:1", (1024, 1024)), ("4:5", (1024, 1280)),
])
def test_together_draws_in_the_project_format(cfg, monkeypatch, tmp_path, aspect, size):
    blob = base64.b64encode(b"j" * 4000).decode()
    state = _sent(monkeypatch, [FakeResponse(payload={"data": [{"b64_json": blob}]})])
    with image_step.frame(aspect):
        image_step.generate_image(cfg("together"), "steppe", tmp_path / "s.png")
    sent = state["calls"][0][1]["json"]
    assert (sent["width"], sent["height"]) == size
    assert sent["width"] % 16 == 0 and sent["height"] % 16 == 0 and max(size) <= 1792


def test_fal_draws_the_final_frame_size(cfg, monkeypatch, tmp_path):
    seen = {}

    def subscribe(model, arguments=None, **kw):
        seen.update(arguments)
        return {"images": [{"url": "https://cdn.example/a.png"}]}

    monkeypatch.setitem(sys.modules, "fal_client", types.SimpleNamespace(subscribe=subscribe))
    monkeypatch.setattr(image_step, "call_with_timeout", lambda fn, *a, timeout=None, label=None, **kw: fn(*a, **kw))
    _sent(monkeypatch, [FakeResponse(content=b"f" * 4000)])
    with image_step.frame("16:9"):
        image_step.generate_image(cfg("fal"), "steppe", tmp_path / "s.png")
    assert seen["image_size"] == {"width": 1920, "height": 1080}


def test_placeholder_in_safe_mode_has_the_project_format(cfg, monkeypatch, tmp_path):
    monkeypatch.setenv("MVP_SAFE_MODE", "1")
    sizes = []
    monkeypatch.setattr(image_step.safe_mode, "placeholder_image",
                        lambda prompt, out, size, index: sizes.append(size) or 0.0)
    with image_step.frame("1:1"):
        image_step.generate_image(cfg("pollinations"), "steppe", tmp_path / "s.png")
    assert sizes == [(1080, 1080)]


def test_without_a_format_everything_stays_vertical(cfg, monkeypatch, tmp_path):
    """Прежние вызовы без формата получают ровно то, что получали раньше."""
    state = _sent(monkeypatch, [FakeResponse(content=b"x" * 5000), FakeResponse(content=b"x" * 5000)])
    image_step.generate_image(cfg("pollinations"), "steppe", tmp_path / "a.png")
    with image_step.frame("21:9"):  # неизвестный формат — вертикаль, как в монтаже
        image_step.generate_image(cfg("pollinations"), "steppe", tmp_path / "b.png")
    assert [(p["width"], p["height"]) for _, p in state["calls"]] == [(576, 1024), (576, 1024)]


def test_format_is_restored_after_the_block():
    with image_step.frame("16:9"):
        with image_step.frame("1:1"):
            assert image_step._aspect() == "1:1"
        assert image_step._aspect() == "16:9"
    assert image_step._aspect() == "9:16"


# --- сценарий --------------------------------------------------------------------

def _llm_prompt(monkeypatch, **kwargs) -> str:
    seen = {}

    def fake_run(cfg_, prompt, schema, n, words, title, images=None):
        seen["prompt"] = prompt
        return {"title": title, "scenes": []}

    monkeypatch.setattr(script_step, "_run", fake_run)
    cfg_ = types.SimpleNamespace(effective_script_mode="llm")
    script_step.generate_script(cfg_, "Степь на рассвете", "cinematic", 30, **kwargs)
    return seen["prompt"]


def test_script_asks_for_the_project_format(monkeypatch):
    prompt = _llm_prompt(monkeypatch, aspect="16:9")
    assert "horizontal 16:9" in prompt and "9:16" not in prompt


def test_script_without_a_format_stays_vertical(monkeypatch):
    assert "vertical 9:16" in _llm_prompt(monkeypatch)


def test_ad_script_asks_for_the_project_format(monkeypatch):
    import product_brief

    brief = types.SimpleNamespace(product_name="Чай", structure=lambda d: ["hook", "product", "cta"])
    monkeypatch.setattr(product_brief, "ad_prompt", lambda *a: "AD PROMPT")
    prompt = _llm_prompt(monkeypatch, brief=brief, aspect="1:1")
    assert prompt.startswith("AD PROMPT") and "square 1:1" in prompt


def test_template_script_uses_the_project_format():
    script = script_step._mock_script("Степь", "cinematic", 20, "16:9")
    assert all("horizontal 16:9 composition" in s["image_prompt"] for s in script["scenes"])
