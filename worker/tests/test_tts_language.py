"""Казахский текст озвучивает модель, которая знает казахский.

eleven_multilingual_v2 (модель по умолчанию) поддерживает 29 языков, казахского
среди них нет. Сеть не используется.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from steps import tts_step  # noqa: E402

SPEECH = b"\xff\xfb" + b"\x00" * 2000
KAZAKH = "Таңертеңгі дала — ең әдемі көрініс."
RUSSIAN = "Утренняя степь — самое красивое зрелище."


class Cfg:
    mvp_safe_mode = False
    elevenlabs_voice_id = "voice"
    elevenlabs_api_key = "not-a-real-key"
    elevenlabs_tts_model = "eleven_multilingual_v2"
    elevenlabs_tts_model_kk = "eleven_v3"


class Reply:
    status_code, content, text = 200, SPEECH, ""


@pytest.mark.parametrize("text, model", [
    (KAZAKH, "eleven_v3"),
    (RUSSIAN, "eleven_multilingual_v2"),
    ("Morning in the steppe.", "eleven_multilingual_v2"),
    ("Қ", "eleven_v3"),
])
def test_model_follows_the_language_of_the_text(text, model):
    assert tts_step.tts_model(Cfg(), text) == model


def test_without_a_kazakh_model_the_default_one_is_used():
    class Old:  # настройки до появления отдельной модели
        elevenlabs_tts_model = "eleven_multilingual_v2"

    assert tts_step.tts_model(Old(), KAZAKH) == "eleven_multilingual_v2"
    blank = Cfg()
    blank.elevenlabs_tts_model_kk = ""
    assert tts_step.tts_model(blank, KAZAKH) == "eleven_multilingual_v2"


@pytest.mark.parametrize("text, model, stability", [
    (KAZAKH, "eleven_v3", 0.5),
    (RUSSIAN, "eleven_multilingual_v2", 0.45),
])
def test_request_carries_the_chosen_model(monkeypatch, tmp_path, text, model, stability):
    sent = {}

    class Client:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json=None, headers=None):
            sent.update(json)
            return Reply()

    monkeypatch.setattr(tts_step.safe_mode, "is_paid_allowed", lambda cfg: True)
    monkeypatch.setattr(tts_step.httpx, "Client", Client)
    tts_step.synthesize(Cfg(), text, tmp_path / "v.mp3")
    assert sent["model_id"] == model
    assert sent["voice_settings"]["stability"] == stability
    assert "language_code" not in sent, "язык модель определяет по тексту сама"


def test_config_defaults(monkeypatch):
    for key, value in {"SUPABASE_URL": "https://e.co", "SUPABASE_SERVICE_ROLE_KEY": "t",
                       "ELEVENLABS_API_KEY": "t"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("ELEVENLABS_TTS_MODEL_KK", raising=False)
    from config import Config

    assert Config().elevenlabs_tts_model_kk == "eleven_v3"
    monkeypatch.setenv("ELEVENLABS_TTS_MODEL_KK", "eleven_v4")
    assert Config().elevenlabs_tts_model_kk == "eleven_v4"
