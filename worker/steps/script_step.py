"""Шаг 1: тема -> сценарий, разбитый на сцены.

Провайдер выбирается настройкой LLM_PROVIDER: `openrouter` или `anthropic`.
Оба пути требуют строгий JSON по схеме — разбирать свободный текст регулярками
нельзя, это источник тихих поломок.

SCRIPT_MODE=mock обходит модель целиком и собирает сценарий шаблоном: так
проверяется остальной конвейер (озвучка, кадры, монтаж) за ноль денег.
"""
from __future__ import annotations

import copy
import json
import logging
import re

import httpx

import product_brief
from config import COSTS, Config, anthropic_price

log = logging.getLogger("worker.script")

# Structured-outputs schema: guarantees parseable JSON (no regex extraction).
SCENES_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        # Описание героев и мира, общее для всего ролика. Без него каждый кадр
        # рисуется независимо, и герои меняются каждые три секунды: фильм
        # разваливается на фотографии незнакомых людей.
        "continuity": {
            "type": "string",
            "description": (
                "ENGLISH. The recurring cast and world, repeated in every shot: "
                "each character's age, gender, hair, clothing; the location; "
                "colour palette and lighting. Concrete and unchanging."
            ),
        },
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
                    # Кадры камеры внутри сцены. Раньше их придумывала механика,
                    # склеивая половину закадрового текста с общим промптом, —
                    # и внутри сцены получались случайные разные картинки.
                    "shots": {
                        "type": "array",
                        "description": "2-3 camera shots covering this scene",
                        "items": {
                            "type": "object",
                            "properties": {
                                "framing": {
                                    "type": "string",
                                    "description": "ENGLISH framing, e.g. 'wide establishing shot', 'close-up on hands'",
                                },
                                "action": {
                                    "type": "string",
                                    "description": "ENGLISH: what the same recurring characters do in this shot",
                                },
                                # Сложность движения выбирает модель видео: сложным
                                # кадрам — сильные модели, лёгким — дешёвые (решение
                                # основателя 2026-11-14). Судит сценарист: он знает,
                                # что происходит в кадре, а механика — нет.
                                "motion": {
                                    "type": "string",
                                    "enum": ["complex", "medium", "simple"],
                                    "description": (
                                        "How hard the movement in this shot is for a video model. "
                                        "'complex': people acting, hands at work, talking faces, fast "
                                        "action, liquids, a product being turned or used. 'medium': one "
                                        "subject moving calmly. 'simple': a slow camera move over a still "
                                        "scene — landscape, interior, product standing still."
                                    ),
                                },
                            },
                            "required": ["framing", "action", "motion"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["narration", "image_prompt", "shots"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "continuity", "scenes"],
    "additionalProperties": False,
}


# Схема рекламы отличается двумя полями, и оба обязательны. `strict: True`
# у провайдера требует, чтобы каждое свойство было в `required`, поэтому
# добавить их в общую схему «необязательными» нельзя — пришлось бы менять
# поведение обычных роликов ради рекламы.
def _ad_schema() -> dict:
    schema = copy.deepcopy(SCENES_SCHEMA)
    # Описание поля в схеме сильнее любой просьбы в тексте задания. Общая
    # схема требует назвать «возраст, пол, волосы и одежду персонажа» — и
    # модель послушно выдумывала девушку даже там, где её прямым текстом
    # просили не выдумывать. Для рекламы постоянство — это товар, а не актёр.
    schema["properties"]["continuity"] = {
        "type": "string",
        "description": (
            "ENGLISH. What must never change between shots: the product's shape, "
            "colour, packaging and material; the location; the colour palette; "
            "the lighting. Describe the product and the world, NOT a person. "
            "Do not name a character, an age, a gender, hair or clothing — this "
            "text is pasted into every frame, and a recurring invented face is "
            "what makes an advertisement look like stock footage."
        ),
    }
    scene = schema["properties"]["scenes"]["items"]
    scene["properties"]["purpose"] = {
        "type": "string",
        "description": "Beat name for this scene, lowercase, from the requested structure",
    }
    scene["required"] = [*scene["required"], "purpose"]
    shot = scene["properties"]["shots"]["items"]
    shot["properties"]["product_required"] = {
        "type": "boolean",
        "description": "True when the product must be visible and recognisable in this shot",
    }
    shot["required"] = [*shot["required"], "product_required"]
    return schema


AD_SCENES_SCHEMA = _ad_schema()


class ScriptFailed(RuntimeError):
    """Сценарий не написал никто из цепочки.

    Несёт потраченную сумму: провайдер мог ответить и взять деньги, а ответ
    оказаться негодным. Конвейер обязан записать эту трату, иначе потолок
    бюджета держится на цифре меньше настоящей.
    """

    def __init__(self, message: str, cost_usd: float = 0.0) -> None:
        super().__init__(message)
        self.cost_usd = cost_usd


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
            "shots": [
                {"framing": "wide establishing shot", "action": f"scene {i + 1} begins"},
                {"framing": "close-up", "action": f"detail of scene {i + 1}"},
            ],
        }
        for i in range(n)
    ]
    return {
        "title": topic,
        "continuity": f"Test cast and world for '{short_topic}', {style} look, consistent palette",
        "scenes": scenes,
        "cost_usd": 0.0,
        "provider": "mock",
        "model": "template",
    }


