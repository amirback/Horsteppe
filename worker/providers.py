"""Реестр возможностей провайдеров и маршрутизатор моделей.

Зачем. До этого модуля выбор выглядел так: картинки — по порядку из
переменной окружения, видео — одна модель, зашитая в настройку. Это работает,
пока модель одна. Как только их две, вопрос «какую звать на этот кадр»
начинает стоить денег: крючок и кадр товара заслуживают лучшего, фон —
дешёвого.

Два шага (ТЗ §16). Сначала **жёсткая отсечка**: модель, которая не умеет
image-to-video, не подходит кадру с фотографией товара, сколько бы она ни
стоила. Затем **оценка оставшихся**.

Приоры честные. Своей статистики у проекта пока нет, и притворяться, что она
есть, ТЗ запрещает прямо. Числа ниже — заявленные возможности и наблюдения из
STATUS.md, а не измерения. Как только появится таблица прогонов, приоры
заменяются на неё.

Метрика — **цена за пригодный кадр**, а не цена вызова: модель за $0.10,
которую приходится звать трижды, дороже модели за $0.25, срабатывающей с
первого раза.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

log = logging.getLogger("worker.providers")


@dataclass(frozen=True)
class Capability:
    provider: str
    model: str
    kind: str  # "image" | "video"

    supports_text_to_image: bool = False
    supports_text_to_video: bool = False
    supports_image_to_video: bool = False
    supports_reference_image: bool = False
    supports_first_frame: bool = False

    durations_sec: tuple[float, ...] = ()
    aspect_ratios: tuple[str, ...] = ("9:16", "16:9", "1:1", "4:5")
    max_side: int = 1920

    cost_usd: float = 0.0
    # Заявленное качество и надёжность: 0..1. Источник — раздел «Таблица
    # состояния» в STATUS.md и документация провайдеров, не свои замеры.
    quality_prior: float = 0.5
    reliability_prior: float = 0.5
    latency_prior_sec: float = 60.0

    # Переменная окружения с ключом. Пусто — ключ не нужен.
    key_env: str = ""

    @property
    def cost_per_usable(self) -> float:
        """Цена с поправкой на то, сколько раз придётся звать."""
        return self.cost_usd / max(self.reliability_prior, 0.1)


def _cost(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


# Только те, что действительно работают в проекте. Двадцать провайдеров ТЗ
# заводить запрещает, и это правильно: каждый непроверенный — обещание.
REGISTRY: tuple[Capability, ...] = (
    Capability(
        provider="pollinations", model="flux", kind="image",
        supports_text_to_image=True,
        # Сервис всегда отдаёт 576x1024, что бы ни просили — проверено
        # 2026-09-11, шестнадцать запросов из шестнадцати.
        max_side=1024, cost_usd=0.0,
        quality_prior=0.55, reliability_prior=0.85, latency_prior_sec=45.0,
    ),
    Capability(
        provider="together", model="black-forest-labs/FLUX.1-schnell-Free", kind="image",
        supports_text_to_image=True, max_side=1440, cost_usd=0.0,
        quality_prior=0.65, reliability_prior=0.6, latency_prior_sec=20.0,
        key_env="TOGETHER_API_KEY",
    ),
    Capability(
        provider="fal", model="fal-ai/flux/schnell", kind="image",
        supports_text_to_image=True, max_side=1920,
        cost_usd=_cost("COST_FAL_IMAGE", 0.006),
        quality_prior=0.8, reliability_prior=0.9, latency_prior_sec=15.0,
        key_env="FAL_KEY",
    ),
    Capability(
        provider="fal", model="fal-ai/kling-video/v2.1/standard/image-to-video", kind="video",
        supports_image_to_video=True, supports_reference_image=True, supports_first_frame=True,
        durations_sec=(5.0, 10.0), max_side=1920,
        cost_usd=_cost("COST_FAL_VIDEO_CLIP", 0.35),
        quality_prior=0.75, reliability_prior=0.85, latency_prior_sec=180.0,
        key_env="FAL_KEY",
    ),
    Capability(
        provider="fal", model="fal-ai/kling-video/v2.1/pro/image-to-video", kind="video",
        supports_image_to_video=True, supports_reference_image=True, supports_first_frame=True,
        durations_sec=(5.0, 10.0), max_side=1920,
        cost_usd=_cost("COST_FAL_VIDEO_CLIP_PRO", 0.95),
        quality_prior=0.92, reliability_prior=0.85, latency_prior_sec=300.0,
        key_env="FAL_KEY",
    ),
)


def has_key(capability: Capability) -> bool:
    return not capability.key_env or bool(os.environ.get(capability.key_env, "").strip())


def candidates(
    kind: str,
    *,
    needs_image_to_video: bool = False,
    needs_reference: bool = False,
    aspect: str | None = None,
    duration_sec: float | None = None,
    affordable_usd: float | None = None,
) -> list[Capability]:
    """Шаг A — жёсткая отсечка. Остаются только пригодные, без оценок."""
    out = []
    for cap in REGISTRY:
        if cap.kind != kind or not has_key(cap):
            continue
        if needs_image_to_video and not cap.supports_image_to_video:
            continue
        if needs_reference and not cap.supports_reference_image:
            continue
        if aspect and cap.aspect_ratios and aspect not in cap.aspect_ratios:
            continue
        if duration_sec and cap.durations_sec and duration_sec > max(cap.durations_sec):
            continue
        if affordable_usd is not None and cap.cost_usd > affordable_usd + 1e-9:
            continue
        out.append(cap)
    return out


def score(capability: Capability, importance: float) -> float:
    """Шаг B — оценка. Чем важнее кадр, тем больше весит качество.

    Важность 1.0 — крючок, кадр товара, кульминация: здесь дешевизна почти
    не имеет значения. Важность 0.3 — фон: здесь она решает.
    """
    importance = min(max(importance, 0.0), 1.0)
    quality_weight = 0.35 + 0.45 * importance
    cost_weight = 0.45 - 0.35 * importance

    # Цена приводится к 0..1 по самой дорогой модели своего типа.
    peer_max = max((c.cost_per_usable for c in REGISTRY if c.kind == capability.kind), default=0.0)
    cost_penalty = (capability.cost_per_usable / peer_max) if peer_max else 0.0

    return round(
        quality_weight * capability.quality_prior
        + 0.20 * capability.reliability_prior
        - cost_weight * cost_penalty,
        4,
    )


def why_not(kind: str, *, affordable_usd: float | None = None, **filters) -> str:
    """Почему пригодных моделей не нашлось — деньгами или возможностями.

    Различать обязательно: «не хватило бюджета» человек может исправить сам,
    «провайдер такого не умеет» — нет.
    """
    if affordable_usd is not None and candidates(kind, **filters):
        return (
            f"бюджет проекта не позволяет: остаток ${affordable_usd:.2f} "
            f"ниже цены самой дешёвой подходящей модели"
        )
    if not any(has_key(c) for c in REGISTRY if c.kind == kind):
        return "ключ провайдера не настроен"
    return "подходящей модели нет"


def choose(
    kind: str,
    *,
    importance: float = 0.5,
    shot_label: str = "",
    **filters,
) -> Capability | None:
    """Выбрать модель под кадр и объяснить выбор в логе.

    None означает «пригодных нет» — это не ошибка, а причина откатиться на
    движение по картинке.
    """
    pool = candidates(kind, **filters)
    if not pool:
        log.info("[ROUTER] %s: пригодных моделей нет (%s)", shot_label or kind, filters)
        return None

    ranked = sorted(pool, key=lambda c: (-score(c, importance), c.cost_per_usable))
    best = ranked[0]
    log.info(
        "[ROUTER] %s → %s/%s (оценка %.3f, $%.3f за вызов, важность %.2f); "
        "рассмотрено %d, отклонено по цене/возможностям %d",
        shot_label or kind, best.provider, best.model, score(best, importance),
        best.cost_usd, importance, len(pool), len(REGISTRY) - len(pool),
    )
    return best
