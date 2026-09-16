"""Бриф товара и режиссура рекламы.

Почему реклама — не «история про товар». Обычный ролик держит зрителя
сюжетом: завязка, развитие, финал. Реклама держит его другим: за первую
секунду попасть в проблему или желание, показать товар так, чтобы он
опознавался, доказать одну-две выгоды и закончить действием. Поставить
рекламу на общий сценарный шаблон — значит получить красивый ролик, после
которого непонятно, что покупать.

Главное ограничение — ТЗ §9: **не выдумывать свойства товара.** Модель охотно
допишет «водонепроницаемый», «сертифицирован» и «-30% сегодня», если ей не
запретить. Поэтому в промпт уходит закрытый список фактов от человека и
прямой запрет добавлять что-либо сверх него.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger("worker.brief")

# Такты рекламы. Ключ уходит в кадр как `purpose`, значение — инструкция
# сценаристу.
BEATS: dict[str, str] = {
    "hook": "HOOK: stop the scroll in the first second. No product yet, no brand name.",
    "problem": "PROBLEM: the everyday annoyance, shown through objects and mess, not through an actor's face.",
    "desire": "DESIRE: the state the audience wants, shown through the scene and the light, not through a model posing.",
    "product": "PRODUCT: the product itself, clearly recognisable, matching the reference photo.",
    "benefit": "BENEFIT: the single strongest benefit, demonstrated in use.",
    "second_benefit": "SECOND BENEFIT: one more concrete benefit, different from the first.",
    "lifestyle": "LIFESTYLE: the product inside the audience's real day, emotional payoff.",
    "cta": "CTA: the exact next step, spoken plainly.",
}

# Порядок предпочтения тактов под цель рекламы. Первый такт всегда крючок,
# последний — призыв; середина набирается по приоритету и обрезается под
# длительность. Один и тот же шаблон на все цели ТЗ §10 прямо запрещает.
GOAL_PRIORITY: dict[str, list[str]] = {
    "sales": ["hook", "problem", "product", "benefit", "second_benefit", "cta"],
    "launch": ["hook", "product", "benefit", "second_benefit", "lifestyle", "cta"],
    "awareness": ["hook", "desire", "lifestyle", "product", "benefit", "cta"],
    "other": ["hook", "product", "benefit", "lifestyle", "cta"],
}
DEFAULT_GOAL = "other"

# Сколько секунд живёт один такт рекламы. Плотнее — зритель не успевает
# прочитать мысль, реже — ролик провисает.
SEC_PER_BEAT = 5.5
MIN_BEATS = 3
MAX_BEATS = 6


# Без этих тактов ролик перестаёт быть рекламой: не посмотрят, не узнают
# товар, не поймут, что делать дальше. Короткий хронометраж режет что угодно,
# кроме них.
REQUIRED_BEATS = ("hook", "product", "cta")


def structure_for(goal: str, duration_sec: float, benefit_count: int = 1) -> list[str]:
    """Такты рекламы под цель и длительность.

    Пятнадцать секунд — это три такта, тридцать — пять-шесть. Обрезка идёт по
    приоритету цели, но кадр товара из неё выведен: реклама без товара была бы
    красивым роликом ни о чём, и первая же версия этой функции именно такую и
    выдавала на пятнадцати секундах.
    """
    priority = GOAL_PRIORITY.get((goal or "").strip().lower(), GOAL_PRIORITY[DEFAULT_GOAL])
    budget = max(MIN_BEATS, min(MAX_BEATS, round(duration_sec / SEC_PER_BEAT)))

    middle = [b for b in priority if b not in ("hook", "cta")]
    if benefit_count < 2:
        # Второй выгоды не существует — придумывать её запрещено.
        middle = [b for b in middle if b != "second_benefit"]

    chosen = middle[: max(budget - 2, 1)]
    if "product" not in chosen:
        chosen = [*chosen[:-1], "product"]
        chosen.sort(key=priority.index)
    return ["hook", *chosen, "cta"]


@dataclass(frozen=True)
class ProductBrief:
    """Факты о товаре — ровно те, что дал человек, и ни одним больше."""

    product_name: str
    product_description: str = ""
    benefits: list[str] = field(default_factory=list)
    target_audience: str = ""
    ad_goal: str = DEFAULT_GOAL
    call_to_action: str = ""
    product_url: str = ""
    reference_count: int = 0

    @classmethod
    def from_project(cls, project: dict, reference_count: int = 0) -> "ProductBrief | None":
        """Собрать бриф из проекта. None — если рекламировать нечего."""
        raw = project.get("brief") or {}
        name = (raw.get("product_name") or "").strip()
        if not name:
            return None
        benefits = [b.strip() for b in (raw.get("product_benefits") or []) if str(b).strip()]
        return cls(
            product_name=name,
            product_description=(raw.get("product_description") or "").strip(),
            benefits=benefits,
            target_audience=(raw.get("target_audience") or "").strip(),
            ad_goal=(raw.get("ad_goal") or DEFAULT_GOAL).strip().lower(),
            call_to_action=(raw.get("call_to_action") or "").strip(),
            product_url=(raw.get("product_url") or "").strip(),
            reference_count=reference_count,
        )

    def facts_block(self) -> str:
        """Закрытый список фактов для сценариста."""
        lines = [f"PRODUCT NAME: {self.product_name}"]
        if self.product_description:
            lines.append(f"WHAT IT IS: {self.product_description}")
        if self.benefits:
            lines.append("BENEFITS THE OWNER STATED:")
            lines += [f"  - {b}" for b in self.benefits]
        if self.target_audience:
            lines.append(f"AUDIENCE: {self.target_audience}")
        if self.call_to_action:
            lines.append(f"CALL TO ACTION: {self.call_to_action}")
        return "\n".join(lines)

    def structure(self, duration_sec: float) -> list[str]:
        return structure_for(self.ad_goal, duration_sec, len(self.benefits))


@dataclass(frozen=True)
class VisualReferenceBrief:
    """Режим «оживить фотографию»: что на снимке и как ему двигаться.

    Собирается из того, что видно и что попросил человек. Ничего не
    додумывает: чем меньше отсебятины в промпте, тем ближе результат к
    исходному кадру.
    """

    creative_direction: str
    width: int = 0
    height: int = 0

    @property
    def aspect_hint(self) -> str:
        if not self.width or not self.height:
            return ""
        return "vertical" if self.height > self.width else "horizontal"

    def motion_prompt(self) -> str:
        """Промпт для image-to-video. Камера и субъект названы раздельно —
        иначе провайдер отвечает одним медленным наездом на всё подряд."""
        direction = self.creative_direction.strip() or (
            "subtle natural motion of the subject, slow cinematic camera move"
        )
        parts = [
            direction,
            "keep the subject, framing and colours of the source photo unchanged",
            "no new objects, no text, no warping",
        ]
        if self.aspect_hint:
            parts.append(f"{self.aspect_hint} framing")
        return ". ".join(parts)


# ------------------------------------------------------------ сценаристу --

# Запрет на выдумывание. Формулировка жёсткая намеренно: мягкую модель
# трактует как пожелание и дописывает «водонепроницаемый» к обычной кружке.
NO_INVENTION = (
    "CRITICAL: use ONLY the facts listed above. Do NOT invent features, materials, "
    "certifications, prices, discounts, awards, statistics or comparisons with "
    "competitors. If a fact is not listed, it does not exist for this script."
)

# Почему в рекламе запрещены лица.
#
# Первая собранная реклама термокружки отдала три кадра из семи под
# сгенерированную девушку, к товару отношения не имевшую. Смотрится это как
# сток, а не как реклама: генератор кадров хуже всего справляется именно с
# лицами — они первыми выдают, что картинка нарисована. Те же деньги и то же
# время, потраченные на предмет, фактуру и руки, дают кадр, который от съёмки
# почти не отличить.
#
# Это не про «нельзя показывать людей» вообще: человек в кадре появляется
# руками, плечом, силуэтом, отражением. Запрещено ровно то, что ломается —
# крупное узнаваемое лицо анонимной модели.
NO_STOCK_FACES = (
    "VISUAL RULE — no stock faces. Do NOT write shots built around a generated "
    "person's face. No portraits, no models looking at camera, no close-ups of "
    "anonymous faces. People appear only as hands, a shoulder, a silhouette, a "
    "blurred figure in the background or a reflection. "
    "The hero of every frame is the product itself, its texture and its "
    "environment: steam, condensation, grain of the table, morning light, the "
    "moment of use. Describe materials and light, not casting."
)


def ad_prompt(brief: ProductBrief, style: str, duration_sec: int, words_per_scene: int) -> str:
    """Задание сценаристу рекламы."""
    beats = brief.structure(duration_sec)
    beat_lines = "\n".join(f"  Scene {i + 1} — {BEATS[b]}" for i, b in enumerate(beats))
    reference_note = (
        f"The owner uploaded {brief.reference_count} photo(s) of the real product. "
        "Product scenes must describe THAT product, not a generic stand-in."
        if brief.reference_count
        else "No product photo was uploaded: describe the product only as stated above."
    )

    return f"""You are writing a {duration_sec}-second vertical (9:16) advertisement.

{brief.facts_block()}

{NO_INVENTION}

{NO_STOCK_FACES}

Structure — exactly {len(beats)} scenes, in this order:
{beat_lines}

Requirements:
- Narration in the SAME language as the product description. {words_per_scene}–{words_per_scene + 4} words per scene.
- `purpose` of each scene is its beat name from the list above, lowercase.
- `product_required` is true for any shot where the product must be visible and
  recognisable, false for mood, texture or environment shots.
- {reference_note}
- Each `image_prompt` is ENGLISH, describes one {style} advertising frame, vertical
  9:16, no text/captions/logos rendered in the image.
- Give each scene 2-3 `shots`: different framings of the same moment — for a product
  beat that means hero shot plus a detail, not two unrelated pictures.
- `continuity` fixes what must never change between shots: the product's shape,
  colour and packaging, the palette, the lighting and the location. Do not put a
  described person into `continuity` — it is pasted into every frame, and a
  recurring generated face is exactly what makes an ad look like stock footage.
- No emojis, no hashtags, no scene numbers in narration."""
