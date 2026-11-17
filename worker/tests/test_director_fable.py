"""«Режиссёр» на Fable 5.2: запрос к Anthropic собран по правилам модели.

Сеть не используется: клиент Anthropic подменён. Проверяется то, что ломается
молча и за деньги:

* потолок ответа. У Fable 5.2 размышление включено всегда и входит в
  max_tokens; при прежних 4000 сценарий мог оборваться, а вызов оплачен;
* отказ фильтра безопасности. Без запасной модели ложное срабатывание
  роняло бы проект целиком;
* цена. Один общий тариф на все модели расходился с кошельком в разы;
* параметры, которые Fable 5.2 отклоняет ошибкой 400 (thinking,
  temperature, принудительный tool_choice), не отправляются вовсе.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from steps import script_step  # noqa: E402

SCRIPT = {
    "title": "Тест",
    "continuity": "a white ceramic cup on a wooden table",
    "scenes": [
        {"narration": "Первая сцена рассказа.", "image_prompt": "shot one", "shots": []},
        {"narration": "Вторая сцена рассказа.", "image_prompt": "shot two", "shots": []},
        {"narration": "Третья сцена рассказа.", "image_prompt": "shot three", "shots": []},
    ],
}


def _response(stop_reason="end_turn", model="claude-fable-5-2", tokens=(1000, 2000), text=None):
    return types.SimpleNamespace(
        stop_reason=stop_reason, model=model,
        content=[types.SimpleNamespace(type="thinking", thinking=""),
                 types.SimpleNamespace(type="text", text=json.dumps(SCRIPT) if text is None else text)],
        usage=types.SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1]),
    )


class FakeAnthropic:
    """Подделка anthropic.Anthropic: помнит, какой путь и с чем вызвали."""

    calls: list[tuple[str, dict]] = []
    reply = None

    def __init__(self, **kwargs):
        self.init = kwargs
        outer = self

        class _Messages:
            def __init__(self, name):
                self.name = name

            def create(self, **kw):
                FakeAnthropic.calls.append((self.name, kw))
                reply = FakeAnthropic.reply
                return reply(kw) if callable(reply) else reply

        self.messages = _Messages("messages")
        self.beta = types.SimpleNamespace(messages=_Messages("beta"))
        FakeAnthropic.last = outer


@pytest.fixture
def cfg(monkeypatch):
    import anthropic

    for name, value in {
        "SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test",
        "MVP_SAFE_MODE": "0", "SCRIPT_MODE": "llm", "LLM_PROVIDER": "anthropic",
        "SCRIPT_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test-key",
        "ELEVENLABS_API_KEY": "test", "FAL_KEY": "test",
    }.items():
        monkeypatch.setenv(name, value)
    for name in ("LLM_MODEL", "LLM_EFFORT", "ANTHROPIC_WORKSPACE_ID"):
        monkeypatch.delenv(name, raising=False)
    FakeAnthropic.calls = []
    FakeAnthropic.reply = _response()
    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    from config import Config

    return Config


def test_fable_is_the_default_director(cfg):
    assert cfg().llm_model == "claude-fable-5-2"
    assert cfg().llm_effort == "medium"


def test_unknown_effort_is_refused_at_start(cfg, monkeypatch):
    monkeypatch.setenv("LLM_EFFORT", "extreme")
    with pytest.raises(RuntimeError, match="LLM_EFFORT"):
        cfg()


def test_fable_request_follows_the_model_rules(cfg):
    data, _ = script_step._via_anthropic(cfg(), "write a script", script_step.SCENES_SCHEMA)
    assert data["title"] == "Тест"
    path, kw = FakeAnthropic.calls[0]
    assert path == "beta", "запасная модель при отказе доступна только на beta-пути"
    assert kw["model"] == "claude-fable-5-2"
    assert kw["fallbacks"] == "default"
    assert kw["betas"] == ["server-side-fallback-2026-07-01"]
    assert kw["max_tokens"] >= 16000, "размышление входит в потолок ответа"
    assert kw["output_config"]["effort"] == "medium"
    assert kw["output_config"]["format"]["type"] == "json_schema"
    # Эти параметры Fable 5.2 отклоняет ошибкой 400.
    for forbidden in ("thinking", "temperature", "top_p", "top_k", "tool_choice"):
        assert forbidden not in kw, forbidden
    assert FakeAnthropic.last.init["timeout"] >= 300


def test_older_model_goes_the_plain_way(cfg, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "claude-opus-4-8")
    FakeAnthropic.reply = _response(model="claude-opus-4-8")
    script_step._via_anthropic(cfg(), "write", script_step.SCENES_SCHEMA)
    path, kw = FakeAnthropic.calls[0]
    assert path == "messages" and "fallbacks" not in kw and "betas" not in kw
    assert kw["output_config"]["effort"] == "medium"


def test_effort_is_not_sent_to_a_model_that_rejects_it(cfg, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "claude-haiku-4-5")
    FakeAnthropic.reply = _response(model="claude-haiku-4-5")
    script_step._via_anthropic(cfg(), "write", script_step.SCENES_SCHEMA)
    assert "effort" not in FakeAnthropic.calls[0][1]["output_config"]


@pytest.mark.parametrize("model, served_by, expected", [
    ("claude-fable-5-2", "claude-fable-5-2", 1000 / 1e6 * 8 + 2000 / 1e6 * 40),
    ("claude-opus-5-5", "claude-opus-5-5", 1000 / 1e6 * 4 + 2000 / 1e6 * 20),
    ("claude-haiku-5-5", "claude-haiku-5-5", 1000 / 1e6 * 0.10 + 2000 / 1e6 * 0.50),
    # Основная отказала, ответила запасная: платим по её тарифу.
    ("claude-fable-5-2", "claude-opus-4-8", 1000 / 1e6 * 5 + 2000 / 1e6 * 25),
])
def test_cost_follows_the_model_that_answered(cfg, monkeypatch, model, served_by, expected):
    monkeypatch.setenv("LLM_MODEL", model)
    FakeAnthropic.reply = _response(model=served_by)
    _, cost = script_step._via_anthropic(cfg(), "write", script_step.SCENES_SCHEMA)
    assert cost == pytest.approx(expected)


def test_unknown_model_uses_the_fallback_tariff():
    from config import COSTS, anthropic_price

    assert anthropic_price("claude-something-new") == (
        COSTS["anthropic_input_per_mtok"], COSTS["anthropic_output_per_mtok"])


def test_refusal_of_the_whole_chain_is_a_refusal_not_a_crash(cfg):
    FakeAnthropic.reply = _response(stop_reason="refusal", text="")
    with pytest.raises(script_step.ScriptRefusedError):
        script_step._via_anthropic(cfg(), "write", script_step.SCENES_SCHEMA)


def test_cut_off_answer_is_an_error_the_chain_can_recover_from(cfg):
    FakeAnthropic.reply = _response(stop_reason="max_tokens", text="")
    with pytest.raises(RuntimeError, match="лимит токенов"):
        script_step._via_anthropic(cfg(), "write", script_step.SCENES_SCHEMA)


def test_answer_without_text_is_named(cfg):
    FakeAnthropic.reply = _response(text="   ")
    with pytest.raises(RuntimeError, match="без текста"):
        script_step._via_anthropic(cfg(), "write", script_step.SCENES_SCHEMA)


def test_director_sees_at_most_two_product_photos(cfg):
    urls = [f"https://cdn.example/ref{i}.jpg" for i in range(4)]
    script_step._via_anthropic(cfg(), "write an ad", script_step.AD_SCENES_SCHEMA, images=urls)
    content = FakeAnthropic.calls[0][1]["messages"][0]["content"]
    images = [b for b in content if b["type"] == "image"]
    assert [b["source"] for b in images] == [{"type": "url", "url": u} for u in urls[:2]]
    assert content[-1] == {"type": "text", "text": "write an ad"}


def test_photos_go_only_to_the_provider_that_can_read_them(monkeypatch):
    """OpenRouter получает прежний текстовый запрос — без снимков и без слов о них."""
    seen = {}

    class Cfg:
        script_provider_chain = ["openrouter", "anthropic"]
        llm_provider = "openrouter"

        def has_script_key(self, provider):
            return True

        def script_model(self, provider):
            return f"{provider}-model"

    def openrouter(cfg_, prompt, schema):
        seen["openrouter"] = prompt
        raise RuntimeError("упал")

    def anthropic(cfg_, prompt, schema, images=None):
        seen["anthropic"] = (prompt, images)
        return SCRIPT, 0.05

    monkeypatch.setattr(script_step, "_via_openrouter", openrouter)
    monkeypatch.setattr(script_step, "_via_anthropic", anthropic)
    result = script_step._run(Cfg(), "ad prompt", script_step.AD_SCENES_SCHEMA, 3, 20, "Товар",
                              images=["https://cdn.example/a.jpg"])
    assert seen["openrouter"] == "ad prompt"
    assert seen["anthropic"] == ("ad prompt" + script_step.PHOTO_NOTE, ["https://cdn.example/a.jpg"])
    assert result["provider"] == "anthropic"
