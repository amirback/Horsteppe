"""Путь генерации сценария через OpenRouter.

Сеть не используется: httpx подменяется. Проверяются именно те случаи,
которые уже ломали конвейер раньше или ломают его тихо, — пустой ответ
модели, отказ модерации, отсутствие стоимости в ответе.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


SCENES = {
    "title": "Тест",
    "scenes": [
        {"narration": "Первая сцена рассказа.", "image_prompt": "cinematic shot one"},
        {"narration": "Вторая сцена рассказа.", "image_prompt": "cinematic shot two"},
    ],
}


class FakeResponse:
    def __init__(self, status: int, body: dict | None = None, text: str = ""):
        self.status_code = status
        self._body = body or {}
        self.text = text or json.dumps(self._body)

    def json(self):
        return self._body


class FakeClient:
    """Замена httpx.Client: возвращает заранее заданный ответ."""

    def __init__(self, response: FakeResponse):
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        return self._response


def _completion(content: str, cost: float | None = 0.0012, refusal: str | None = None,
                finish: str = "stop") -> dict:
    message: dict = {"content": content}
    if refusal:
        message["refusal"] = refusal
    body: dict = {"choices": [{"message": message, "finish_reason": finish}]}
    if cost is not None:
        body["usage"] = {"cost": cost}
    return body


@pytest.fixture()
def cfg(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test")
    monkeypatch.setenv("MVP_SAFE_MODE", "0")
    monkeypatch.setenv("SCRIPT_MODE", "llm")
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
    monkeypatch.setenv("FAL_KEY", "test")
    from config import Config

    return Config()


def _patch(monkeypatch, response: FakeResponse):
    from steps import script_step

    monkeypatch.setattr(script_step.httpx, "Client", lambda **kw: FakeClient(response))
    return script_step


def test_openrouter_returns_scenes_and_real_cost(monkeypatch, cfg):
    step = _patch(monkeypatch, FakeResponse(200, _completion(json.dumps(SCENES), cost=0.0031)))
    result = step.generate_script(cfg, "Тема", "cinematic", 30)
    assert len(result["scenes"]) == 2
    # Стоимость берётся из ответа, а не оценивается по токенам.
    assert result["cost_usd"] == pytest.approx(0.0031)


def test_empty_model_answer_is_an_error(monkeypatch, cfg):
    """Модель может вернуть рассуждения без итогового текста — это уже ломало конвейер."""
    step = _patch(monkeypatch, FakeResponse(200, _completion("")))
    with pytest.raises(RuntimeError, match="пустой ответ"):
        step.generate_script(cfg, "Тема", "cinematic", 30)


def test_moderation_refusal_is_not_retried_as_generic_error(monkeypatch, cfg):
    step = _patch(monkeypatch, FakeResponse(200, _completion("", refusal="no")))
    with pytest.raises(step.ScriptRefusedError):
        step.generate_script(cfg, "Тема", "cinematic", 30)


def test_out_of_credits_says_so_plainly(monkeypatch, cfg):
    step = _patch(monkeypatch, FakeResponse(402, {}, text="insufficient credits"))
    with pytest.raises(RuntimeError, match="средства"):
        step.generate_script(cfg, "Тема", "cinematic", 30)


def test_missing_cost_falls_back_to_estimate(monkeypatch, cfg):
    step = _patch(monkeypatch, FakeResponse(200, _completion(json.dumps(SCENES), cost=None)))
    result = step.generate_script(cfg, "Тема", "cinematic", 30)
    assert result["cost_usd"] > 0


def test_too_few_scenes_is_rejected(monkeypatch, cfg):
    bad = {"title": "x", "scenes": [{"narration": "одна", "image_prompt": "one"}]}
    step = _patch(monkeypatch, FakeResponse(200, _completion(json.dumps(bad))))
    with pytest.raises(RuntimeError, match="сцен"):
        step.generate_script(cfg, "Тема", "cinematic", 30)
