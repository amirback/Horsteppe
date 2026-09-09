"""Шаг 1: тема -> сценарий, разбитый на сцены.

Провайдер выбирается настройкой LLM_PROVIDER: `openrouter` или `anthropic`.
Оба пути требуют строгий JSON по схеме — разбирать свободный текст регулярками
нельзя, это источник тихих поломок.

SCRIPT_MODE=mock обходит модель целиком и собирает сценарий шаблоном: так
проверяется остальной конвейер (озвучка, кадры, монтаж) за ноль денег.
"""
from __future__ import annotations

import json
import logging

import httpx

from config import COSTS, Config

log = logging.getLogger("worker.script")

# Structured-outputs schema: guarantees parseable JSON (no regex extraction).
SCENES_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "narration": {
                        "type": "string",
                        "description": "Voice-over text for this scene, in the language of the topic",
                    },
                    "image_prompt": {
                        "type": "string",
                        "description": "English text-to-image prompt for this scene, vertical 9:16 composition",
                    },
                },
                "required": ["narration", "image_prompt"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "scenes"],
    "additionalProperties": False,
}


class ScriptRefusedError(Exception):
    """The topic was declined by content moderation."""


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT = 120


def _scene_count(duration_sec: int) -> int:
    return max(3, min(5, round(duration_sec / 7)))


def _mock_script(topic: str, style: str, duration_sec: int) -> dict:
    """Zero-cost template script — no LLM call. For testing the pipeline
    without an Anthropic API key. Narration is generic filler, not a real
    story — swap SCRIPT_MODE back to 'llm' for actual content."""
    n = _scene_count(duration_sec)
    # Keep narration short: TTS bills per character, and free tiers are tiny.
    short_topic = topic.strip()
    if len(short_topic) > 80:
        short_topic = short_topic[:80].rsplit(" ", 1)[0] + "…"
    beats = ["Вступление", "Развитие", "Поворот", "Кульминация", "Финал"][:n]
    scenes = [
        {
            "narration": f"{beats[i]}. Тестовая озвучка сцены {i + 1} из {n} по теме: {short_topic}.",
            "image_prompt": f"{style} style photo illustrating '{short_topic}', scene {i + 1} of {n}, "
            f"vertical 9:16 composition, no text, no logos, no captions",
        }
        for i in range(n)
    ]
    return {"title": topic, "scenes": scenes, "cost_usd": 0.0}


def generate_script(cfg: Config, topic: str, style: str, duration_sec: int) -> dict:
    """Returns {"title": str, "scenes": [{"narration", "image_prompt"}, ...], "cost_usd": float}."""
    if cfg.effective_script_mode == "mock":
        log.info("script: SCRIPT_MODE=mock — skipping Claude, using template scenes")
        return _mock_script(topic, style, duration_sec)

    n = _scene_count(duration_sec)
    words_per_scene = round(duration_sec / n * 2.3)  # ~2.3 words/sec of narration

    prompt = f"""You are a short-form video scriptwriter for vertical (9:16) social videos.

Write a script for a {duration_sec}-second video.

Topic: {topic}
Visual style: {style}

Requirements:
- Exactly {n} scenes.
- Each scene's narration is about {words_per_scene} words (spoken aloud it must fit ~{duration_sec // n} seconds). Write narration in the SAME language as the topic.
- The narration must flow as one continuous story across scenes: a hook in scene 1, development, and a punchy ending.
- Each image_prompt is in ENGLISH, describes a single striking {style} shot for that scene, mentions vertical 9:16 composition, and contains NO text/captions/logos in the image.
- No emojis, no hashtags, no scene numbers inside narration."""

    if cfg.llm_provider == "openrouter":
        data, cost = _via_openrouter(cfg, prompt)
    else:
        data, cost = _via_anthropic(cfg, prompt)

    scenes = _validate(data, n)
    log.info("script: %d сцен, провайдер %s, стоимость $%.4f", len(scenes), cfg.llm_provider, cost)
    return {"title": data.get("title", topic), "scenes": scenes, "cost_usd": cost}