def _mock_ad_script(brief, style: str, duration_sec: int) -> dict:
    """Шаблонная реклама без модели: проверяет остальной конвейер за ноль денег.

    Такты берутся настоящие — те же, что ушли бы в модель, — поэтому по моку
    видно и структуру, и расстановку кадров товара.
    """
    beats = brief.structure(duration_sec)
    scenes = []
    for i, beat in enumerate(beats):
        product = beat in ("product", "benefit", "second_benefit")
        scenes.append({
            "narration": f"{beat.replace('_', ' ').capitalize()}. Тестовая озвучка "
                         f"такта {i + 1} из {len(beats)} для «{brief.product_name}».",
            "image_prompt": f"{style} advertising frame for '{brief.product_name}', "
                            f"beat {beat}, vertical 9:16 composition, no text, no logos",
            "purpose": beat,
            "shots": [
                {"framing": "hero product shot", "action": f"{beat}: product in frame",
                 "product_required": product},
                {"framing": "close-up detail", "action": f"{beat}: detail",
                 "product_required": product},
            ],
        })
    return {
        "title": brief.product_name,
        "continuity": f"The product '{brief.product_name}' keeps its exact shape, colour and "
                      f"packaging in every shot; consistent palette and lighting",
        "scenes": scenes,
        "cost_usd": 0.0,
        "provider": "mock",
        "model": "template",
    }


def generate_script(cfg: Config, topic: str, style: str, duration_sec: int, brief=None,
                    reference_urls: list[str] | None = None) -> dict:
    """Returns {"title": str, "scenes": [{"narration", "image_prompt"}, ...], "cost_usd": float}.

    `brief` — ProductBrief. Если он есть, пишется реклама: другая структура,
    другая схема ответа и прямой запрет выдумывать свойства товара. Обычный
    ролик этим не затронут — у него прежний промпт и прежняя схема.

    `reference_urls` — снимки товара. Режиссёр с поддержкой изображений
    (Anthropic) видит их и описывает товар по фото, а не по догадке.
    """
    if cfg.effective_script_mode == "mock":
        log.info("script: SCRIPT_MODE=mock — skipping Claude, using template scenes")
        return _mock_ad_script(brief, style, duration_sec) if brief else _mock_script(topic, style, duration_sec)

    if brief is not None:
        n = len(brief.structure(duration_sec))
        words_per_scene = _words_per_scene(duration_sec, n)
        prompt = product_brief.ad_prompt(brief, style, duration_sec, words_per_scene)
        schema = AD_SCENES_SCHEMA
        log.info("script: реклама «%s», такты %s", brief.product_name, brief.structure(duration_sec))
        images = [u for u in (reference_urls or []) if u][:MAX_DIRECTOR_IMAGES]
        return _run(cfg, prompt, schema, n, words_per_scene, brief.product_name, images=images)

    n = _scene_count(duration_sec)
    words_per_scene = _words_per_scene(duration_sec, n)

    prompt = f"""You are a short-form video scriptwriter for vertical (9:16) social videos.

Write a script for a {duration_sec}-second video.

Topic: {topic}
Visual style: {style}

Requirements:
- Exactly {n} scenes.
- Each scene's narration is between {words_per_scene} and {words_per_scene + 4} words.
  Fewer makes the finished video too short, more makes it too long; both are failures.
  Count the words. Write narration in the SAME language as the topic.
- The narration must flow as one continuous story across scenes: a hook in scene 1, development, and a punchy ending.
- `continuity` describes the SAME cast and world used in every single shot: name each
  character with age, hair, exact clothing; name the location, the colour palette and
  the lighting. This text is pasted into every image prompt, so it must be concrete
  and must never contradict itself.
- Each image_prompt is in ENGLISH, describes a single striking {style} shot for that scene, mentions vertical 9:16 composition, and contains NO text/captions/logos in the image.
- Give each scene 2-3 `shots`: different framings of the SAME moment and the SAME
  characters — for example a wide shot, then a close-up on a face or hands. Shots are
  camera angles on one continuous action, not separate events with new people.
- No emojis, no hashtags, no scene numbers inside narration."""

    return _run(cfg, prompt, SCENES_SCHEMA, n, words_per_scene, topic)


