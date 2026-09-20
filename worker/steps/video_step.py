"""Шаг 4: кадр → короткий клип настоящей видео-модели.

Провайдеры перечисляются в VIDEO_PROVIDER через запятую и пробуются по
очереди — так же, как у картинок. Один провайдер это одна точка отказа, и
она уже сработала: аккаунт fal заблокировали за исчерпанный баланс, и весь
платный путь встал, хотя клип мог сделать кто-то другой.

* `higgsfield` — тот самый сервис, по которому равняется продукт. Kling 2.5
  Turbo Pro напрямую у источника; схема полей взята из его openapi.json, а не
  угадана. Единственный из трёх, кто отличает отказ по содержанию от сбоя.
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
from dataclasses import dataclass
from pathlib import Path

import httpx

import quality_debug
import safe_mode
from config import COSTS, Config

from ._timeout import CallTimeout, call_with_timeout

log = logging.getLogger("worker.video")

# Клип из кадра генерируется минутами, а не секундами: запас больше, чем
# у изображения, но он всё равно конечен.
TIMEOUT_SEC = float(os.environ.get("FAL_VIDEO_TIMEOUT_SEC", "600"))


class VideoError(Exception):
    pass


@dataclass(frozen=True)
class ClipResult:
    """Кто на самом деле сделал клип и во что он обошёлся.

    Раньше шаг возвращал одну цифру — стоимость, — и конвейер записывал в
    кадр то, что предложил маршрутизатор. Но маршрутизатор знает только
    модели fal, а цепочка отдаёт кадр первому доступному провайдеру. В базе
    оставалась ложь: «fal, kling v2.1 pro», хотя клип сделал Higgsfield
    моделью v2.5-turbo. Метаданные, по которым считают деньги и выбирают
    модель, обязаны говорить правду о том, что произошло.
    """

    provider: str
    model: str
    cost_usd: float


def _chain_for(cfg: Config, provider: str | None) -> list[str]:
    """Порядок обхода провайдеров с учётом выбора маршрутизатора.

    Выбранный идёт первым, остальные остаются запасом в прежнем порядке.
    Раньше выбор маршрутизатора на порядок не влиял вовсе: кадр всегда
    доставался первому в настройке, а имя выбранной модели просто терялось.

    Провайдер, которого нет в настройке, игнорируется молча — настройка
    остаётся главнее подсказки.
    """
    chain = list(cfg.video_providers)
    if provider and provider in chain:
        chain.remove(provider)
        chain.insert(0, provider)
    return chain


def generate_clip(
    cfg: Config, image_public_url: str, motion_prompt: str, out_path: Path,
    model: str | None = None, cost_usd: float | None = None,
    provider: str | None = None,
) -> ClipResult:
    """Animate an image into a ~5s clip. `image_public_url` must be publicly
    reachable (we pass the Supabase Storage public URL). Returns cost in USD.

    `provider`, `model` и `cost_usd` приходят от маршрутизатора: на важный
    кадр он берёт модель посильнее, на фоновый — подешевле. Без них шаг
    работает как раньше, по настройке из окружения.
    """
    # Защита в глубину: конвейер и так не зовёт этот шаг в безопасном режиме.
    # Оценка передаётся до вызова — потолок проекта обязан успеть отказать,
    # пока деньги ещё не потрачены.
    price = COSTS["fal_video_per_clip"] if cost_usd is None else float(cost_usd)
    safe_mode.require_paid(cfg, "генерация видео", price)

    chain = _chain_for(cfg, provider)
    # Имя модели осмысленно только для того провайдера, который её и
    # предложил. Отдавать `kling-video/v2.5-turbo` в fal или наоборот — верный
    # способ получить отказ за деньги, поэтому запасным провайдерам модель
    # не передаётся: они берут свою из настройки.
    # Кому адресована подсказка о модели. Маршрутизатор называет провайдера
    # явно; у старых вызовов его нет, и там `model` всегда означал модель
    # fal — это значение сохраняется, чтобы не сломать их молча.
    addressed_to = provider or "fal"
    errors: list[str] = []
    for position, current in enumerate(chain, start=1):
        hint = model if current == addressed_to else None
        try:
            if current == "higgsfield":
                return _via_higgsfield(cfg, image_public_url, motion_prompt, out_path, hint)
            if current == "replicate":
                return _via_replicate(cfg, image_public_url, motion_prompt, out_path)
            return _via_fal(cfg, image_public_url, motion_prompt, out_path, hint, price)
        except ContentRejected:
            # Отклонение по содержанию — приговор для всей цепочки. Что
            # отвергла одна модель, отвергнет и соседняя, а вызов к ней
            # будет стоить денег.
            raise
        except VideoError as e:
            errors.append(f"{current}: {e}")
            if position < len(chain):
                log.warning("%s не сделал клип, пробую следующего: %s", current, e)
            continue
    raise VideoError("Клип не удалось получить ни у одного провайдера. " + " | ".join(errors))


def _via_fal(
    cfg: Config, image_public_url: str, motion_prompt: str, out_path: Path,
    model: str | None, price: float,
) -> ClipResult:
    os.environ.setdefault("FAL_KEY", cfg.fal_key)
    import fal_client

    arguments = {
        "image_url": image_public_url,
        "prompt": motion_prompt,
        "duration": "5",
    }
    try:
        result = call_with_timeout(
            fal_client.subscribe,
            model or cfg.fal_video_model,
            arguments=arguments,
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
    chosen = model or cfg.fal_video_model
    quality_debug.record_clip(out_path.stem, "fal", chosen, arguments, out_path)
    return ClipResult("fal", chosen, price)


# --------------------------------------------------------------- replicate --

REPLICATE_URL = "https://api.replicate.com/v1/models/{model}/predictions"
# Клип генерируется минутами. Держать соединение открытым всё это время
# нельзя, поэтому ответ ждём опросом, а не одним длинным запросом.
REPLICATE_POLL_SEC = float(os.environ.get("REPLICATE_POLL_SEC", "5"))
REPLICATE_TIMEOUT_SEC = float(os.environ.get("REPLICATE_TIMEOUT_SEC", "900"))


def _via_replicate(cfg: Config, image_public_url: str, motion_prompt: str, out_path: Path) -> ClipResult:
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
    quality_debug.record_clip(out_path.stem, "replicate", cfg.replicate_video_model, payload, out_path)
    return ClipResult("replicate", cfg.replicate_video_model, COSTS["replicate_video_per_clip"])


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


# ------------------------------------------------------------- higgsfield --

HIGGSFIELD_BASE = os.environ.get("HIGGSFIELD_BASE_URL", "https://api.higgsfield.ai").rstrip("/")
HIGGSFIELD_POLL_SEC = float(os.environ.get("HIGGSFIELD_POLL_SEC", "5"))
HIGGSFIELD_TIMEOUT_SEC = float(os.environ.get("HIGGSFIELD_TIMEOUT_SEC", "900"))
# Коды, на которых повтор осмыслен: перегрузка и временные сбои. Взято из
# стратегии повторов их же SDK — она сама так и настроена.
HIGGSFIELD_RETRY_CODES = {408, 429, 500, 502, 503, 504}
HIGGSFIELD_ATTEMPTS = 3
# Длительность клипа. У Kling допустимы 5 и 10 секунд, у Hailuo — 6 и 10;
# пять берём потому, что монтаж всё равно режет клип под длину кадра.
HIGGSFIELD_DURATION = int(os.environ.get("HIGGSFIELD_DURATION_SEC", "5"))

# Насколько строго модель держится промпта: 0…1, у них по умолчанию 0.5.
# Значение не меняем без замера — их документированное умолчание это
# компромисс между послушанием и естественностью движения, и «покрутить
# вверх» наугад скорее сделает картинку деревянной.
HIGGSFIELD_CFG_SCALE = float(os.environ.get("HIGGSFIELD_CFG_SCALE", "0.5"))

# Список того, чего в рекламном кадре быть не должно. Поле `negative_prompt`
# у Kling есть, и до сих пор мы его не использовали вовсе — отправляли
# пустую строку по умолчанию.
#
# Сюда попали только те дефекты, которые мы действительно видели на своих
# роликах: плывущая форма товара, выдуманные надписи на упаковке (модель не
# умеет писать буквы) и чужой водяной знак, который приходилось срезать
# кадрированием. Выдумывать список «на всякий случай» смысла нет: каждый
# лишний запрет отъедает у модели внимание.
HIGGSFIELD_NEGATIVE = os.environ.get(
    "HIGGSFIELD_NEGATIVE_PROMPT",
    "warped product shape, morphing logo, distorted packaging, "
    "garbled text, misspelled letters, watermark, subtitles, "
    "extra fingers, deformed hands",
)


class ContentRejected(VideoError):
    """Кадр отклонён по содержанию.

    Отдельный класс нужен, чтобы цепочка НЕ шла к следующему провайдеру:
    отклонённое одной моделью отклонит и соседняя, а вызов будет стоить
    денег. У Higgsfield это отдельный терминальный статус `nsfw`, а не
    ошибка сети — мы это различие сохраняем.
    """


# Терминальные статусы отказа по содержанию. `nsfw` объявлен в их openapi,
# `ip_detected` встречается в их же руководстве по разбору сбоев — принимаем
# оба, чтобы новый повод для отказа не притворился сбоем сети.
CONTENT_STATUSES = {"nsfw", "ip_detected"}


def _json_or_fail(response, what: str) -> dict:
    """Разобрать ответ, не уронив проект на странице капчи.

    Защита от анти-бота: их руководство прямо описывает случай, когда вместо
    JSON приходит HTML с проверкой. Без этой обёртки разбор падал бы
    исключением мимо цепочки провайдеров — то есть кадр терялся бы там, где
    сосед мог справиться.
    """
    try:
        return response.json()
    except ValueError as e:
        body = (response.text or "")[:200].replace("\n", " ")
        raise VideoError(f"Higgsfield вернул не JSON на {what}: {body}") from e


def _higgsfield_headers(cfg: Config) -> dict:
    return {
        "Authorization": f"Key {cfg.higgsfield_credential}",
        "Content-Type": "application/json",
    }


def _via_higgsfield(
    cfg: Config, image_public_url: str, motion_prompt: str, out_path: Path,
    model: str | None = None,
) -> ClipResult:
    """Клип через собственный API Higgsfield.

    Схема запроса взята из их openapi.json, а не угадана: обязательны
    `prompt` и `image_url`, длительность выбирается из фиксированного набора.
    Запрос асинхронный — ответ забирается опросом по выданному адресу.

    Промпт сюда приходит уже как описание движения: их же руководство по
    промптам требует не пересказывать кадр, который модель и так видит.
    """
    import time

    if not cfg.higgsfield_credential:
        raise VideoError("HF_KEY (или HF_API_KEY и HF_API_SECRET) не задан")

    # Модель приходит от маршрутизатора: крючку достаётся pro, фону —
    # standard. Настройка из окружения остаётся запасным вариантом, а не
    # единственным, как было раньше.
    model = (model or cfg.higgsfield_video_model).strip("/")
    payload = {
        "prompt": motion_prompt,
        "image_url": image_public_url,
        "duration": HIGGSFIELD_DURATION,
        "cfg_scale": HIGGSFIELD_CFG_SCALE,
    }
    if HIGGSFIELD_NEGATIVE.strip():
        payload["negative_prompt"] = HIGGSFIELD_NEGATIVE.strip()
    headers = _higgsfield_headers(cfg)

    try:
        with httpx.Client(timeout=120) as client:
            started = _higgsfield_submit(client, f"{HIGGSFIELD_BASE}/{model}", headers, payload)
            deadline = time.monotonic() + HIGGSFIELD_TIMEOUT_SEC
            status_url = started.get("status_url") or f"{HIGGSFIELD_BASE}/requests/{started['request_id']}/status"

            state = started.get("status") or "queued"
            data = started
            while state in ("queued", "in_progress"):
                if time.monotonic() > deadline:
                    _higgsfield_cancel(client, headers, started)
                    raise VideoError(f"Higgsfield не отдал клип за {HIGGSFIELD_TIMEOUT_SEC:.0f} с")
                time.sleep(HIGGSFIELD_POLL_SEC)
                data = _json_or_fail(client.get(status_url, headers=headers), "опросе статуса")
                state = data.get("status") or "in_progress"

            if state in CONTENT_STATUSES:
                raise ContentRejected(f"Higgsfield отклонил кадр по содержанию ({state})")
            if state != "completed":
                raise VideoError(f"Higgsfield: {state} — {str(data.get('error'))[:300]}")

            url = (data.get("video") or {}).get("url")
            if not url:
                raise VideoError("Higgsfield вернул готовый ответ без ссылки на видео")

            clip = client.get(url, timeout=300)
            clip.raise_for_status()
    except ContentRejected:
        raise
    except httpx.HTTPError as e:
        raise VideoError(f"Higgsfield: сеть — {e}") from e

    out_path.write_bytes(clip.content)
    quality_debug.record_clip(out_path.stem, "higgsfield", model, payload, out_path)
    return ClipResult("higgsfield", model, COSTS["higgsfield_video_per_clip"])


def _higgsfield_submit(client, url: str, headers: dict, payload: dict) -> dict:
    """Постановка задачи с повторами на перегрузке.

    Раньше единственный отказ 429 ронял кадр целиком. Пауза растёт, чтобы
    повтор не добавлял нагрузки тому, кто уже ей захлёбывается.
    """
    import time

    last = ""
    for attempt in range(1, HIGGSFIELD_ATTEMPTS + 1):
        response = client.post(url, headers=headers, json=payload)
        if response.status_code < 400:
            return _json_or_fail(response, "постановке задачи")
        last = f"HTTP {response.status_code}: {response.text[:300]}"
        if response.status_code not in HIGGSFIELD_RETRY_CODES or attempt == HIGGSFIELD_ATTEMPTS:
            raise VideoError(f"Higgsfield отказал — {last}")
        time.sleep(2 ** attempt)
    raise VideoError(f"Higgsfield отказал — {last}")


def _higgsfield_cancel(client, headers: dict, started: dict) -> None:
    """Снять задачу, которую мы перестали ждать.

    Брошенный запрос продолжает считаться и тратить кредиты. Отмена не
    обязана сработать — начатую генерацию остановить нельзя, — поэтому её
    неудача не должна подменять собой исходную ошибку таймаута.
    """
    url = started.get("cancel_url")
    if not url:
        return
    try:
        client.post(url, headers=headers, timeout=20)
        log.info("Higgsfield: задача %s снята по таймауту", started.get("request_id"))
    except Exception as e:  # noqa: BLE001 — отмена не важнее причины отказа
        log.warning("Higgsfield: снять задачу не удалось: %s", e)
