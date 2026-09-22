"""Step 2: per-scene voice-over via ElevenLabs.

TTS runs BEFORE image/video generation: the real narration duration of each
scene drives the length of its visual segment, which is how audio and video
stay in sync in the final render.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import httpx

import safe_mode
from config import COSTS, Config

log = logging.getLogger("worker.tts")

API_BASE = "https://api.elevenlabs.io/v1"

# Озвучка — единственный платный шаг без запасного провайдера. У картинок и
# видео есть цепочка: не справился один, пробуем соседа. Здесь соседа нет, и
# единственный ответ «слишком много запросов» убивал весь проект вместе с
# уже оплаченными кадрами. Повтор — единственная доступная страховка.
ATTEMPTS = int(os.environ.get("ELEVENLABS_ATTEMPTS", "3"))

# Коды, на которых повтор осмыслен: перегрузка и временные сбои на их
# стороне. Набор тот же, что у Higgsfield, — он взят из их же стратегии
# повторов и здесь работает по той же причине.
RETRY_CODES = {408, 429, 500, 502, 503, 504}

# Минимальный правдоподобный размер mp3. Ответ 200 с телом в сто байт — это
# не речь, а сообщение об ошибке, и узнать об этом лучше здесь, чем через
# три шага, когда монтаж не сможет измерить длительность.
MIN_AUDIO_BYTES = 512


class TtsError(Exception):
    pass


def synthesize(cfg: Config, text: str, out_path: Path) -> float:
    """Generate an mp3 voice-over for `text`, save to out_path.
    Returns the estimated cost in USD."""
    if not safe_mode.is_paid_allowed(cfg):
        return safe_mode.placeholder_voice(text, out_path)

    url = f"{API_BASE}/text-to-speech/{cfg.elevenlabs_voice_id}"
    payload = {
        "text": text,
        "model_id": cfg.elevenlabs_tts_model,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
    }
    headers = {"xi-api-key": cfg.elevenlabs_api_key}

    last = ""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with httpx.Client(timeout=120) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as e:
            last = f"сеть — {e}"
            if attempt == ATTEMPTS:
                break
            _wait(attempt, last)
            continue

        if resp.status_code == 200:
            if len(resp.content) < MIN_AUDIO_BYTES:
                # Повторять бессмысленно: это не перегрузка, а ответ не той
                # формы. Пусть причина дойдёт до человека целиком.
                raise TtsError(
                    f"ElevenLabs вернул {len(resp.content)} байт вместо речи: "
                    f"{resp.text[:300]}"
                )
            out_path.write_bytes(resp.content)
            return len(text) / 1000 * COSTS["elevenlabs_per_1k_chars"]

        if resp.status_code == 401:
            # Неверный ключ повтором не исправить.
            raise TtsError("ElevenLabs: неверный API-ключ")

        last = f"HTTP {resp.status_code}: {resp.text[:300]}"
        if resp.status_code not in RETRY_CODES or attempt == ATTEMPTS:
            break
        _wait(attempt, last)

    if "429" in last:
        raise TtsError(f"ElevenLabs: превышен лимит запросов, попробуйте позже ({last})")
    raise TtsError(f"ElevenLabs не отдал озвучку за {ATTEMPTS} попытки — {last}")


def _wait(attempt: int, reason: str) -> None:
    """Пауза растёт, чтобы повтор не добавлял нагрузки тому, кто ей уже
    захлёбывается."""
    pause = 2 ** attempt
    log.warning("ElevenLabs: повтор через %d с (попытка %d) — %s", pause, attempt, reason)
    time.sleep(pause)
