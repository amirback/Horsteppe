"""Шаг 4: кадр → короткий клип настоящей видео-модели.

Провайдеры перечисляются в VIDEO_PROVIDER через запятую и пробуются по
очереди — так же, как у картинок. Один провайдер это одна точка отказа, и
она уже сработала: аккаунт fal заблокировали за исчерпанный баланс, и весь
платный путь встал, хотя клип мог сделать кто-то другой.

* `fal` — Kling и соседи. Дешевле за секунду, но требует предоплаты, и
  минимальный платёж там $10.
* `replicate` — оплата по факту в конце месяца, предоплаты нет. Дороже за
  секунду, зато пускает потратить полтора доллара, а не десять.

В VIDEO_MODE=kenburns шаг не вызывается вовсе: движение по кадру рисует
FFmpeg, и это не стоит ничего.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

import safe_mode
from config import COSTS, Config

from ._timeout import CallTimeout, call_with_timeout

log = logging.getLogger("worker.video")

# Клип из кадра генерируется минутами, а не секундами: запас больше, чем
# у изображения, но он всё равно конечен.
TIMEOUT_SEC = float(os.environ.get("FAL_VIDEO_TIMEOUT_SEC", "600"))


class VideoError(Exception):
    pass


def generate_clip(
    cfg: Config, image_public_url: str, motion_prompt: str, out_path: Path,
    model: str | None = None, cost_usd: float | None = None,
) -> float:
    """Animate an image into a ~5s clip. `image_public_url` must be publicly
    reachable (we pass the Supabase Storage public URL). Returns cost in USD.

    `model` и `cost_usd` приходят от маршрутизатора: на важный кадр он берёт
    модель посильнее, на фоновый — подешевле. Без них шаг работает как раньше,
    по настройке из окружения.
    """
    # Защита в глубину: конвейер и так не зовёт этот шаг в безопасном режиме.
    # Оценка передаётся до вызова — потолок проекта обязан успеть отказать,
    # пока деньги ещё не потрачены.
    price = COSTS["fal_video_per_clip"] if cost_usd is None else float(cost_usd)
    safe_mode.require_paid(cfg, "генерация видео", price)

    chain = cfg.video_providers
    errors: list[str] = []
    for position, provider in enumerate(chain, start=1):
        try:
            if provider == "replicate":
                return _via_replicate(cfg, image_public_url, motion_prompt, out_path)
            return _via_fal(cfg, image_public_url, motion_prompt, out_path, model, price)
        except VideoError as e:
            errors.append(f"{provider}: {e}")
            if position < len(chain):
                log.warning("%s не сделал клип, пробую следующего: %s", provider, e)
            continue
    raise VideoError("Клип не удалось получить ни у одного провайдера. " + " | ".join(errors))


def _via_fal(
    cfg: Config, image_public_url: str, motion_prompt: str, out_path: Path,
    model: str | None, price: float,
) -> float:
    os.environ.setdefault("FAL_KEY", cfg.fal_key)
    import fal_client

    try:
        result = call_with_timeout(
            fal_client.subscribe,
            model or cfg.fal_video_model,
            arguments={
                "image_url": image_public_url,
                "prompt": motion_prompt,
                "duration": "5",
            },
            timeout=TIMEOUT_SEC,
            label="fal.video",
        )
    except CallTimeout as e:
        raise VideoError(str(e)) from e
    except Exception as e:
        raise VideoError(f"fal.ai video generation failed: {e}") from e

    video = result.get("video") or {}
    url = video.get("url")
    if not url:
        raise VideoError(
            "fal.ai вернул пустой результат видео — возможно, кадр отклонён фильтром безопасности"
        )

    with httpx.Client(timeout=300) as client:
        resp = client.get(url)
        resp.raise_for_status()
    out_path.write_bytes(resp.content)
    return price


# --------------------------------------------------------------- replicate --

REPLICATE_URL = "https://api.replicate.com/v1/models/{model}/predictions"
# Клип генерируется минутами. Держать соединение открытым всё это время
# нельзя, поэтому ответ ждём опросом, а не одним длинным запросом.
REPLICATE_POLL_SEC = float(os.environ.get("REPLICATE_POLL_SEC", "5"))
REPLICATE_TIMEOUT_SEC = float(os.environ.get("REPLICATE_TIMEOUT_SEC", "900"))


def _via_replicate(cfg: Config, image_public_url: str, motion_prompt: str, out_path: Path) -> float:
    """Клип через Replicate.

    Почему он здесь вообще. У fal минимальный платёж $10, и это оказалось
    непреодолимым: человеку нужно два-три ролика, а не тридцать. Replicate
    выставляет счёт по факту в конце месяца, без предоплаты — потратить
    полтора доллара там можно.

    Набор полей намеренно минимальный: `image` и `prompt` принимают почти все
    модели «кадр → видео», а всё остальное у каждой своё. Дополнения
    задаются через REPLICATE_VIDEO_INPUT одной JSON-строкой, и ошибку
    провайдера мы показываем целиком — по ней сразу видно недостающее поле.
    """
    import json
    import time

    if not cfg.replicate_api_token:
        raise VideoError("REPLICATE_API_TOKEN не задан")

    payload: dict = {"image": image_public_url, "prompt": motion_prompt}
    extra = (os.environ.get("REPLICATE_VIDEO_INPUT") or "").strip()
    if extra:
        try:
            payload.update(json.loads(extra))
        except ValueError as e:
            raise VideoError(f"REPLICATE_VIDEO_INPUT не разбирается как JSON: {e}") from e

    headers = {
        "Authorization": f"Bearer {cfg.replicate_api_token}",
        "Content-Type": "application/json",
    }
    url = REPLICATE_URL.format(model=cfg.replicate_video_model)

    try:
        with httpx.Client(timeout=120) as client:
            started = client.post(url, headers=headers, json={"input": payload})
            if started.status_code >= 400:
                raise VideoError(f"Replicate отказал ({started.status_code}): {started.text[:400]}")
            prediction = started.json()

            deadline = time.monotonic() + REPLICATE_TIMEOUT_SEC
            while prediction.get("status") in ("starting", "processing"):
                if time.monotonic() > deadline:
                    raise VideoError(
                        f"Replicate не отдал клип за {REPLICATE_TIMEOUT_SEC:.0f} с"
                    )
                time.sleep(REPLICATE_POLL_SEC)
                poll = (prediction.get("urls") or {}).get("get")
                if not poll:
                    raise VideoError("Replicate не вернул адрес для опроса")
                prediction = client.get(poll, headers=headers).json()

            if prediction.get("status") != "succeeded":
                raise VideoError(
                    f"Replicate: {prediction.get('status')} — {str(prediction.get('error'))[:300]}"
                )

            video_url = _replicate_output_url(prediction.get("output"))
            if not video_url:
                raise VideoError("Replicate вернул результат без ссылки на видео")

            clip = client.get(video_url, timeout=300)
            clip.raise_for_status()
    except httpx.HTTPError as e:
        raise VideoError(f"Replicate: сеть — {e}") from e

    out_path.write_bytes(clip.content)
    return COSTS["replicate_video_per_clip"]


def _replicate_output_url(output) -> str | None:
    """Ссылка на клип. Модели отдают её то строкой, то списком, то объектом."""
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output:
        return _replicate_output_url(output[-1])
    if isinstance(output, dict):
        for key in ("video", "url", "output"):
            if output.get(key):
                return _replicate_output_url(output[key])
    return None
