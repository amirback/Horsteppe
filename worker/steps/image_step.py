"""Шаг 3: кадр для каждой сцены.

Провайдер выбирается настройкой IMAGE_PROVIDER:

* `together` — бесплатный тариф FLUX.1-schnell, нужен только ключ. Отвечает
  предсказуемо, в том числе из дата-центра.
* `pollinations` — бесплатно и вовсе без аккаунта, но ненадёжен: на боевом
  размере кадра один и тот же запрос возвращался то за три секунды, то за
  тринадцать минут, а из дата-центра отдавал 500. Годится последним запасным.
* `fal` — платный, качество выше.

Провайдеры перечисляются в IMAGE_PROVIDER через запятую и пробуются по
очереди: один недоступный поставщик не должен уносить весь проект. Именно
так и вышло однажды — аккаунт fal заблокировали за исчерпанный баланс, и
проект падал на третьем шаге, хотя сценарий и озвучка уже были оплачены.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import base64
import hashlib
import time
import urllib.parse

import httpx

import safe_mode
from config import COSTS, Config

from ._timeout import CallTimeout, call_with_timeout

log = logging.getLogger("worker.image")

# Генерация кадра у fal обычно занимает секунды. Три минуты — заведомо
# избыточный запас; всё, что дольше, считается зависшим.
TIMEOUT_SEC = float(os.environ.get("FAL_IMAGE_TIMEOUT_SEC", "180"))

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"
# Бесплатный сервис отвечает медленнее платного и иногда даёт 5xx под нагрузкой.
# Минута — не «сколько он может думать», а «сколько мы готовы ждать»: замер на
# боевом размере кадра дал ответы в 3 секунды и в 13 минут на одном и том же
# запросе. Зависшая попытка должна умереть и уступить место следующей.
POLLINATIONS_TIMEOUT_SEC = float(os.environ.get("POLLINATIONS_TIMEOUT_SEC", "60"))
POLLINATIONS_ATTEMPTS = 3

TOGETHER_URL = "https://api.together.xyz/v1/images/generations"
TOGETHER_TIMEOUT_SEC = float(os.environ.get("TOGETHER_TIMEOUT_SEC", "90"))
TOGETHER_ATTEMPTS = 3
# Стороны кратны 16 и не выше 1792 — таковы требования эндпоинта.
TOGETHER_WIDTH = 1024
TOGETHER_HEIGHT = 1792
# FLUX.1-schnell рассчитан на 1–4 шага; больше ничего не улучшает.
TOGETHER_STEPS = 4
# Пауза между попытками. Бесплатный сервис отвечает 500 под нагрузкой, и
# повтор в ту же секунду только добавляет ему нагрузки.
POLLINATIONS_BACKOFF_SEC = float(os.environ.get("POLLINATIONS_BACKOFF_SEC", "5"))
# Меньше килобайта — это не кадр, а страница с ошибкой.
MIN_IMAGE_BYTES = 1024


class ImageError(Exception):
    pass


def generate_image(cfg: Config, prompt: str, out_path: Path, index: int = 0) -> float:
    """Generate a 1080x1920 image for `prompt`, save to out_path.
    Returns estimated cost in USD."""
    if not safe_mode.is_paid_allowed(cfg):
        return safe_mode.placeholder_image(prompt, out_path, (1080, 1920), index)

    chain = cfg.image_providers
    errors: list[str] = []
    for position, provider in enumerate(chain, start=1):
        try:
            if provider == "pollinations":
                return _via_pollinations(cfg, prompt, out_path, index)
            if provider == "together":
                return _via_together(cfg, prompt, out_path, index)
            return _via_fal(cfg, prompt, out_path)
        except ImageError as e:
            errors.append(f"{provider}: {e}")
            if position < len(chain):
                log.warning("%s не справился, пробую следующего: %s", provider, e)
            continue
    raise ImageError("Кадр не удалось получить ни у одного провайдера. " + " | ".join(errors))


def _via_pollinations(cfg: Config, prompt: str, out_path: Path, index: int) -> float:
    """Бесплатная генерация кадра. Ключ не нужен.

    Промпт кодируется percent-encoding в UTF-8: без этого кириллица и типографские
    знаки ломают адрес, и сервис возвращает не тот кадр или ошибку.
    """
    # Seed выводится из промпта: один и тот же кадр воспроизводится при повторе,
    # а разные сцены не получают одинаковую картинку.
    seed = int(hashlib.sha256(f"{index}:{prompt}".encode()).hexdigest()[:8], 16)
    url = POLLINATIONS_URL + urllib.parse.quote(prompt, safe="")
    params = {
        "width": 1080,
        "height": 1920,
        "model": cfg.pollinations_model,
        "nologo": "true",
        "seed": seed,
        "referrer": "horsteppe",
    }

    last = ""
    for attempt in range(1, POLLINATIONS_ATTEMPTS + 1):
        try:
            with httpx.Client(timeout=POLLINATIONS_TIMEOUT_SEC, follow_redirects=True) as client:
                resp = client.get(url, params=params)
        except httpx.HTTPError as e:
            last = f"сеть: {e}"
            log.warning("pollinations попытка %d/%d: %s", attempt, POLLINATIONS_ATTEMPTS, last)
            _pause(attempt)
            continue

        if resp.status_code >= 500:
            last = f"HTTP {resp.status_code}"
            log.warning("pollinations попытка %d/%d: %s", attempt, POLLINATIONS_ATTEMPTS, last)
            _pause(attempt)
            continue
        if resp.status_code != 200:
            raise ImageError(f"Pollinations вернул {resp.status_code}: {resp.text[:200]}")

        content_type = resp.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise ImageError(f"Pollinations вернул не изображение ({content_type or 'без типа'})")
        if len(resp.content) < MIN_IMAGE_BYTES:
            last = f"слишком маленький ответ ({len(resp.content)} байт)"
            log.warning("pollinations попытка %d/%d: %s", attempt, POLLINATIONS_ATTEMPTS, last)
            _pause(attempt)
            continue

        out_path.write_bytes(resp.content)
        return COSTS["pollinations_per_call"]

    raise ImageError(f"Pollinations не отдал кадр за {POLLINATIONS_ATTEMPTS} попытки — {last}")


def _via_together(cfg: Config, prompt: str, out_path: Path, index: int) -> float:
    """Кадр через Together AI. Бесплатный тариф FLUX.1-schnell, нужен ключ.

    Размер кадра здесь меньше финального: сервис принимает стороны кратными 16
    и не выше 1792. Это не потеря — Ken Burns всё равно увеличивает исходник
    вдвое и кадрирует под нужный формат.
    """
    if not cfg.together_api_key:
        raise ImageError("TOGETHER_API_KEY не задан")

    seed = int(hashlib.sha256(f"{index}:{prompt}".encode()).hexdigest()[:8], 16) % (2**31)
    payload = {
        "model": cfg.together_image_model,
        "prompt": prompt,
        "width": TOGETHER_WIDTH,
        "height": TOGETHER_HEIGHT,
        "steps": TOGETHER_STEPS,
        "n": 1,
        "seed": seed,
    }
    # Формат ответа не задаём: эндпоинт отдаёт либо ссылку, либо base64 —
    # разбираем оба, и запрос не ломается о неизвестное значение параметра.

    last = ""
    for attempt in range(1, TOGETHER_ATTEMPTS + 1):
        try:
            with httpx.Client(timeout=TOGETHER_TIMEOUT_SEC) as client:
                resp = client.post(
                    TOGETHER_URL,
                    headers={"Authorization": f"Bearer {cfg.together_api_key}"},
                    json=payload,
                )
        except httpx.HTTPError as e:
            last = f"сеть: {e}"
            log.warning("together попытка %d/%d: %s", attempt, TOGETHER_ATTEMPTS, last)
            _pause(attempt)
            continue

        # 429 — упёрлись в бесплатный лимит запросов в минуту, это лечится паузой.
        if resp.status_code == 429 or resp.status_code >= 500:
            last = f"HTTP {resp.status_code}"
            log.warning("together попытка %d/%d: %s", attempt, TOGETHER_ATTEMPTS, last)
            _pause(attempt)
            continue
        if resp.status_code != 200:
            raise ImageError(f"Together вернул {resp.status_code}: {resp.text[:200]}")

        data = (resp.json().get("data") or [{}])[0]
        encoded = data.get("b64_json")
        if encoded:
            blob = base64.b64decode(encoded)
        elif data.get("url"):
            with httpx.Client(timeout=TOGETHER_TIMEOUT_SEC) as client:
                img = client.get(data["url"])
                img.raise_for_status()
                blob = img.content
        else:
            raise ImageError("Together вернул ответ без изображения")

        if len(blob) < MIN_IMAGE_BYTES:
            last = f"слишком маленький ответ ({len(blob)} байт)"
            log.warning("together попытка %d/%d: %s", attempt, TOGETHER_ATTEMPTS, last)
            _pause(attempt)
            continue

        out_path.write_bytes(blob)
        return COSTS["together_image_per_call"]

    raise ImageError(f"Together не отдал кадр за {TOGETHER_ATTEMPTS} попытки — {last}")


def _pause(attempt: int) -> None:
    """Растущая пауза: 5, 10, 20 секунд."""
    if POLLINATIONS_BACKOFF_SEC > 0:
        time.sleep(POLLINATIONS_BACKOFF_SEC * (2 ** (attempt - 1)))


def _via_fal(cfg: Config, prompt: str, out_path: Path) -> float:
    """Платная генерация кадра через fal.ai."""
    os.environ.setdefault("FAL_KEY", cfg.fal_key)
    import fal_client

    try:
        result = call_with_timeout(
            fal_client.subscribe,
            cfg.fal_image_model,
            arguments={
                "prompt": prompt,
                "image_size": {"width": 1080, "height": 1920},
                "num_images": 1,
                "enable_safety_checker": True,
            },
            timeout=TIMEOUT_SEC,
            label="fal.image",
        )
    except CallTimeout as e:
        raise ImageError(str(e)) from e
    except Exception as e:  # fal wraps HTTP errors in its own exceptions
        raise ImageError(f"fal.ai image generation failed: {e}") from e

    images = result.get("images") or []
    if not images:
        raise ImageError(
            "fal.ai вернул пустой результат — возможно, промпт отклонён фильтром безопасности"
        )

    url = images[0]["url"]
    with httpx.Client(timeout=120) as client:
        resp = client.get(url)
        resp.raise_for_status()
    out_path.write_bytes(resp.content)
    return COSTS["fal_image_per_call"]
