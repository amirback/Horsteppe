"""Step 3: per-scene image via fal.ai (Flux), vertical 9:16."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

from config import COSTS, Config

log = logging.getLogger("worker.image")


class ImageError(Exception):
    pass


def generate_image(cfg: Config, prompt: str, out_path: Path) -> float:
    """Generate a 1080x1920 image for `prompt`, save to out_path.
    Returns estimated cost in USD."""
    os.environ.setdefault("FAL_KEY", cfg.fal_key)
    import fal_client

    try:
        result = fal_client.subscribe(
            cfg.fal_image_model,
            arguments={
                "prompt": prompt,
                "image_size": {"width": 1080, "height": 1920},
                "num_images": 1,
                "enable_safety_checker": True,
            },
        )
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
