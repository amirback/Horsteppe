"""Step 4 (provider mode): image -> short video clip via fal.ai (Kling et al.).

In VIDEO_MODE=kenburns this step is skipped entirely — render_step animates
the still image with ffmpeg instead, which costs nothing. Switch to
VIDEO_MODE=provider only when the pipeline is fully debugged.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

from config import COSTS, Config

from ._timeout import CallTimeout, call_with_timeout

log = logging.getLogger("worker.video")

# Клип из кадра генерируется минутами, а не секундами: запас больше, чем
# у изображения, но он всё равно конечен.
TIMEOUT_SEC = float(os.environ.get("FAL_VIDEO_TIMEOUT_SEC", "600"))


class VideoError(Exception):
    pass


def generate_clip(cfg: Config, image_public_url: str, motion_prompt: str, out_path: Path) -> float:
    """Animate an image into a ~5s clip. `image_public_url` must be publicly
    reachable (we pass the Supabase Storage public URL). Returns cost in USD."""
    os.environ.setdefault("FAL_KEY", cfg.fal_key)
    import fal_client

    try:
        result = call_with_timeout(
            fal_client.subscribe,
            cfg.fal_video_model,
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
    return COSTS["fal_video_per_clip"]
