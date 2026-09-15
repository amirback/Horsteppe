"""Цепочка провайдеров сценария: кто пишет и что происходит при отказе.

Сценарий — лицо продукта, и он же единственный шаг, который раньше не имел
запасного пути: OpenRouter отвечал 429 или пустым телом, и падал весь проект.

Ни сети, ни ключей, ни денег: вызовы провайдеров подменяются.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

from steps import script_step  # noqa: E402
from steps.script_step import ScriptRefusedError  # noqa: E402

ANSWER = {
    "title": "Ролик",
    "continuity": "один и тот же герой",
    "scenes": [
        {"narration": "первая сцена про дело", "image_prompt": "frame one",
         "shots": [{"framing": "wide", "action": "start"}]},
        {"narration": "вторая сцена про дело", "image_prompt": "frame two",
         "shots": [{"framing": "close", "action": "end"}]},
    ],
}


class FakeCfg:
    """Ровно те поля конфигурации, которые читает шаг сценария."""

    def __init__(self, chain: list[str], keys: dict[str, bool]) -> None:
        self._chain = chain
        self._keys = keys
        self.llm_provider = chain[0]
        self.llm_model = "claude-opus-5"
        self.openrouter_model = "anthropic/claude-opus-5"

    @property
    def script_provider_chain(self) -> list[str]:
        return self._chain

    def has_script_key(self, provider: str) -> bool:
        return self._keys.get(provider, False)

    def script_model(self, provider: str) -> str:
        return self.openrouter_model if provider == "openrouter" else self.llm_model


class ChainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list[str] = []
        self._original = (script_step._via_anthropic, script_step._via_openrouter)

    def tearDown(self) -> None:
        script_step._via_anthropic, script_step._via_openrouter = self._original

    def answer(self, name: str, cost: float = 0.02):
        def caller(cfg, prompt, schema=None):
            self.calls.append(name)
            return ANSWER, cost
        return caller

    def failure(self, name: str, error: Exception):
        def caller(cfg, prompt, schema=None):
            self.calls.append(name)
            raise error
        return caller

    def run_chain(self, cfg: FakeCfg) -> dict:
        return script_step._run(cfg, "prompt", None, 2, 6, "Ролик")

    def test_claude_goes_first_when_it_is_first_in_the_chain(self) -> None:
        script_step._via_anthropic = self.answer("anthropic")
        script_step._via_openrouter = self.answer("openrouter")
        cfg = FakeCfg(["anthropic", "openrouter"], {"anthropic": True, "openrouter": True})

        result = self.run_chain(cfg)
        self.assertEqual(self.calls, ["anthropic"], "второго провайдера звать было незачем")
        self.assertEqual(result["provider"], "anthropic")
        self.assertEqual(result["model"], "claude-opus-5")

    def test_provider_without_a_key_is_skipped_not_fatal(self) -> None:
        script_step._via_anthropic = self.answer("anthropic")
        script_step._via_openrouter = self.answer("openrouter")
        cfg = FakeCfg(["anthropic", "openrouter"], {"anthropic": False, "openrouter": True})

        result = self.run_chain(cfg)
        self.assertEqual(self.calls, ["openrouter"])
        self.assertEqual(result["provider"], "openrouter")

    def test_failure_falls_through_to_the_next_provider(self) -> None:
        script_step._via_anthropic = self.failure("anthropic", RuntimeError("перегрузка"))
        script_step._via_openrouter = self.answer("openrouter")
        cfg = FakeCfg(["anthropic", "openrouter"], {"anthropic": True, "openrouter": True})

        result = self.run_chain(cfg)
        self.assertEqual(self.calls, ["anthropic", "openrouter"])
        self.assertEqual(result["provider"], "openrouter", "в учёт идёт настоящий автор")
        self.assertEqual(result["model"], "anthropic/claude-opus-5")

    def test_moderation_refusal_does_not_go_to_the_next_provider(self) -> None:
        """Отклонённую по содержанию тему отклонит и вторая модель."""
        script_step._via_anthropic = self.failure("anthropic", ScriptRefusedError("нельзя"))
        script_step._via_openrouter = self.answer("openrouter")
        cfg = FakeCfg(["anthropic", "openrouter"], {"anthropic": True, "openrouter": True})

        with self.assertRaises(ScriptRefusedError):
            self.run_chain(cfg)
        self.assertEqual(self.calls, ["anthropic"], "лишний платный вызов недопустим")

    def test_everyone_failed_names_the_chain(self) -> None:
        script_step._via_anthropic = self.failure("anthropic", RuntimeError("503"))
        script_step._via_openrouter = self.failure("openrouter", RuntimeError("429"))
        cfg = FakeCfg(["anthropic", "openrouter"], {"anthropic": True, "openrouter": True})

        with self.assertRaises(RuntimeError) as raised:
            self.run_chain(cfg)
        self.assertIn("anthropic", str(raised.exception))
        self.assertIn("openrouter", str(raised.exception))

    def test_cost_comes_from_the_provider_that_answered(self) -> None:
        script_step._via_anthropic = self.failure("anthropic", RuntimeError("нет"))
        script_step._via_openrouter = self.answer("openrouter", cost=0.031)
        cfg = FakeCfg(["anthropic", "openrouter"], {"anthropic": True, "openrouter": True})
        self.assertAlmostEqual(self.run_chain(cfg)["cost_usd"], 0.031)


class ConfigChainTest(unittest.TestCase):
    """Порядок из настроек: старые .env обязаны работать как раньше."""

    def setUp(self) -> None:
        import os
        self._backup = {k: os.environ.get(k) for k in
                        ("LLM_PROVIDER", "SCRIPT_PROVIDER", "MVP_SAFE_MODE", "SCRIPT_MODE",
                         "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")}
        os.environ.update({"MVP_SAFE_MODE": "1", "SCRIPT_MODE": "mock",
                           "SUPABASE_URL": "https://example.invalid",
                           "SUPABASE_SERVICE_ROLE_KEY": "test"})

    def tearDown(self) -> None:
        import os
        for key, value in self._backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def config(self, **env):
        import os
        os.environ.update({k: v for k, v in env.items()})
        from config import Config
        return Config()

    def test_old_setting_keeps_its_order_and_gains_a_fallback(self) -> None:
        import os
        os.environ.pop("SCRIPT_PROVIDER", None)
        cfg = self.config(LLM_PROVIDER="openrouter")
        self.assertEqual(cfg.script_provider_chain, ["openrouter", "anthropic"])

    def test_explicit_chain_wins(self) -> None:
        cfg = self.config(SCRIPT_PROVIDER="anthropic,openrouter", LLM_PROVIDER="openrouter")
        self.assertEqual(cfg.script_provider_chain, ["anthropic", "openrouter"])

    def test_junk_in_the_chain_is_ignored(self) -> None:
        cfg = self.config(SCRIPT_PROVIDER="anthropic, , gpt4all, anthropic")
        self.assertEqual(cfg.script_provider_chain, ["anthropic"])


if __name__ == "__main__":
    unittest.main()