PHOTO_NOTE = """

The attached photos show the real product. In `continuity`, describe exactly what you
see on them: shape, colours, materials, packaging and any visible text. Do not invent
details that are not on the photos."""


def _run(cfg: Config, prompt: str, schema: dict, n: int, words_per_scene: int, title: str,
         images: list[str] | None = None) -> dict:
    """Общий хвост обоих режиссёров: цепочка провайдеров, проверка, длина.

    Провайдеры пробуются по очереди, как у кадров. Один провайдер — одна
    точка отказа: OpenRouter уже отвечал и 429, и пустым ответом, и тогда
    падал весь проект, хотя сценарий мог написать кто-то другой.

    Отказ модерации — исключение из правила: если тему отклонили по
    содержанию, её отклонит и следующая модель, а лишний вызов будет стоить
    денег и времени.
    """
    chain = cfg.script_provider_chain
    callers = {"openrouter": _via_openrouter, "anthropic": _via_anthropic}
    last_error: Exception | None = None
    # Деньги, потраченные на попытки, которые ничего не дали. Отвечает
    # провайдер — значит, вызов оплачен, даже если ответ оказался негодным.
    # Без этой суммы журнал затрат отстаёт от кошелька.
    wasted = 0.0

    for position, provider in enumerate(chain, start=1):
        if not cfg.has_script_key(provider):
            log.info("script: %s пропущен — ключ не задан", provider)
            continue
        model = cfg.script_model(provider)
        try:
            if images and provider == "anthropic":
                # Снимки уходят только тому, кто умеет их читать. Остальным —
                # прежний текстовый запрос, без упоминания вложений.
                data, cost = _via_anthropic(cfg, prompt + PHOTO_NOTE, schema, images=images)
            else:
                data, cost = callers[provider](cfg, prompt, schema)
        except ScriptRefusedError:
            raise
        except Exception as e:  # noqa: BLE001 — падение одного провайдера не финал
            last_error = e
            log.warning("script: %s (%s) не справился: %s", provider, model, e)
            if position < len(chain):
                log.info("script: пробуем следующего провайдера")
            continue

        # Проверка внутри попытки, а не после неё. Раньше негодный ответ —
        # скажем, три сцены вместо четырёх — не передавал ход следующему
        # провайдеру, а ронял проект целиком. Причём вызов был уже оплачен,
        # и в журнал эта трата не попадала никогда.
        try:
            scenes = _clamp_narration(_validate(data, n), words_per_scene)
        except Exception as e:  # noqa: BLE001 — ответ не той формы это не финал
            wasted += cost
            last_error = e
            log.warning(
                "script: %s (%s) ответил, но ответ негодный (потрачено $%.4f): %s",
                provider, model, cost, e,
            )
            continue

        total = round(cost + wasted, 6)
        if wasted:
            log.info(
                "script: %d сцен, написал %s (%s), стоимость $%.4f — "
                "из них $%.4f ушло на неудачные попытки",
                len(scenes), provider, model, total, wasted,
            )
        else:
            log.info(
                "script: %d сцен, сценарий написал %s (%s), стоимость $%.4f",
                len(scenes), provider, model, total,
            )
        return {
            "title": data.get("title", title),
            "continuity": (data.get("continuity") or "").strip(),
            "scenes": scenes,
            "cost_usd": total,
            "provider": provider,
            "model": model,
        }

    raise ScriptFailed(
        f"сценарий не написал ни один провайдер из цепочки {', '.join(chain)}: {last_error}",
        cost_usd=wasted,
    )


