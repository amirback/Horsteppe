"""Бесплатный генератор кадров Pollinations.

Сеть не используется: httpx подменяется. Проверяются случаи, из-за которых
конвейер падал или мог записать мусор вместо кадра.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeResponse:
    def __init__(self, status=200, content=b"", content_type="image/jpeg", text=""):
        self.status_code = status
        self.content = content
        self.headers = {"content-type": content_type}
        self.text = text


class FakeClient:
    """Отдаёт ответы из общей очереди.

    Очередь и журнал вызовов общие для всех экземпляров: код создаёт новый
    httpx.Client на каждую попытку, и без этого повторы получали бы один и
    тот же первый ответ.
    """

    def __init__(self, state):
        self._state = state

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, params=None):
        self._state["calls"].append((url, params))
        return self._state["responses"].pop(0)


@pytest.fixture()
def cfg(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test")
    monkeypatch.setenv("MVP_SAFE_MODE", "0")
    monkeypatch.setenv("SCRIPT_MODE", "mock")
    monkeypatch.setenv("IMAGE_PROVIDER", "pollinations")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
    monkeypatch.delenv("FAL_KEY", raising=False)
    from config import Config

    return Config()


def _patch(monkeypatch, responses):
    from steps import image_step

    state = {"responses": list(responses), "calls": []}
    monkeypatch.setattr(image_step.httpx, "Client", lambda **kw: FakeClient(state))
    return image_step, state


def test_free_provider_saves_the_image_and_costs_nothing(monkeypatch, cfg, tmp_path):
    step, _ = _patch(monkeypatch, [FakeResponse(content=b"x" * 5000)])
    out = tmp_path / "scene.png"
    cost = step.generate_image(cfg, "a lone astronaut", out, index=0)
    assert out.read_bytes() == b"x" * 5000
    assert cost == 0.0


def test_fal_key_not_required_when_images_are_free(cfg):
    """Раньше воркер требовал ключ fal всегда — и падал на старте без него."""
    assert cfg.image_provider == "pollinations"
    assert cfg.fal_key == ""


def test_html_error_page_is_not_written_as_an_image(monkeypatch, cfg, tmp_path):
    step, _ = _patch(monkeypatch, [FakeResponse(content=b"<html>oops</html>", content_type="text/html")])
    with pytest.raises(step.ImageError, match="не изображение"):
        step.generate_image(cfg, "prompt", tmp_path / "s.png", index=0)


def test_tiny_response_is_retried_then_reported(monkeypatch, cfg, tmp_path):
    step, state = _patch(monkeypatch, [FakeResponse(content=b"tiny") for _ in range(3)])
    with pytest.raises(step.ImageError, match="не отдал кадр"):
        step.generate_image(cfg, "prompt", tmp_path / "s.png", index=0)
    assert len(state["calls"]) == 3  # три попытки, потом понятная ошибка


def test_server_error_is_retried_and_then_succeeds(monkeypatch, cfg, tmp_path):
    step, _ = _patch(monkeypatch, [FakeResponse(status=503), FakeResponse(content=b"y" * 4000)])
    out = tmp_path / "s.png"
    assert step.generate_image(cfg, "prompt", out, index=0) == 0.0
    assert out.exists()


def test_cyrillic_prompt_is_percent_encoded(monkeypatch, cfg, tmp_path):
    """Кириллица в адресе уже ломала генерацию в прошлой версии движка."""
    step, state = _patch(monkeypatch, [FakeResponse(content=b"z" * 4000)])
    step.generate_image(cfg, "космонавт в степи", tmp_path / "s.png", index=0)
    url, _ = state["calls"][0]
    assert "космонавт" not in url
    assert "%D0%BA" in url


def test_different_scenes_get_different_seeds(monkeypatch, cfg, tmp_path):
    step, s1 = _patch(monkeypatch, [FakeResponse(content=b"a" * 4000)])
    step.generate_image(cfg, "same prompt", tmp_path / "a.png", index=0)
    seed_a = s1["calls"][0][1]["seed"]
    step, s2 = _patch(monkeypatch, [FakeResponse(content=b"b" * 4000)])
    step.generate_image(cfg, "same prompt", tmp_path / "b.png", index=1)
    assert seed_a != s2["calls"][0][1]["seed"]


def test_chain_falls_through_to_the_next_provider(monkeypatch, tmp_path):
    """Падение одного провайдера не должно уносить весь проект.

    Ровно это и случилось на сервере: Pollinations отдал 500, и проект
    погиб, хотя сценарий и озвучка уже были оплачены.
    """
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test")
    monkeypatch.setenv("MVP_SAFE_MODE", "0")
    monkeypatch.setenv("SCRIPT_MODE", "mock")
    monkeypatch.setenv("IMAGE_PROVIDER", "pollinations,fal")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
    monkeypatch.setenv("FAL_KEY", "test")
    monkeypatch.setenv("POLLINATIONS_BACKOFF_SEC", "0")
    from config import Config
    from steps import image_step

    cfg = Config()
    assert cfg.image_providers == ["pollinations", "fal"]

    # Pollinations всегда отвечает 500…
    state = {"responses": [FakeResponse(status=503) for _ in range(3)], "calls": []}
    monkeypatch.setattr(image_step.httpx, "Client", lambda **kw: FakeClient(state))

    # …а fal отрабатывает.
    used = {}

    def fake_fal(cfg_, prompt, out_path):
        used["fal"] = True
        out_path.write_bytes(b"f" * 3000)
        return 0.006

    monkeypatch.setattr(image_step, "_via_fal", fake_fal)

    out = tmp_path / "s.png"
    cost = image_step.generate_image(cfg, "prompt", out, index=0)
    assert used.get("fal") is True
    assert cost == 0.006
    assert out.exists()


def test_chain_reports_every_provider_when_all_fail(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test")
    monkeypatch.setenv("MVP_SAFE_MODE", "0")
    monkeypatch.setenv("SCRIPT_MODE", "mock")
    monkeypatch.setenv("IMAGE_PROVIDER", "pollinations,fal")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
    monkeypatch.setenv("FAL_KEY", "test")
    monkeypatch.setenv("POLLINATIONS_BACKOFF_SEC", "0")
    from config import Config
    from steps import image_step

    state = {"responses": [FakeResponse(status=503) for _ in range(3)], "calls": []}
    monkeypatch.setattr(image_step.httpx, "Client", lambda **kw: FakeClient(state))

    def broken_fal(cfg_, prompt, out_path):
        raise image_step.ImageError("баланс исчерпан")

    monkeypatch.setattr(image_step, "_via_fal", broken_fal)

    with pytest.raises(image_step.ImageError) as e:
        image_step.generate_image(Config(), "prompt", tmp_path / "s.png", index=0)
    # В сообщении должны быть обе причины, иначе чинить придётся вслепую.
    assert "pollinations" in str(e.value) and "баланс исчерпан" in str(e.value)
