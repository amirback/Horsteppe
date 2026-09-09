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

    # Кто пишет сценарий. Провайдер выбирается настройкой, а не правкой кода:
    # ТЗ требует независимости от конкретного поставщика модели.
    llm_provider: str = field(
        default_factory=lambda: os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()
    )
    openrouter_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENROUTER_API_KEY", "").strip()
    )
    openrouter_model: str = field(
        default_factory=lambda: os.environ.get("OPENROUTER_MODEL", "openai/gpt-5.4-mini")
    )

    # Пустое значение допустимо: в безопасном режиме озвучка заменяется
    # тишиной нужной длины и ключ не используется. Проверка — в __post_init__.
    elevenlabs_api_key: str = field(
        default_factory=lambda: os.environ.get("ELEVENLABS_API_KEY", "").strip()
    )
    elevenlabs_voice_id: str = field(
        default_factory=lambda: os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
    )
    elevenlabs_tts_model: str = field(
        default_factory=lambda: os.environ.get("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")
    )

    # То же самое: в безопасном режиме кадры рисует FFmpeg, ключ не нужен.
    fal_key: str = field(default_factory=lambda: os.environ.get("FAL_KEY", "").strip())
    fal_image_model: str = field(
        default_factory=lambda: os.environ.get("FAL_IMAGE_MODEL", "fal-ai/flux/schnell")
    )
    fal_video_model: str = field(
        default_factory=lambda: os.environ.get(
            "FAL_VIDEO_MODEL", "fal-ai/kling-video/v2.1/standard/image-to-video"
        )
    )

    # Единственный выключатель денег. Включён по умолчанию: платный путь
    # требует явного MVP_SAFE_MODE=0. Пустое значение тоже считается
    # безопасным — ошибка в .env не должна открывать кошелёк.
    mvp_safe_mode: bool = field(
        default_factory=lambda: os.environ.get("MVP_SAFE_MODE", "1").strip().lower()
        not in ("0", "false", "no", "off")
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

    @property
    def active_llm_model(self) -> str:
        """Модель, которая реально используется. Раньше лог всегда писал
        LLM_MODEL, даже когда сценарий шёл через OpenRouter, — и в логе стояла
        одна модель, а платили за другую."""
        return self.openrouter_model if self.llm_provider == "openrouter" else self.llm_model

    @property
    def effective_video_mode(self) -> str:
        """В безопасном режиме премиум-видео недоступно, чем бы ни был VIDEO_MODE."""
        return "kenburns" if self.mvp_safe_mode else self.video_mode

    @property
    def effective_script_mode(self) -> str:
        """Обращение к LLM тоже платное, поэтому в безопасном режиме — шаблон."""
        return "mock" if self.mvp_safe_mode else self.script_mode

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
        if self.llm_provider not in ("anthropic", "openrouter"):
            raise RuntimeError(
                f"LLM_PROVIDER must be 'anthropic' or 'openrouter', got {self.llm_provider!r}"
            )
        if self.effective_script_mode == "llm":
            needed, name = (
                (self.openrouter_api_key, "OPENROUTER_API_KEY")
                if self.llm_provider == "openrouter"
                else (self.anthropic_api_key, "ANTHROPIC_API_KEY")
            )
            if not needed:
                raise RuntimeError(
                    f"{name} требуется при SCRIPT_MODE=llm и LLM_PROVIDER={self.llm_provider}. "
                    "Поставьте SCRIPT_MODE=mock, чтобы работать без ключа."
                )
        # Ключи провайдеров обязательны только тогда, когда деньги разрешены.
        # Требовать их всегда — значит запрещать запуск в безопасном режиме,
        # который и существует ради проверки конвейера до появления ключей.
        if not self.mvp_safe_mode:
            missing = [
                name
                for name, value in (
                    ("ELEVENLABS_API_KEY", self.elevenlabs_api_key),
                    ("FAL_KEY", self.fal_key),
                )
                if not value
            ]
            if missing:
                raise RuntimeError(
                    f"{', '.join(missing)} требуются при MVP_SAFE_MODE=0. "
                    "Верните MVP_SAFE_MODE=1, чтобы работать на бесплатных заменителях."
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
    # Запасная оценка, если OpenRouter не вернул реальную стоимость запроса.
    "openrouter_fallback_per_call": float(os.environ.get("COST_OPENROUTER_CALL", "0.002")),
}