# Реальный темп синтезированной речи, замеренный на готовых роликах: 2.57 и
# 2.82 слова в секунду на двух прогонах. Берём середину. В коде стояло 2.3, и
# ролик выходил короче заказанного.
WORDS_PER_SECOND = 2.70
# Небольшой запас на недобор: модель пишет меньше, чем просят. Большим он быть
# не должен — перебор теперь ограничен сверху, и раздувать заказ незачем.
LENGTH_SAFETY = 1.05


def _words_per_scene(duration_sec: int, scene_count: int) -> int:
    """Сколько слов заказать у сценариста на одну сцену.

    Просили 30 секунд — получали 22.6, то есть на четверть меньше. Допуск в
    CLAUDE.md §8 составляет ±20%, так что это был выход за границу, а не
    особенность. Причин было две, и обе учтены здесь.
    """
    return max(4, round(duration_sec * LENGTH_SAFETY / scene_count * WORDS_PER_SECOND))


# Сколько слов сверх заказа ещё терпимо. Просьба «не меньше N» одну беду
# сменила на другую: модель написала 162 слова вместо 88, и ролик вышел
# 57 секунд вместо 30. Верхняя граница обязана быть жёсткой и подобрана так,
# чтобы даже полный перебор оставался внутри допуска ±20% из CLAUDE.md §8.
NARRATION_OVERSHOOT = 1.12


def _clamp_narration(scenes: list[dict], words_per_scene: int) -> list[dict]:
    """Обрезать слишком длинную озвучку по границе предложения.

    Модель систематически промахивается мимо заказанной длины в обе стороны,
    а длительность ролика идёт ровно за голосом. Обрезка по точке звучит как
    законченная мысль; обрезка по слову — как оборванная запись.
    """
    limit = int(words_per_scene * NARRATION_OVERSHOOT)
    out = []
    for scene in scenes:
        text = (scene.get("narration") or "").strip()
        if len(text.split()) <= limit:
            out.append(scene)
            continue

        kept: list[str] = []
        for sentence in re.split(r"(?<=[.!?…])\s+", text):
            if kept and len(" ".join(kept + [sentence]).split()) > limit:
                break
            kept.append(sentence)
        trimmed = " ".join(kept)
        # Первое предложение принимается всегда — иначе можно остаться ни с
        # чем. Но если и оно длиннее лимита, режем по словам: иначе одно
        # длинное предложение проходит мимо ограничения целиком.
        if not trimmed or len(trimmed.split()) > limit:
            trimmed = " ".join(text.split()[:limit])
        log.info("озвучка сцены укорочена: %d слов → %d", len(text.split()), len(trimmed.split()))
        out.append({**scene, "narration": trimmed})
    return out


def _validate(data: dict, expected: int) -> list[dict]:
    """Модель могла вернуть синтаксически верный, но бессмысленный ответ."""
    scenes = data.get("scenes") or []
    if not (2 <= len(scenes) <= 8):
        raise RuntimeError(f"модель вернула {len(scenes)} сцен, ожидалось около {expected}")
    for s in scenes:
        if not (s.get("narration") or "").strip() or not (s.get("image_prompt") or "").strip():
            raise RuntimeError("модель вернула пустое поле сцены")
    return scenes


def _via_openrouter(cfg: Config, prompt: str, schema: dict = None) -> tuple[dict, float]:
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
            "json_schema": {"name": "scenes", "strict": True, "schema": schema or SCENES_SCHEMA},
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


# Потолок ответа режиссёра. У Fable 5.2, Opus 5 и новее размышление включено
# всегда, и его токены входят в этот же потолок. Прежние 4000 были рассчитаны
# на модель без размышления: с ним ответ мог оборваться раньше первой строки
# сценария, вызов при этом оплачен. 16000 — рекомендуемый запас для запроса
# без потоковой передачи; платим мы только за то, что модель реально написала.
ANTHROPIC_MAX_TOKENS = 16000
# Размышление занимает десятки секунд; двух минут, как у OpenRouter, мало.
# 600 — штатный таймаут самого SDK для запроса без потоковой передачи. Короче
# нельзя: по таймауту SDK повторяет запрос, а оборванный ответ может быть
# оплачен. Задача считается зависшей только через 30 минут.
ANTHROPIC_TIMEOUT_SEC = 600
# Сколько снимков товара показывать режиссёру. Каждый стоит ~3 тыс. входных
# токенов; первых двух хватает, чтобы описать товар таким, какой он есть.
MAX_DIRECTOR_IMAGES = 2

