"""Фотография, которую принёс пользователь: приведение к рабочему виду.

Что здесь важно и почему именно так.

**Не пересжимать без нужды.** Снимок товара — исходник, а не промежуточный
файл. Если он уже в рабочих границах и в понятном формате, байты уходят
провайдеру как есть: каждое лишнее сжатие JPEG съедает ту самую резкость,
ради которой человек и приносил фотографию.

**Поворот по EXIF.** Телефон пишет ориентацию в метаданные, а пиксели
оставляет как сняты. FFmpeg для неподвижных кадров эти метаданные
игнорирует, и товар уезжает боком — причём молча. Pillow в зависимостях нет
и добавлять его запрещено (CLAUDE.md §4), поэтому ориентация читается
разбором APP1 вручную: сорок строк против новой зависимости.

**Никогда не растягивать.** Пропорции сохраняются всегда; уменьшение — только
когда сторона больше рабочей границы.
"""
from __future__ import annotations

import logging
import struct
from pathlib import Path

import media

log = logging.getLogger("worker.references")

# Больше этой стороны провайдеру не нужно: image-to-video всё равно работает
# в пределах 1080–1920, а лишние мегапиксели только замедляют загрузку.
MAX_SIDE = 1536

# Ниже этого снимок бесполезен: провайдер вернёт мыло, и никакая настройка
# генерации этого не спасёт.
MIN_USABLE_SIDE = 256

# Порог честного предупреждения (ТЗ §21). Не запрет — человек вправе
# попробовать, но обещать премиум-результат на таком исходнике нельзя.
LOW_QUALITY_SIDE = 720

ALLOWED_MIME: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

# Форматы, которые пересжимать нельзя без причины.
LOSSY_MIME = {"image/jpeg"}


class ReferenceError(Exception):
    """Снимок непригоден: битый файл, чужой формат, слишком маленький."""


# ------------------------------------------------------------------ EXIF --

# Ориентация → цепочка фильтров ffmpeg. Числа — из стандарта EXIF, где 1 это
# «как снято», а 6 и 8 — обычный вертикальный кадр с телефона.
_ORIENTATION_FILTER: dict[int, str] = {
    1: "",
    2: "hflip",
    3: "transpose=1,transpose=1",
    4: "vflip",
    5: "transpose=0",
    6: "transpose=1",
    7: "transpose=3",
    8: "transpose=2",
}


def read_exif_orientation(data: bytes) -> int:
    """Ориентация из EXIF. 1 — если её нет, файл не JPEG или разбор не удался.

    Отсутствие тега — не ошибка: у PNG его не бывает вовсе.
    """
    if not data.startswith(b"\xff\xd8"):
        return 1
    offset = 2
    limit = len(data)
    while offset + 4 <= limit:
        if data[offset] != 0xFF:
            return 1
        marker = data[offset + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            offset += 2
            continue
        if marker == 0xDA:  # начались данные картинки, EXIF дальше не будет
            return 1
        (size,) = struct.unpack(">H", data[offset + 2:offset + 4])
        segment = data[offset + 4:offset + 2 + size]
        if marker == 0xE1 and segment.startswith(b"Exif\x00\x00"):
            return _orientation_from_tiff(segment[6:])
        offset += 2 + size
    return 1


def _orientation_from_tiff(tiff: bytes) -> int:
    try:
        if tiff[:2] == b"II":
            endian = "<"
        elif tiff[:2] == b"MM":
            endian = ">"
        else:
            return 1
        (ifd_offset,) = struct.unpack(endian + "I", tiff[4:8])
        (count,) = struct.unpack(endian + "H", tiff[ifd_offset:ifd_offset + 2])
        for i in range(count):
            entry = ifd_offset + 2 + i * 12
            (tag,) = struct.unpack(endian + "H", tiff[entry:entry + 2])
            if tag == 0x0112:  # Orientation
                (value,) = struct.unpack(endian + "H", tiff[entry + 8:entry + 10])
                return value if value in _ORIENTATION_FILTER else 1
    except (struct.error, IndexError):
        return 1
    return 1


# ------------------------------------------------------------ подготовка --


def quality_note(width: int, height: int) -> str | None:
    """Честное предупреждение о слабом исходнике. None — претензий нет."""
    if min(width, height) < LOW_QUALITY_SIDE:
        return (
            f"Снимок {width}×{height}: это немного. Фотография побольше даст "
            f"заметно более чёткое видео."
        )
    return None


def normalize(src: Path, dest_dir: Path, name: str, mime_type: str) -> dict:
    """Привести снимок к рабочему виду. Вернуть описание результата.

    Ключи ответа: `path`, `width`, `height`, `mime_type`, `rotated`,
    `downscaled`, `recompressed`, `note`.
    """
    if mime_type not in ALLOWED_MIME:
        raise ReferenceError(f"формат {mime_type} не поддерживается")

    data = src.read_bytes()
    if not data:
        raise ReferenceError("пустой файл")

    try:
        width, height = media.image_size(src)
    except RuntimeError as e:
        raise ReferenceError(f"файл не читается как картинка: {e}") from e

    if min(width, height) < MIN_USABLE_SIDE:
        raise ReferenceError(
            f"снимок {width}×{height} слишком мал: минимальная сторона {MIN_USABLE_SIDE} px"
        )

    orientation = read_exif_orientation(data)
    rotate_filter = _ORIENTATION_FILTER.get(orientation, "")
    too_big = max(width, height) > MAX_SIDE

    ext = ALLOWED_MIME[mime_type]
    dest = dest_dir / f"{name}{ext}"

    if not rotate_filter and not too_big:
        # Ничего делать не нужно — и это лучший исход. Пересжатие JPEG ради
        # «единообразия» стоило бы резкости и не дало бы ничего взамен.
        dest.write_bytes(data)
        return {
            "path": dest, "width": width, "height": height, "mime_type": mime_type,
            "rotated": False, "downscaled": False, "recompressed": False,
            "note": quality_note(width, height),
        }

    filters = [f for f in (rotate_filter,) if f]
    if too_big:
        # Вписать в квадрат MAX_SIDE, сохранив пропорции. `decrease` не
        # увеличивает маленькие снимки: растянутый товар хуже мелкого.
        filters.append(
            f"scale=w='min({MAX_SIDE},iw)':h='min({MAX_SIDE},ih)'"
            f":force_original_aspect_ratio=decrease"
        )

    args = ["-i", str(src), "-vf", ",".join(filters), "-frames:v", "1"]
    if mime_type in LOSSY_MIME:
        args += ["-q:v", "2"]  # почти без потерь: пересжатие и так вынужденное
    media.run_ffmpeg([*args, str(dest)])

    new_width, new_height = media.image_size(dest)
    log.info(
        "[REFERENCE] %s: %d×%d → %d×%d%s%s",
        name, width, height, new_width, new_height,
        f", поворот EXIF {orientation}" if rotate_filter else "",
        ", уменьшен" if too_big else "",
    )
    return {
        "path": dest, "width": new_width, "height": new_height, "mime_type": mime_type,
        "rotated": bool(rotate_filter), "downscaled": too_big,
        "recompressed": mime_type in LOSSY_MIME,
        "note": quality_note(new_width, new_height),
    }
