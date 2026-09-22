"""Негодный ответ сценариста передаёт ход следующему, а не роняет проект.

Дефект, из-за которого появился файл. Проверка ответа стояла ПОСЛЕ вызова и
вне попытки. Модель отвечала — значит, вызов оплачен, — но выдавала,
скажем, три сцены вместо четырёх. Проверка падала, цепочка провайдеров при
этом не пробовала следующего, и проект умирал целиком. Деньги за этот вызов
в журнал не попадали никогда.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from steps import script_step  # noqa: E402


class FakeConfig:
    effective_script_mode = "real"
    llm_provider = "anthropic"
    script_provider_chain = ["anthropic", "openrouter"]

    def has_script_key(self, provider: str) -> bool:
        return True

    def script_model(self, provider: str) -> str:
        return f"{provider}-model"


def _good(n: int = 3) -> dict:
    return {
        "title": "Заголовок",
        "continuity": "один и тот же товар на светлом столе",
        "scenes": [
            {
                "narration": "Короткая фраза для сцены номер %d здесь." % i,
                "image_prompt": "a bright product shot, vertical 9:16",
                "shots": [
                    {"shot_type": "wide", "visual_prompt": "wide product shot"},
                    {"shot_type": "close_up", "visual_prompt": "close up on texture"},
                ],
            }
            for i in range(n)
        ],
    }


def _chain(monkeypatch, anthropic, openrouter):
    monkeypatch.setattr(script_step, "_via_anthropic", anthropic)
    monkeypatch.setattr(script_step, "_via_openrouter", openrouter)


def test_bad_answer_hands_over_to_the_next_provider(monkeypatch):
    """Тот самый случай: ответ пришёл, но сцен не столько."""
    calls = []

    def anthropic(cfg, prompt, schema):
        calls.append("anthropic")
        return _good(1), 0.02  # сцен меньше, чем просили

    def openrouter(cfg, prompt, schema):
        calls.append("openrouter")
        return _good(3), 0.03

    _chain(monkeypatch, anthropic, openrouter)
    result = script_step._run(FakeConfig(), "prompt", {}, 3, 12, "тема")

    assert calls == ["anthropic", "openrouter"], "ход не передан следующему"
    assert result["provider"] == "openrouter"


def test_the_wasted_money_is_counted(monkeypatch):
    """Неудачная попытка оплачена, и в стоимость она обязана войти."""
    _chain(
        monkeypatch,
        lambda cfg, p, s: (_good(1), 0.02),
        lambda cfg, p, s: (_good(3), 0.03),
    )
    result = script_step._run(FakeConfig(), "prompt", {}, 3, 12, "тема")
    assert result["cost_usd"] == pytest.approx(0.05), (
        "в стоимость вошла только удачная попытка"
    )


def test_total_failure_carries_what_was_spent(monkeypatch):
    """Если не справился никто, сумма всё равно должна дойти до журнала."""
    _chain(
        monkeypatch,
        lambda cfg, p, s: (_good(1), 0.02),
        lambda cfg, p, s: (_good(9), 0.03),
    )
    with pytest.raises(script_step.ScriptFailed) as err:
        script_step._run(FakeConfig(), "prompt", {}, 3, 12, "тема")
    assert err.value.cost_usd == pytest.approx(0.05)


def test_a_provider_that_crashed_costs_nothing(monkeypatch):
    """Упавший вызов денег не стоит — приписывать их нельзя."""
    _chain(
        monkeypatch,
        lambda cfg, p, s: (_ for _ in ()).throw(RuntimeError("сеть")),
        lambda cfg, p, s: (_good(3), 0.03),
    )
    result = script_step._run(FakeConfig(), "prompt", {}, 3, 12, "тема")
    assert result["cost_usd"] == pytest.approx(0.03)


def test_moderation_refusal_stops_the_chain(monkeypatch):
    """Что отвергла одна модель, отвергнет и соседняя — платить дважды незачем."""
    calls = []

    def anthropic(cfg, prompt, schema):
        calls.append("anthropic")
        raise script_step.ScriptRefusedError("тема отклонена")

    def openrouter(cfg, prompt, schema):
        calls.append("openrouter")
        return _good(3), 0.03

    _chain(monkeypatch, anthropic, openrouter)
    with pytest.raises(script_step.ScriptRefusedError):
        script_step._run(FakeConfig(), "prompt", {}, 3, 12, "тема")
    assert calls == ["anthropic"], "после отказа модерации звонили дальше"


def test_first_good_answer_wins(monkeypatch):
    calls = []
    _chain(
        monkeypatch,
        lambda cfg, p, s: (calls.append("a"), (_good(3), 0.02))[1],
        lambda cfg, p, s: (calls.append("o"), (_good(3), 0.03))[1],
    )
    result = script_step._run(FakeConfig(), "prompt", {}, 3, 12, "тема")
    assert calls == ["a"]
    assert result["cost_usd"] == pytest.approx(0.02)