# Модели, у которых отказ фильтра безопасности можно автоматически передать
# запасной модели на стороне Anthropic (параметр `fallbacks`). Без этого
# ложное срабатывание фильтра на безобидную тему роняло бы проект целиком.
_REFUSAL_FALLBACK_MODELS = {
    "claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5",
}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Семейства, принимающие output_config.effort. Старым моделям параметр
# не отправляется: они отвечают на него ошибкой.
_EFFORT_PREFIXES = (
    "claude-fable-", "claude-mythos-", "claude-opus-5", "claude-opus-4-6", "claude-opus-4-7",
    "claude-opus-4-8", "claude-sonnet-5", "claude-sonnet-4-6", "claude-haiku-5",
)


def _via_anthropic(cfg: Config, prompt: str, schema: dict = None,
                   images: list[str] | None = None) -> tuple[dict, float]:
    """Сценарий через Anthropic напрямую.

    `images` — публичные ссылки на снимки товара. Режиссёр видит товар и
    описывает его в `continuity` таким, какой он на фото, а не выдумывает.
    """
    # Импорт здесь, а не наверху: в безопасном режиме этот код не выполняется,
    # и воркер должен запускаться без пакета anthropic — как и без fal_client.
    import anthropic

    # Организационный ключ обязан назвать рабочее пространство, иначе запрос
    # отклоняется ещё до модели. Ключ, созданный внутри пространства, этого
    # не требует, и заголовок просто не добавляется.
    headers = (
        {"anthropic-workspace-id": cfg.anthropic_workspace_id}
        if cfg.anthropic_workspace_id else None
    )
    client = anthropic.Anthropic(
        api_key=cfg.anthropic_api_key, timeout=ANTHROPIC_TIMEOUT_SEC, default_headers=headers
    )
    model = cfg.llm_model.strip()
    output_config: dict = {"format": {"type": "json_schema", "schema": schema or SCENES_SCHEMA}}
    if model.startswith(_EFFORT_PREFIXES):
        output_config["effort"] = cfg.llm_effort

    content: list[dict] | str = prompt
    if images:
        content = [
            {"type": "image", "source": {"type": "url", "url": url}}
            for url in images[:MAX_DIRECTOR_IMAGES]
        ] + [{"type": "text", "text": prompt}]

    request = dict(
        model=model,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        output_config=output_config,
        messages=[{"role": "user", "content": content}],
    )
    # Параметры размышления и sampling не отправляются вовсе: у Fable 5.2
    # размышление включено всегда, а temperature и принудительный tool_choice
    # отклоняются ошибкой 400.
    if model in _REFUSAL_FALLBACK_MODELS:
        response = client.beta.messages.create(betas=[_FALLBACK_BETA], fallbacks="default", **request)
    else:
        response = client.messages.create(**request)

    # Причина остановки проверяется ДО чтения ответа: при отказе текста нет.
    # Отказ здесь означает, что отказали и основная, и запасная модель.
    if response.stop_reason == "refusal":
        raise ScriptRefusedError("Тема отклонена модерацией контента. Переформулируйте запрос.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Сценарий не поместился в лимит токенов — повторите")

    text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), "")
    if not text.strip():
        raise RuntimeError("Anthropic вернул ответ без текста сценария")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Anthropic вернул не JSON: {text[:200]}") from e

    # Цена — по модели, которая реально ответила: при отказе основной это
    # запасная, и её тариф другой.
    served_by = getattr(response, "model", None) or model
    price_in, price_out = anthropic_price(served_by if isinstance(served_by, str) else model)
    usage = response.usage
    cost = usage.input_tokens / 1_000_000 * price_in + usage.output_tokens / 1_000_000 * price_out
    if served_by != model:
        log.info("script: %s отказала, сценарий написала запасная %s", model, served_by)
    return data, cost
