"""Озвучка — единственный платный шаг без запасного провайдера.

У картинок и видео есть цепочка: не справился один, пробуем соседа. Здесь
соседа нет, и единственный ответ «слишком много запросов» убивал весь
проект вместе с уже оплаченными кадрами. Повтор — единственная доступная
страховка, и этот файл проверяет, что она не превратилась в упрямство:
неверный ключ повторять незачем.

Сети нет: httpx подменяется.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from steps import tts_step  # noqa: E402

SPEECH = b"\xff\xfb" + b"\x00" * 2000


class FakeConfig:
    mvp_safe_mode = False
    elevenlabs_voice_id = "voice"
    elevenlabs_tts_model = "model"
    elevenlabs_api_key = "not-a-real-key"


class FakeResponse:
    def __init__(self, status_code: int, content: bytes = b"") -> None:
        self.status_code = status_code
        self.content = content
        self.text = content.decode("utf-8", "replace")


class FakeClient:
    """Отдаёт заранее заготовленные ответы по очереди."""

    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, *_a, **_k):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def no_waiting(monkeypatch):
    monkeypatch.setattr(tts_step.time, "sleep", lambda _s: None)


def _install(monkeypatch, script) -> FakeClient:
    client = FakeClient(script)
    monkeypatch.setattr(tts_step.httpx, "Client", lambda **_k: client)
    return client


def test_speech_arrives_on_the_first_try(no_waiting, monkeypatch, tmp_path):
    client = _install(monkeypatch, [FakeResponse(200, SPEECH)])
    out = tmp_path / "voice.mp3"
    cost = tts_step.synthesize(FakeConfig(), "Привет", out)
    assert out.read_bytes() == SPEECH
    assert cost > 0
    assert client.calls == 1


def test_rate_limit_is_survived(no_waiting, monkeypatch, tmp_path):
    """Тот самый случай, который раньше убивал проект целиком."""
    client = _install(monkeypatch, [
        FakeResponse(429, b"slow down"),
        FakeResponse(200, SPEECH),
    ])
    out = tmp_path / "voice.mp3"
    tts_step.synthesize(FakeConfig(), "Привет", out)
    assert client.calls == 2
    assert out.exists()


def test_server_error_is_survived(no_waiting, monkeypatch, tmp_path):
    client = _install(monkeypatch, [
        FakeResponse(503, b"busy"), FakeResponse(502, b"bad gateway"),
        FakeResponse(200, SPEECH),
    ])
    tts_step.synthesize(FakeConfig(), "Привет", tmp_path / "voice.mp3")
    assert client.calls == 3


def test_network_hiccup_is_survived(no_waiting, monkeypatch, tmp_path):
    client = _install(monkeypatch, [
        tts_step.httpx.ConnectError("оборвалось"),
        FakeResponse(200, SPEECH),
    ])
    tts_step.synthesize(FakeConfig(), "Привет", tmp_path / "voice.mp3")
    assert client.calls == 2


def test_bad_key_is_not_retried(no_waiting, monkeypatch, tmp_path):
    """Повторять то, что повтором не чинится, — это трата времени человека."""
    client = _install(monkeypatch, [FakeResponse(401, b"unauthorized")])
    with pytest.raises(tts_step.TtsError) as err:
        tts_step.synthesize(FakeConfig(), "Привет", tmp_path / "voice.mp3")
    assert client.calls == 1
    assert "ключ" in str(err.value)


def test_giving_up_names_the_reason(no_waiting, monkeypatch, tmp_path):
    client = _install(monkeypatch, [FakeResponse(429, b"slow down")] * tts_step.ATTEMPTS)
    with pytest.raises(tts_step.TtsError) as err:
        tts_step.synthesize(FakeConfig(), "Привет", tmp_path / "voice.mp3")
    assert client.calls == tts_step.ATTEMPTS
    assert "лимит" in str(err.value)


def test_an_answer_that_is_not_speech_is_caught_here(no_waiting, monkeypatch, tmp_path):
    """Ответ 200 с телом в сто байт — это сообщение об ошибке, а не речь.

    Узнать об этом лучше здесь, чем через три шага, когда монтаж не сможет
    измерить длительность и скажет что-то невнятное.
    """
    _install(monkeypatch, [FakeResponse(200, b'{"detail":"quota exceeded"}')])
    out = tmp_path / "voice.mp3"
    with pytest.raises(tts_step.TtsError) as err:
        tts_step.synthesize(FakeConfig(), "Привет", out)
    assert "quota exceeded" in str(err.value)
    assert not out.exists(), "негодный ответ не должен попадать на диск"


def test_nothing_is_written_when_every_try_fails(no_waiting, monkeypatch, tmp_path):
    _install(monkeypatch, [FakeResponse(500, b"boom")] * tts_step.ATTEMPTS)
    out = tmp_path / "voice.mp3"
    with pytest.raises(tts_step.TtsError):
        tts_step.synthesize(FakeConfig(), "Привет", out)
    assert not out.exists()
