"""Контрольная проверка качества: ОДИН клип, 5 секунд.

Зачем. Аудит 2026-09-20 нашёл, что модель «кадр → видео» наследует пропорции
поданной картинки, и квадратное фото товара давало квадратный клип, у
которого монтаж выбрасывал 44% ширины. Правка сделана, тесты её закрывают —
но тест доказывает арифметику, а не поведение чужого сервиса. Доказать
поведение может только один настоящий вызов.

Проверка минимальная намеренно: один снимок, одна модель, один клип. Всё,
что можно выяснить без денег, выясняется без денег.

БЕЗ ТРАТ — показывает точное тело запроса и обрезку снимка, никуда не ходит:

    worker/.venv/bin/python worker/scripts/quality_probe.py

С ОДНИМ ПЛАТНЫМ ВЫЗОВОМ:

    ALLOW_QUALITY_PROBE=1 worker/.venv/bin/python worker/scripts/quality_probe.py

Снимок берётся последний загруженный в проектах. Свой можно задать так:

    PROBE_IMAGE_URL=https://.../photo.jpg

Результат — в `output/debug_quality/<дата-время>/`: сырой клип провайдера,
тело запроса без ключей, замеры и таблица сравнения.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

ALLOW_FLAG = "ALLOW_QUALITY_PROBE"

# Режим разбора обязателен: без него проверять будет нечего.
os.environ["HORSTEPPE_QUALITY_DEBUG"] = "1"

import media  # noqa: E402
import quality_debug  # noqa: E402
import references as references_mod  # noqa: E402
from config import COSTS, Config  # noqa: E402
from db import Db  # noqa: E402
from steps import video_step  # noqa: E402

MOTION = "slow push in on the product, soft light drifting across the surface"


def _newest_reference(db: Db) -> dict | None:
    """Последний загруженный снимок товара — по всем проектам.

    Порядок по дате, а если колонки нет — просто последний из выборки:
    проверка не должна падать из-за того, чего не знает о схеме.
    """
    table = db.client.table("project_references").select("*")
    try:
        rows = table.order("created_at", desc=True).limit(1).execute().data
    except Exception:  # noqa: BLE001 — схема важнее догадок о ней
        rows = db.client.table("project_references").select("*").limit(50).execute().data
    return rows[-1] if rows else None


def main() -> int:
    cfg = Config()
    work = ROOT.parent / "output" / "debug_quality" / "_probe"
    work.mkdir(parents=True, exist_ok=True)

    url = os.environ.get("PROBE_IMAGE_URL", "").strip()
    mime = "image/jpeg"
    if not url:
        db = Db(cfg)
        row = _newest_reference(db)
        if not row:
            print("Снимков в базе нет. Загрузите фото товара через сайт или задайте PROBE_IMAGE_URL.")
            return 1
        url, mime = row["public_url"], row.get("mime_type") or "image/jpeg"
        print(f"Снимок из базы: {row.get('width')}×{row.get('height')}, загружен {row.get('created_at')}")

    # 1. что было бы без правки
    import httpx

    src = work / "source.img"
    with httpx.Client(timeout=120) as client:
        resp = client.get(url)
        resp.raise_for_status()
    src.write_bytes(resp.content)
    src_w, src_h = media.image_size(src)

    aspect = media.frame_size(cfg.video_format)
    fitted = references_mod.fit_aspect(src, work / "fitted.png", aspect, mime)
    fit_w, fit_h = fitted["width"], fitted["height"]

    print("\n=== СНИМОК ===")
    print(f"  исходный          {src_w}×{src_h}  (отношение {src_w / src_h:.3f})")
    print(f"  после обрезки     {fit_w}×{fit_h}  (отношение {fit_w / fit_h:.3f})")
    print(f"  целевой кадр      {aspect[0]}×{aspect[1]}  (отношение {aspect[0] / aspect[1]:.3f})")

    # Сколько ширины выбросил бы монтаж, получив клип такой формы.
    def kept_width(w: int, h: int) -> float:
        scale = max(aspect[0] / w, aspect[1] / h)
        return aspect[0] / (w * scale)

    print("\n=== СКОЛЬКО ШИРИНЫ ДОЙДЁТ ДО ЗРИТЕЛЯ ===")
    print(f"  было бы без правки  {kept_width(src_w, src_h) * 100:.0f}%")
    print(f"  с правкой           {kept_width(fit_w, fit_h) * 100:.0f}%")

    model = cfg.higgsfield_video_model.strip("/")
    payload = {
        "prompt": MOTION,
        "image_url": "<ссылка на обрезанный снимок>",
        "duration": video_step.HIGGSFIELD_DURATION,
        "cfg_scale": video_step.HIGGSFIELD_CFG_SCALE,
        "negative_prompt": video_step.HIGGSFIELD_NEGATIVE,
    }
    print("\n=== ЗАПРОС, КОТОРЫЙ УЙДЁТ ===")
    print(f"  POST {video_step.HIGGSFIELD_BASE}/{model}")
    for key, value in payload.items():
        print(f"  {key}: {value}")
    print(f"\n  наша оценка стоимости: ${COSTS['higgsfield_video_per_clip']:.2f} за клип")
    print("  (оценка, а не факт: в API Higgsfield цены нет — см. docs/AUDIT_QUALITY.md §J)")

    if os.environ.get(ALLOW_FLAG, "") != "1":
        print(f"\nПлатный вызов НЕ сделан. Чтобы сделать, запустите с {ALLOW_FLAG}=1")
        return 0

    # 2. платный вызов — ровно один
    print("\n=== ВЫЗОВ ПРОВАЙДЕРА ===")
    db = Db(cfg)
    ready = Path(fitted["path"])
    public = db.upload(f"probe/{ready.name}", ready.read_bytes(), "image/png")
    print(f"  снимок опубликован: {public[:80]}…")

    clip = work / "probe_clip.mp4"
    done = video_step.generate_clip(
        cfg, public, MOTION, clip,
        provider="higgsfield", model=model,
        cost_usd=COSTS["higgsfield_video_per_clip"],
    )
    print(f"  сделал: {done.provider} / {done.model}")

    raw = quality_debug.video_info(clip)
    print(f"  сырой клип: {raw.get('width')}×{raw.get('height')}, "
          f"{raw.get('fps')} кадр/с, {raw.get('bitrate_kbps')} кбит/с, "
          f"{raw.get('duration_sec')} с")

    # 3. через монтаж — то, что увидит зритель
    segment = work / "probe_segment.mp4"
    media.make_clip_segment(clip, segment, 4.0, aspect)
    final = quality_debug.video_info(segment)

    print("\n=== ИТОГ ===")
    print(f"  провайдер прислал  {raw.get('width')}×{raw.get('height')}")
    print(f"  зритель увидит     {final.get('width')}×{final.get('height')}")
    lost = 1 - kept_width(int(raw.get("width") or 1), int(raw.get("height") or 1))
    print(f"  потеряно ширины    {lost * 100:.0f}%")
    if lost > 0.05:
        print("  ⚠ ПРАВКА НЕ СРАБОТАЛА: потери больше 5%, разбираться дальше")
    else:
        print("  ✓ правка работает: кадр доходит до зрителя целиком")
    print(f"\n  файлы: {work}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
