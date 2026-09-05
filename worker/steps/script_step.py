"""Step 1: topic -> script broken into scenes, via Claude with structured outputs.

SCRIPT_MODE=mock (config) bypasses Claude entirely with a template generator —
use this to test the rest of the pipeline (TTS/images/render) for $0 before
paying for Anthropic API access.
"""
from __future__ import annotations

import json
import logging

import anthropic

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
    if cfg.script_mode == "mock":
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

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    response = client.messages.create(
        model=cfg.llm_model,
        max_tokens=4000,
        output_config={"format": {"type": "json_schema", "schema": SCENES_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )

    if response.stop_reason == "refusal":
        raise ScriptRefusedError(
            "Тема отклонена модерацией контента. Переформулируйте запрос."
        )
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Script generation hit the token limit — retry")

    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)

    scenes = data.get("scenes") or []
    if not (2 <= len(scenes) <= 8):
        raise RuntimeError(f"LLM returned {len(scenes)} scenes, expected {n}")
    for s in scenes:
        if not s["narration"].strip() or not s["image_prompt"].strip():
            raise RuntimeError("LLM returned an empty scene field")

    usage = response.usage
    cost = (
        usage.input_tokens / 1_000_000 * COSTS["anthropic_input_per_mtok"]
        + usage.output_tokens / 1_000_000 * COSTS["anthropic_output_per_mtok"]
    )
    log.info("script: %d scenes, %d in / %d out tokens", len(scenes), usage.input_tokens, usage.output_tokens)
    return {"title": data.get("title", topic), "scenes": scenes, "cost_usd": cost}
