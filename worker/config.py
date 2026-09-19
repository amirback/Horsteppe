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


# Как называется переменная с ключом у каждого провайдера видео. Нужна,
# чтобы отказ на старте называл человеку конкретное имя, а не «нет ключа».
VIDEO_KEY_NAMES = {
    "higgsfield": "HF_KEY",
    "fal": "FAL_KEY",
    "replicate": "REPLICATE_API_TOKEN",
}


@dataclass(frozen=True)
class Config:
    supabase_url: str = field(default_factory=lambda: _require("SUPABASE_URL"))
    supabase_service_key: str = field(default_factory=lambda: _require("SUPABASE_SERVICE_ROLE_KEY"))

    # Empty string allowed here — validated in __post_init__ only when actually needed
    # (SCRIPT_MODE=mock doesn't call Anthropic at all, so no key required).
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "").strip())
    llm_model: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "claude-opus-5"))
    # Ключ уровня организации не привязан к рабочему пространству, и вызов без
    # этого идентификатора отклоняется с 400. Ключ, созданный внутри рабочего
    # пространства, ничего такого не требует — поле остаётся пустым.
    anthropic_workspace_id: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    )
    script_mode: str = field(default_factory=lambda: os.environ.get("SCRIPT_MODE", "llm"))

    # Кто пишет сценарий. Провайдер выбирается настройкой, а не правкой кода:
    # ТЗ требует независимости от конкретного поставщика модели.
    llm_provider: str = field(
        default_factory=lambda: os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()
    )
    openrouter_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENROUTER_API_KEY", "").strip()
    )
    # Сценарий — лицо продукта: по нему судят, «умный» ролик или нет.
    # Поэтому по умолчанию его пишет Claude Opus 5, в том числе когда доступ
    # идёт через OpenRouter. Дешёвая модель экономит центы и стоит качества.
    openrouter_model: str = field(
        default_factory=lambda: os.environ.get("OPENROUTER_MODEL", "anthropic/claude-opus-5")
    )

    # Цепочка провайдеров сценария, как у кадров: пробуются по очереди.
    # Пусто — порядок выводится из LLM_PROVIDER, чтобы старые .env работали
    # как раньше, но уже с запасным путём.
    script_provider: str = field(
        default_factory=lambda: os.environ.get("SCRIPT_PROVIDER", "").strip().lower()
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
    # Кто рисует кадры. Можно перечислить через запятую: провайдеры
    # пробуются по очереди. Один недоступный поставщик не должен уносить
    # весь проект — этого прямо требует ТЗ.
    image_provider: str = field(
        default_factory=lambda: os.environ.get("IMAGE_PROVIDER", "fal").strip().lower()
    )
    pollinations_model: str = field(
        default_factory=lambda: os.environ.get("POLLINATIONS_MODEL", "flux")
    )
    # Together AI: бесплатный тариф FLUX.1-schnell, но с ключом и, в отличие
    # от Pollinations, со стабильным ответом из дата-центра. Pollinations на
    # боевом размере кадра отвечал то за три секунды, то за тринадцать минут,
    # и именно на нём вставали проекты.
    together_api_key: str = field(
        default_factory=lambda: os.environ.get("TOGETHER_API_KEY", "").strip()
    )
    together_image_model: str = field(
        default_factory=lambda: os.environ.get(
            "TOGETHER_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell-Free"
        )
    )

    fal_image_model: str = field(
        default_factory=lambda: os.environ.get("FAL_IMAGE_MODEL", "fal-ai/flux/schnell")
    )
    # Модель, которая делает настоящее видео из кадра. Это диффузия по
    # времени, а не деформация одной картинки: именно она даёт параллакс
    # фона, движение всего тела и связность между кадрами. Ken Burns не
    # умеет ничего из этого и никогда не научится — там нет новых кадров.
    #
    # Цены проверены на странице провайдера 16.09.2026, за секунду готового
    # видео:
    #   Wan 2.5                $0.05  — дешевле всего
    #   Kling 2.5 Turbo Pro    $0.07  — взята за основу
    #   Veo 3                  $0.40  — впятеро дороже
    # Было `kling-video/v2.1/standard`: та же цена за секунду, но поколением
    # старше и не «pro». Менять на более дешёвую Wan имеет смысл тогда,
    # когда счёт пойдёт на сотни роликов, а не на первые пробы.
    fal_video_model: str = field(
        default_factory=lambda: os.environ.get(
            "FAL_VIDEO_MODEL", "fal-ai/kling-video/v2.5-turbo/pro/image-to-video"
        )
    )

    # Кто делает настоящее видео. Через запятую, пробуются по очереди —
    # как у картинок. Один провайдер это одна точка отказа, и она уже
    # сработала: аккаунт fal заблокировали, и весь платный путь встал.
    video_provider: str = field(
        default_factory=lambda: os.environ.get("VIDEO_PROVIDER", "fal").strip().lower()
    )
    # Replicate берёт дороже за секунду, зато выставляет счёт по факту в конце
    # месяца. У fal минимальный платёж $10 — для двух-трёх пробных роликов это
    # оказалось непреодолимым препятствием.
    replicate_api_token: str = field(
        default_factory=lambda: os.environ.get("REPLICATE_API_TOKEN", "").strip()
    )
    # Higgsfield — тот самый сервис, по которому равняется продукт. У него
    # есть публичный REST API с генерацией видео из кадра, и схема полей
    # известна точно из его openapi.json: гадать, как у соседей, не нужно.
    # Ключ выдаётся парой; SDK читает их из HF_KEY или из HF_API_KEY и
    # HF_API_SECRET — принимаем оба способа.
    higgsfield_api_key: str = field(
        default_factory=lambda: os.environ.get("HF_API_KEY", "").strip()
    )
    higgsfield_api_secret: str = field(
        default_factory=lambda: os.environ.get("HF_API_SECRET", "").strip()
    )
    higgsfield_key: str = field(default_factory=lambda: os.environ.get("HF_KEY", "").strip())
    higgsfield_video_model: str = field(
        default_factory=lambda: os.environ.get(
            "HIGGSFIELD_VIDEO_MODEL", "kling-video/v2.5-turbo/pro/image-to-video"
        )
    )
    replicate_video_model: str = field(
        default_factory=lambda: os.environ.get(
            "REPLICATE_VIDEO_MODEL", "wavespeedai/wan-2.1-i2v-480p"
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
    # Ограничение времени жизни процесса. Нужно там, где воркер запускают по
    # расписанию с жёстким лимитом на длительность задания: он обязан выйти
    # сам и чисто, а не быть убитым посреди сборки. 0 — работать бесконечно.
    max_runtime_sec: float = field(
        default_factory=lambda: float(os.environ.get("WORKER_MAX_RUNTIME_SEC", "0"))
    )
    worker_id: str = field(
        default_factory=lambda: os.environ.get("WORKER_ID")
        or f"{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
    )

    @property
    def image_providers(self) -> list[str]:
        """Цепочка провайдеров кадров в порядке приоритета."""
        return [x.strip() for x in self.image_provider.split(",") if x.strip()]

    @property
    def video_providers(self) -> list[str]:
        """Цепочка провайдеров видео в порядке приоритета."""
        known = ("higgsfield", "fal", "replicate")
        chain = [x.strip() for x in self.video_provider.split(",") if x.strip() in known]
        return chain or ["fal"]

    def has_video_key(self, provider: str) -> bool:
        """Есть ли чем расплатиться с этим провайдером видео."""
        if provider == "higgsfield":
            return bool(self.higgsfield_credential)
        if provider == "replicate":
            return bool(self.replicate_api_token)
        return bool(self.fal_key)

    @property
    def higgsfield_credential(self) -> str:
        """Ключ в виде `id:secret` — так его ждёт заголовок Authorization."""
        if self.higgsfield_key:
            return self.higgsfield_key
        if self.higgsfield_api_key and self.higgsfield_api_secret:
            return f"{self.higgsfield_api_key}:{self.higgsfield_api_secret}"
        return ""

    @property
    def script_provider_chain(self) -> list[str]:
        """Провайдеры сценария по приоритету.

        Один провайдер — одна точка отказа: OpenRouter уже отвечал 429 и
        пустым ответом, и тогда проект падал целиком. Запасной путь стоит
        ноль, пока основной работает.
        """
        if self.script_provider:
            chain = [x.strip() for x in self.script_provider.split(",") if x.strip()]
        else:
            other = "openrouter" if self.llm_provider == "anthropic" else "anthropic"
            chain = [self.llm_provider, other]
        seen: list[str] = []
        for name in chain:
            if name in ("anthropic", "openrouter") and name not in seen:
                seen.append(name)
        return seen

    def has_script_key(self, provider: str) -> bool:
        return bool(self.openrouter_api_key if provider == "openrouter" else self.anthropic_api_key)

    def script_model(self, provider: str) -> str:
        return self.openrouter_model if provider == "openrouter" else self.llm_model

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
        known = ("fal", "together", "pollinations")
        unknown = [x for x in self.image_providers if x not in known]
        if unknown or not self.image_providers:
            raise RuntimeError(
                f"IMAGE_PROVIDER: неизвестные значения {unknown or '(пусто)'}. "
                f"Допустимы {', '.join(repr(k) for k in known)}, можно через запятую."
            )
        if self.llm_provider not in ("anthropic", "openrouter"):
            raise RuntimeError(
                f"LLM_PROVIDER must be 'anthropic' or 'openrouter', got {self.llm_provider!r}"
            )
        if self.effective_script_mode == "llm":
            # Хватает одного работающего провайдера в цепочке: остальные —
            # запас. Раньше отсутствие ключа основного роняло запуск, даже
            # когда второй провайдер был настроен и готов писать сценарий.
            if not any(self.has_script_key(p) for p in self.script_provider_chain):
                names = " или ".join(
                    "OPENROUTER_API_KEY" if p == "openrouter" else "ANTHROPIC_API_KEY"
                    for p in self.script_provider_chain
                )
                raise RuntimeError(
                    f"{names} требуется при SCRIPT_MODE=llm "
                    f"(цепочка: {', '.join(self.script_provider_chain)}). "
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
                    # fal нужен, только если он рисует кадры. Раньше его ключ
                    # требовался при любом VIDEO_MODE=provider — но видео с тех
                    # пор делает любой из трёх провайдеров, и требовать ключ
                    # именно fal стало неверно: запуск падал у того, кто платит
                    # Higgsfield и про fal не слышал.
                    *(
                        (("FAL_KEY", self.fal_key),)
                        if "fal" in self.image_providers
                        else ()
                    ),
                    *(
                        (("TOGETHER_API_KEY", self.together_api_key),)
                        if "together" in self.image_providers
                        else ()
                    ),
                )
                if not value
            ]
            if missing:
                raise RuntimeError(
                    f"{', '.join(missing)} требуются при MVP_SAFE_MODE=0. "
                    "Верните MVP_SAFE_MODE=1, чтобы работать на бесплатных заменителях."
                )

            # Настоящее видео требует ключа хотя бы у одного провайдера из
            # цепочки. Без этой проверки сборщик стартовал бы бодро и упал
            # на первом же клипе — после того, как за сценарий и озвучку
            # уже заплачено.
            if self.video_mode == "provider" and not any(
                self.has_video_key(p) for p in self.video_providers
            ):
                names = " или ".join(VIDEO_KEY_NAMES[p] for p in self.video_providers)
                raise RuntimeError(
                    f"{names} требуется при VIDEO_MODE=provider "
                    f"(цепочка: {', '.join(self.video_providers)}). "
                    "Поставьте VIDEO_MODE=kenburns, чтобы обойтись движением по кадру."
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
    # Pollinations бесплатен — ноль записывается явно, чтобы учёт затрат
    # оставался полным и не было дыр в истории проекта.
    "pollinations_per_call": 0.0,
    # FLUX.1-schnell-Free на Together входит в бесплатный тариф.
    "together_image_per_call": float(os.environ.get("COST_TOGETHER_IMAGE", "0")),
    # Kling standard 5s clip on fal, approx
    "fal_video_per_clip": float(os.environ.get("COST_FAL_VIDEO_CLIP", "0.35")),
    # Wan 2.1 480p на Replicate — $0.09 за секунду готового видео, проверено
    # на странице цен 17.09.2026. Пятисекундный клип обходится в $0.45.
    "replicate_video_per_clip": float(os.environ.get("COST_REPLICATE_VIDEO_CLIP", "0.45")),
    # Higgsfield берёт кредитами, цена за клип в документации не объявлена.
    # Ставим ориентир по той же модели у соседей — Kling 2.5 Turbo Pro, пять
    # секунд. Уточняется переменной, когда появится счёт.
    "higgsfield_video_per_clip": float(os.environ.get("COST_HIGGSFIELD_VIDEO_CLIP", "0.35")),
    # Запасная оценка, если OpenRouter не вернул реальную стоимость запроса.
    "openrouter_fallback_per_call": float(os.environ.get("COST_OPENROUTER_CALL", "0.002")),
}