def _validate(data: dict, expected: int) -> list[dict]:
    """Модель могла вернуть синтаксически верный, но бессмысленный ответ."""
    scenes = data.get("scenes") or []
    if not (2 <= len(scenes) <= 8):
        raise RuntimeError(f"модель вернула {len(scenes)} сцен, ожидалось около {expected}")
    for s in scenes:
        if not (s.get("narration") or "").strip() or not (s.get("image_prompt") or "").strip():
            raise RuntimeError("модель вернула пустое поле сцены")
    return scenes


def _via_openrouter(cfg: Config, prompt: str) -> tuple[dict, float]:
    """Сценарий через OpenRouter (совместим с OpenAI Chat Completions).

    `usage.include` просит вернуть реальную стоимость запроса — она точнее
    любой оценки по токенам, потому что цены у моделей разные и меняются.
    """
    payload = {
        "model": cfg.openrouter_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "scenes", "strict": True, "schema": SCENES_SCHEMA},
        },
        "usage": {"include": True},
    }
    headers = {
        "Authorization": f"Bearer {cfg.openrouter_api_key}",
        "Content-Type": "application/json",
        # OpenRouter просит эти заголовки для атрибуции трафика.
        "HTTP-Referer": "https://horsteppe.vercel.app",
        "X-Title": "Horsteppe",
    }

    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        resp = client.post(OPENROUTER_URL, json=payload, headers=headers)

    if resp.status_code == 401:
        raise RuntimeError("OpenRouter: неверный ключ")
    if resp.status_code == 402:
        raise RuntimeError("OpenRouter: закончились средства на счёте")
    if resp.status_code == 429:
        raise RuntimeError("OpenRouter: слишком много запросов, попробуйте позже")
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter вернул {resp.status_code}: {resp.text[:400]}")

    body = resp.json()
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter вернул ответ без вариантов")

    message = choices[0].get("message") or {}
    if message.get("refusal"):
        raise ScriptRefusedError("Тема отклонена модерацией. Переформулируйте запрос.")
    if choices[0].get("finish_reason") == "length":
        raise RuntimeError("Сценарий не поместился в лимит токенов — повторите")

    content = (message.get("content") or "").strip()
    if not content:
        # Часть моделей возвращает рассуждения без итогового ответа —
        # это уже ломало конвейер раньше, поэтому проверка явная.
        raise RuntimeError("OpenRouter вернул пустой ответ модели")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"OpenRouter вернул не JSON: {content[:200]}") from e

    usage = body.get("usage") or {}
    cost = usage.get("cost")
    if cost is None:
        cost = COSTS["openrouter_fallback_per_call"]
        log.warning("OpenRouter не вернул стоимость, записана оценка")
    return data, float(cost)


def _via_anthropic(cfg: Config, prompt: str) -> tuple[dict, float]:
    """Сценарий через Anthropic напрямую."""
    # Импорт здесь, а не наверху: в безопасном режиме этот код не выполняется,
    # и воркер должен запускаться без пакета anthropic — как и без fal_client.
    import anthropic

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key, timeout=REQUEST_TIMEOUT)
    response = client.messages.create(
        model=cfg.llm_model,
        max_tokens=4000,
        output_config={"format": {"type": "json_schema", "schema": SCENES_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )

    if response.stop_reason == "refusal":
        raise ScriptRefusedError("Тема отклонена модерацией контента. Переформулируйте запрос.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Сценарий не поместился в лимит токенов — повторите")

    text = next(b.text for b in response.content if b.type == "text")
    usage = response.usage
    cost = (
        usage.input_tokens / 1_000_000 * COSTS["anthropic_input_per_mtok"]
        + usage.output_tokens / 1_000_000 * COSTS["anthropic_output_per_mtok"]
    )
    return json.loads(text), cost
