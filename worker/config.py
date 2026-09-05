"""Worker configuration loaded from environment (.env supported)."""
import os
import socket
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

WORKER_DIR = Path(__file__).parent
TMP_DIR = WORKER_DIR / "tmp"


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name} (see worker/.env.example)")
    return value


@dataclass(frozen=True)
class Config:
    supabase_url: str = field(default_factory=lambda: _require("SUPABASE_URL"))
    supabase_service_key: str = field(default_factory=lambda: _require("SUPABASE_SERVICE_ROLE_KEY"))

    # Empty string allowed here — validated in __post_init__ only when actually needed
    # (SCRIPT_MODE=mock doesn't call Anthropic at all, so no key required).
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "").strip())
    llm_model: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "claude-opus-5"))
    script_mode: str = field(default_factory=lambda: os.environ.get("SCRIPT_MODE", "llm"))

    elevenlabs_api_key: str = field(default_factory=lambda: _require("ELEVENLABS_API_KEY"))
    elevenlabs_voice_id: str = field(
        default_factory=lambda: os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
    )
    elevenlabs_tts_model: str = field(
        default_factory=lambda: os.environ.get("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")
    )

    fal_key: str = field(default_factory=lambda: _require("FAL_KEY"))
    fal_image_model: str = field(
        default_factory=lambda: os.environ.get("FAL_IMAGE_MODEL", "fal-ai/flux/schnell")
    )
    fal_video_model: str = field(
        default_factory=lambda: os.environ.get(
            "FAL_VIDEO_MODEL", "fal-ai/kling-video/v2.1/standard/image-to-video"
        )
    )

    video_mode: str = field(default_factory=lambda: os.environ.get("VIDEO_MODE", "kenburns"))

    # Формат кадра по умолчанию, если проект его не задал.
    video_format: str = field(default_factory=lambda: os.environ.get("VIDEO_FORMAT", "9:16"))
    # Длительность перехода между сценами, секунды. 0 — жёсткие склейки.
    transition_sec: float = field(
        default_factory=lambda: float(os.environ.get("TRANSITION_SEC", "0.5"))
    )
    subtitles: bool = field(
        default_factory=lambda: os.environ.get("SUBTITLES", "1").strip() not in ("0", "false", "")
    )
    music_file: str = field(default_factory=lambda: os.environ.get("MUSIC_FILE", "").strip())

    poll_interval_sec: float = field(
        default_factory=lambda: float(os.environ.get("POLL_INTERVAL_SEC", "3"))
    )
    worker_id: str = field(
        default_factory=lambda: os.environ.get("WORKER_ID")
        or f"{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
    )

    def __post_init__(self) -> None:
        if self.video_format not in ("9:16", "16:9", "1:1", "4:5"):
            raise RuntimeError(
                f"VIDEO_FORMAT must be one of 9:16 / 16:9 / 1:1 / 4:5, got {self.video_format!r}"
            )
        if not 0 <= self.transition_sec <= 2:
            raise RuntimeError(f"TRANSITION_SEC must be between 0 and 2, got {self.transition_sec}")
        if self.video_mode not in ("kenburns", "provider"):
            raise RuntimeError(f"VIDEO_MODE must be 'kenburns' or 'provider', got {self.video_mode!r}")
        if self.script_mode not in ("llm", "mock"):
            raise RuntimeError(f"SCRIPT_MODE must be 'llm' or 'mock', got {self.script_mode!r}")
        if self.script_mode == "llm" and not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required when SCRIPT_MODE=llm. "
                "Set SCRIPT_MODE=mock in worker/.env to test without an Anthropic key."
            )
        if self.music_file and not Path(self.music_file).exists():
            raise RuntimeError(f"MUSIC_FILE points to a missing file: {self.music_file}")


# Approximate provider prices for cost logging (USD). Override via env if needed.
COSTS = {
    # Claude Opus 5: $5/M input, $25/M output — logged from real usage in script_step
    "anthropic_input_per_mtok": float(os.environ.get("COST_ANTHROPIC_INPUT_MTOK", "5.0")),
    "anthropic_output_per_mtok": float(os.environ.get("COST_ANTHROPIC_OUTPUT_MTOK", "25.0")),
    # ElevenLabs multilingual v2 ~ $0.18 per 1000 chars (creator tier, approx)
    "elevenlabs_per_1k_chars": float(os.environ.get("COST_ELEVENLABS_1K_CHARS", "0.18")),
    # Flux schnell on fal ~ $0.003 per megapixel; 1080x1920 ~ 2MP
    "fal_image_per_call": float(os.environ.get("COST_FAL_IMAGE", "0.006")),
    # Kling standard 5s clip on fal, approx
    "fal_video_per_clip": float(os.environ.get("COST_FAL_VIDEO_CLIP", "0.35")),
}
