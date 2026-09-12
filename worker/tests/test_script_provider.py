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


def test_word_budget_matches_the_measured_speech_rate():
    """Просили 30 секунд — получали 22.6, то есть на четверть меньше.

    Причин было две: в коде стоял темп 2.3 слова в секунду вместо
    замеренных 2.57, и модель писала меньше, чем просят (14-15 слов
    вместо 17). Допуск CLAUDE.md §8 — ±20%, так что это был выход
    за границу.
    """
    from steps import script_step

    per_scene = script_step._words_per_scene(30, 4)
    total = per_scene * 4
    # Даже если модель недодаст 12%, как раньше, ролик остаётся в допуске.
    shortfall = total * 0.88 / script_step.WORDS_PER_SECOND
    assert 24 <= shortfall <= 36, f"{per_scene} слов на сцену даёт {shortfall:.1f} с"
    # А при точном исполнении — не длиннее верхней границы допуска.
    exact = total / script_step.WORDS_PER_SECOND
    assert exact <= 36, f"{exact:.1f} с"


def test_word_budget_scales_with_duration():
    from steps import script_step

    assert script_step._words_per_scene(60, 4) > script_step._words_per_scene(30, 4)


def test_overlong_narration_is_cut_at_a_sentence_boundary():
    """Просьба «не меньше N слов» породила обратную беду.

    Модель написала 162 слова вместо 88, и ролик вышел 57 секунд вместо 30.
    Верхняя граница обязана быть жёсткой, а обрезка — по точке: обрыв на
    полуслове звучит как испорченная запись.
    """
    from steps import script_step

    long_text = " ".join([f"Предложение номер {i} здесь." for i in range(1, 21)])
    scenes = [{"narration": long_text, "image_prompt": "p", "shots": []}]
    out = script_step._clamp_narration(scenes, words_per_scene=20)

    words = out[0]["narration"].split()
    assert len(words) <= int(20 * script_step.NARRATION_OVERSHOOT)
    assert out[0]["narration"].rstrip().endswith("."), out[0]["narration"][-40:]


def test_narration_within_the_budget_is_left_alone():
    from steps import script_step

    scenes = [{"narration": "Короткая фраза сцены.", "image_prompt": "p", "shots": []}]
    assert script_step._clamp_narration(scenes, 20) == scenes


def test_one_giant_sentence_is_still_cut():
    """Единственное предложение длиннее лимита резать больше негде."""
    from steps import script_step

    scenes = [{"narration": " ".join(["слово"] * 100), "image_prompt": "p", "shots": []}]
    out = script_step._clamp_narration(scenes, 20)
    assert len(out[0]["narration"].split()) == int(20 * script_step.NARRATION_OVERSHOOT)


def test_every_plausible_script_length_lands_inside_the_tolerance():
    """Допуск CLAUDE.md §8 — ±20%. Проверяем оба края разом.

    Недобор уже давал 22.6 с вместо 30, перебор — 57.5 с вместо 30.
    Заказ и жёсткий потолок подобраны так, чтобы обе крайности остались
    внутри допуска.
    """
    from steps import script_step

    for requested in (15, 30, 45, 60):
        n = script_step._scene_count(requested)
        ordered = script_step._words_per_scene(requested, n)
        cap = int(ordered * script_step.NARRATION_OVERSHOOT)

        # Модель недодала столько же, сколько недодавала раньше.
        shortest = ordered * n * 0.88 / script_step.WORDS_PER_SECOND
        # Модель написала по самому потолку, и обрезка сработала.
        longest = cap * n / script_step.WORDS_PER_SECOND

        low, high = requested * 0.8, requested * 1.2
        assert low <= shortest <= high, f"{requested} с: недобор даёт {shortest:.1f} с"
        assert low <= longest <= high, f"{requested} с: перебор даёт {longest:.1f} с"
