"""Режим разбора качества: что именно прислал провайдер, до монтажа.

Зачем отдельный режим. Спор «плохо сгенерировало» против «плохо смонтировали»
нельзя решить, глядя на готовый ролик: к финалу файл пересжат три раза,
обрезан под формат и склеен с соседями. Нужен сырой файл провайдера, рядом с
ним — запрос, который его породил, и размеры обоих. Тогда видно, на каком
шаге потерялось качество, а не кажется.

Включается переменной окружения:

    HORSTEPPE_QUALITY_DEBUG=1

Выключен — не делает ничего и не стоит ни одного лишнего вызова ffmpeg.
Складывает всё в `output/debug_quality/<дата-время>/`.

Что сюда НЕ попадает ни при каких обстоятельствах: заголовки запроса,
ключи, секреты. Запрос сохраняется только телом, и тело дополнительно
просеивается по именам полей — на случай, если завтра провайдер потребует
класть ключ внутрь JSON.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

log = logging.getLogger("worker.quality_debug")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "output" / "debug_quality"

# Имена полей, значение которых не сохраняется никогда. Список намеренно
# шире, чем нужно сегодня: дешевле лишний раз затереть безобидное поле, чем
# один раз положить ключ в файл, который потом попадёт в архив или в чат.
_SECRET_NAMES = re.compile(r"key|secret|token|auth|password|credential|signature", re.I)
_REDACTED = "<скрыто>"


def enabled() -> bool:
    return os.environ.get("HORSTEPPE_QUALITY_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")


def _session_dir() -> Path:
    """Каталог текущего прогона.

    Имя по времени запуска, а не по проекту: разбор качества обычно значит
    «сделай один ролик и покажи, что получилось», и два прогона подряд не
    должны затирать друг друга.
    """
    base = Path(os.environ.get("HORSTEPPE_DEBUG_DIR", "").strip() or DEFAULT_DIR)
    stamp = os.environ.get("HORSTEPPE_DEBUG_STAMP")
    if not stamp:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.environ["HORSTEPPE_DEBUG_STAMP"] = stamp
    path = base / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def redact(value):
    """Убрать из данных всё, что похоже на секрет — по имени поля.

    Рекурсивно, потому что тело запроса вложенное, и ключ, спрятанный в
    третьем уровне словаря, ничем не безопаснее ключа в первом.
    """
    if isinstance(value, dict):
        return {
            k: (_REDACTED if _SECRET_NAMES.search(str(k)) else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def video_info(path: Path) -> dict:
    """Размер, частота кадров, битрейт и вес файла — из вывода ffmpeg.

    Отдельного ffprobe в зависимостях нет, и заводить его ради отладки
    незачем: ffmpeg печатает описание потока в stderr.
    """
    import media

    info: dict = {"file": path.name, "bytes": path.stat().st_size if path.exists() else 0}
    try:
        proc = subprocess.run(
            [media.ffmpeg_path(), "-hide_banner", "-i", str(path)],
            capture_output=True, text=True, timeout=120,
        )
        text = proc.stderr
        if m := re.search(r"Video: .*?(\d{2,5})x(\d{2,5})", text):
            info["width"], info["height"] = int(m.group(1)), int(m.group(2))
        if m := re.search(r"([\d.]+) fps", text):
            info["fps"] = float(m.group(1))
        if m := re.search(r"bitrate: (\d+) kb/s", text):
            info["bitrate_kbps"] = int(m.group(1))
        if m := re.search(r"Duration: (\d+):(\d+):([\d.]+)", text):
            h, mm, s = m.groups()
            info["duration_sec"] = round(int(h) * 3600 + int(mm) * 60 + float(s), 3)
        info["has_audio"] = "Audio:" in text
    except Exception as e:  # noqa: BLE001 — отладка не имеет права ронять сборку
        info["error"] = str(e)[:200]
    return info


def record_clip(label: str, provider: str, model: str, payload: dict, raw: Path) -> None:
    """Сохранить сырой клип провайдера и запрос, который его породил.

    Сырой файл копируется, а не перемещается: дальше он нужен конвейеру.
    Любая ошибка здесь проглатывается — отладочный режим не должен стоить
    пользователю заказа.
    """
    if not enabled():
        return
    try:
        out = _session_dir()
        shutil.copy2(raw, out / f"{label}_raw{raw.suffix}")
        (out / f"{label}_request_safe.json").write_text(
            json.dumps(
                {"provider": provider, "model": model, "payload": redact(payload)},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        info = video_info(raw)
        (out / f"{label}_raw_probe.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        log.info(
            "[QUALITY DEBUG] %s: %s/%s → %sx%s, %s кбит/с, %s",
            label, provider, model, info.get("width"), info.get("height"),
            info.get("bitrate_kbps"), out.name,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("[QUALITY DEBUG] не удалось сохранить %s: %s", label, e)


def record_final(final: Path) -> None:
    """Замерить готовый ролик и сложить сравнение рядом с сырыми клипами.

    Ради этой таблицы режим и существует: слева то, что прислал провайдер,
    справа то, что увидит зритель. Если разрешение падает здесь — виноват
    монтаж, а не модель.
    """
    if not enabled():
        return
    try:
        out = _session_dir()
        info = video_info(final)
        (out / "final_probe.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        raws = sorted(out.glob("*_raw_probe.json"))
        rows = [json.loads(p.read_text(encoding="utf-8")) for p in raws]
        lines = ["источник | размер | кадр/с | кбит/с | сек"]
        for name, row in zip([p.name.replace("_raw_probe.json", "") for p in raws], rows):
            lines.append(
                f"{name} | {row.get('width')}x{row.get('height')} | {row.get('fps')} "
                f"| {row.get('bitrate_kbps')} | {row.get('duration_sec')}"
            )
        lines.append(
            f"ГОТОВЫЙ РОЛИК | {info.get('width')}x{info.get('height')} | {info.get('fps')} "
            f"| {info.get('bitrate_kbps')} | {info.get('duration_sec')}"
        )
        (out / "comparison.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        log.info("[QUALITY DEBUG] сравнение записано: %s", out / "comparison.txt")
    except Exception as e:  # noqa: BLE001
        log.warning("[QUALITY DEBUG] не удалось замерить готовый ролик: %s", e)
