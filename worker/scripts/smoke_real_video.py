"""Один настоящий клип от провайдера — ручная проверка перед включением режима.

Зачем отдельный скрипт. Весь конвейер до сих пор собирал ролики из картинок, и
доказательства, что настоящее видео вообще приходит от провайдера, у нас нет:
путь проверен только на подменённом клиенте. Прогонять ради этого полный
30-секундный ролик — значит заказать шесть клипов вместо одного.

Скрипт делает **ровно один** платный вызов и ничего больше: ни сценария, ни
озвучки, ни монтажа. Повторов нет.

Запускается только руками и только с явным разрешением:

    ALLOW_PAID_SMOKE_TEST=1 worker/.venv/bin/python worker/scripts/smoke_real_video.py

Без переменной скрипт выходит, не обратившись к провайдеру. В pytest он не
попадает: имя файла не начинается с `test_`, и он лежит вне каталога тестов.

Картинку берём готовую — из уже собранного проекта. Новых не создаём.
Переопределить можно переменной SMOKE_IMAGE_URL.

VIDEO_MODE трогать не нужно: шаг видео спрашивает только MVP_SAFE_MODE.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ALLOW_FLAG = "ALLOW_PAID_SMOKE_TEST"
OUT_PATH = ROOT / "output" / "smoke" / "real_video_test.mp4"
REQUESTED_SECONDS = 5


def _fail(message: str) -> int:
    print(f"\n  ОСТАНОВЛЕНО: {message}")
    print("  Платный вызов НЕ выполнялся.")
    return 1


def _probe(path: Path) -> tuple[float, int, int]:
    """Длительность и размер кадра по разбору вывода ffmpeg."""
    import media

    proc = subprocess.run(
        [media.ffmpeg_path(), "-hide_banner", "-i", str(path)],
        capture_output=True, text=True,
    )
    text = proc.stderr
    video = re.search(r"Stream #\d+:\d+.*: Video: .*?(\d{2,5})x(\d{2,5})", text)
    if not video:
        return media.media_duration_sec(path), 0, 0
    return media.media_duration_sec(path), int(video.group(1)), int(video.group(2))


def _reference_image(cfg) -> str:
    """Готовая картинка из последнего собранного проекта."""
    override = os.environ.get("SMOKE_IMAGE_URL", "").strip()
    if override:
        return override

    from db import Db

    rows = (
        Db(cfg).client.table("shots")
        .select("image_url")
        .not_.is_("image_url", "null")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise RuntimeError(
            "в базе нет ни одной готовой картинки — укажите SMOKE_IMAGE_URL вручную"
        )
    return rows[0]["image_url"]


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    print("=== ПРОВЕРКА НАСТОЯЩЕГО ВИДЕО ===")

    if os.environ.get(ALLOW_FLAG) != "1":
        return _fail(
            f"нет разрешения на трату. Запустите с {ALLOW_FLAG}=1, "
            "если согласны оплатить один клип"
        )

    from config import COSTS, Config
    from steps import video_step

    cfg = Config()

    # Значения ключей не печатаем — только факт наличия.
    if not cfg.fal_key:
        return _fail("FAL_KEY не задан")
    if cfg.mvp_safe_mode:
        return _fail("MVP_SAFE_MODE включён — платные вызовы запрещены")

    try:
        image_url = _reference_image(cfg)
    except Exception as e:  # noqa: BLE001 — причина важнее трассировки
        return _fail(str(e))

    cost = COSTS["fal_video_per_clip"]
    print(f"  провайдер:      fal.ai")
    print(f"  модель:         {cfg.fal_video_model}")
    print(f"  длительность:   {REQUESTED_SECONDS} с")
    print(f"  оценка расхода: ${cost:.2f}")
    print(f"  исходный кадр:  {image_url[:78]}…")
    print(f"  ключ FAL_KEY:   задан")
    print("\n  Выполняется ОДИН вызов провайдера. Это может занять несколько минут…")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prompt = "slow cinematic camera push-in, subtle natural motion, film grain"

    try:
        actual_cost = video_step.generate_clip(cfg, image_url, prompt, OUT_PATH)
    except Exception as e:  # noqa: BLE001 — печатаем причину, а не падаем стеком
        print(f"\n  провайдер отказал: {e}")
        print("\nREAL VIDEO SMOKE TEST")
        print(f"  Provider:       fal.ai")
        print(f"  Model:          {cfg.fal_video_model}")
        print(f"  Output:         —")
        print(f"  Duration:       —")
        print(f"  Resolution:     —")
        print(f"  Estimated cost: ${cost:.2f}")
        print("\nSTATUS: FAIL")
        return 1

    problems: list[str] = []
    if not OUT_PATH.exists() or OUT_PATH.stat().st_size == 0:
        problems.append("файл не создан или пуст")
        duration = width = height = 0
    else:
        duration, width, height = _probe(OUT_PATH)
        if duration <= 0:
            problems.append("длительность равна нулю")
        if width <= 0 or height <= 0:
            problems.append("видеопоток не найден")

    print("\nREAL VIDEO SMOKE TEST")
    print(f"  Provider:       fal.ai")
    print(f"  Model:          {cfg.fal_video_model}")
    print(f"  Output:         {OUT_PATH}")
    print(f"  Duration:       {duration:.2f} с")
    print(f"  Resolution:     {width}x{height}")
    print(f"  Estimated cost: ${actual_cost:.2f}")
    if problems:
        print(f"  Проблемы:       {'; '.join(problems)}")
    print(f"\nSTATUS: {'FAIL' if problems else 'PASS'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
