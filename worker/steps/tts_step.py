"""Step 2: per-scene voice-over via ElevenLabs.

TTS runs BEFORE image/video generation: the real narration duration of each
scene drives the length of its visual segment, which is how audio and video
stay in sync in the final render.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from config import COSTS, Config

log = logging.getLogger("worker.tts")

API_BASE = "https://api.elevenlabs.io/v1"


class TtsError(Exception):
    pass


def synthesize(cfg: Config, text: str, out_path: Path) -> float:
    """Generate an mp3 voice-over for `text`, save to out_path.
    Returns the estimated cost in USD."""
    url = f"{API_BASE}/text-to-speech/{cfg.elevenlabs_voice_id}"
    payload = {
        "text": text,
        "model_id": cfg.elevenlabs_tts_model,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
    }
    headers = {"xi-api-key": cfg.elevenlabs_api_key}

    with httpx.Client(timeout=120) as client:
        resp = client.post(url, json=payload, headers=headers)

    if resp.status_code == 401:
        raise TtsError("ElevenLabs: неверный API-ключ")
    if resp.status_code == 429:
        raise TtsError("ElevenLabs: превышен лимит запросов, попробуйте позже")
    if resp.status_code != 200:
        raise TtsError(f"ElevenLabs error {resp.status_code}: {resp.text[:500]}")

    out_path.write_bytes(resp.content)
    return len(text) / 1000 * COSTS["elevenlabs_per_1k_chars"]
