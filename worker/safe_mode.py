"""Безопасный режим: единственный выключатель денег и бесплатные заменители.

Зачем модуль существует. Раньше «безопасность» держалась на одном условии
`video_mode == "provider"` в конвейере: оно отключало только премиум-видео,
а озвучка и генерация кадров выполнялись всегда. То есть отладочный прогон
тратил деньги, хотя режим назывался безопасным.

Теперь есть один барьер. `MVP_SAFE_MODE=1` — значение по умолчанию, а не
опция: платный путь включается явным `MVP_SAFE_MODE=0`.

Второе назначение модуля — сделать так, чтобы в безопасном режиме конвейер
не падал, а доходил до конца. Для этого каждому платному шагу есть локальный
заменитель на FFmpeg: кадр-заглушка вместо генерации изображения и тишина
нужной длины вместо озвучки. Ролик собирается целиком и стоит ноль, поэтому
всю цепочку можно проверить до появления ключей провайдеров.

Заменители намеренно выглядят как заглушки. Выдавать их за настоящий
результат нельзя: на кадре написан номер сцены и текст промпта.
"""
from __future__ import annotations

import logging
from pathlib import Path

import media

log = logging.getLogger("worker.safe")

# Та же плотность речи, что и в script_step: по ней оценивается длительность
# сцены, когда настоящей озвучки нет.
WORDS_PER_SEC = 2.3
MIN_PLACEHOLDER_SEC = 1.5

# Фоновые цвета заглушек — из палитры Horsteppe, чтобы отладочный ролик
# нельзя было спутать с чужим тестовым материалом.
PLACEHOLDER_COLORS = ["0x2c5223", "0x93a845", "0x0e2a10", "0x6d8c3e", "0xc3ce6a"]


class PaidCallBlocked(Exception):
    """Платный вызов запрещён текущим режимом."""


def is_paid_allowed(cfg) -> bool:
    """Единственная точка, отвечающая на вопрос «можно ли сейчас тратить деньги».

    Все платные вызовы обязаны спрашивать здесь. Дублировать проверку
    условиями вида `if video_mode == ...` в шагах запрещено — именно так
    и появилась дыра, из-за которой платили в «безопасном» режиме.
    """
    return not cfg.mvp_safe_mode


def is_paid_video_allowed(cfg) -> bool:
    """Имя из CLAUDE.md §1. Премиум-видео дополнительно требует режима provider."""
    return is_paid_allowed(cfg) and cfg.video_mode == "provider"


def require_paid(cfg, what: str) -> None:
    """Бросить исключение, если платный вызов запрещён."""
    if not is_paid_allowed(cfg):
        raise PaidCallBlocked(
            f"{what}: платные вызовы отключены (MVP_SAFE_MODE=1). "
            f"Чтобы разрешить, задайте MVP_SAFE_MODE=0."
        )


# ------------------------------------------------- бесплатные заменители --


def placeholder_image(prompt: str, out_path: Path, size: tuple[int, int], index: int = 0) -> float:
    """Кадр-заглушка вместо генерации изображения. Стоит ноль."""
    w, h = size
    color = PLACEHOLDER_COLORS[index % len(PLACEHOLDER_COLORS)]
    fontsdir, family = media.resolve_font()

    vf = [f"drawbox=x=0:y=0:w={w}:h={h}:color={color}@1:t=fill"]
    if fontsdir and family:
        font_file = _font_file(fontsdir, family)
        common = f"fontfile='{font_file}':fontcolor=0xf7f6e9:box=0"
        vf.append(
            f"drawtext={common}:text='SAFE MODE':fontsize={int(h / 22)}"
            f":x=(w-text_w)/2:y={int(h * 0.36)}"
        )
        # drawtext не переносит строки сам, поэтому промпт режется заранее:
        # иначе длинная тема уезжает за край кадра.
        line_height = int(h / 30)
        for n, line in enumerate(_wrap(prompt, width=30, lines=3)):
            vf.append(
                f"drawtext={common}:text='{_escape_drawtext(line)}':fontsize={int(h / 40)}"
                f":x=(w-text_w)/2:y={int(h * 0.45) + n * line_height}"
            )

    media.run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}",
        "-frames:v", "1", "-vf", ",".join(vf), str(out_path),
    ])
    log.info("safe: кадр-заглушка для сцены %d", index + 1)
    return 0.0


def placeholder_voice(text: str, out_path: Path) -> float:
    """Тишина длиной с предполагаемую озвучку. Стоит ноль.

    Длительность считается по числу слов: так сцены в отладочном ролике
    получают правдоподобный тайминг, и монтаж проверяется по-настоящему.
    """
    words = max(len(text.split()), 1)
    seconds = max(words / WORDS_PER_SEC, MIN_PLACEHOLDER_SEC)
    media.run_ffmpeg([
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", f"{seconds:.3f}", "-c:a", "libmp3lame", "-b:a", "128k", str(out_path),
    ])
    log.info("safe: тишина %.2f с вместо озвучки (%d слов)", seconds, words)
    return 0.0


def _wrap(text: str, width: int, lines: int) -> list[str]:
    """Разбить текст на строки не длиннее `width`, не больше `lines` штук."""
    out: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            out.append(current)
            current = word
            if len(out) == lines:
                break
        else:
            current = candidate
    if current and len(out) < lines:
        out.append(current)
    if len(out) == lines and len(" ".join(out)) < len(text):
        out[-1] = out[-1][: width - 1] + "…"
    return out


def _font_file(fontsdir: Path, family: str) -> str:
    candidate = fontsdir / f"{family}.ttf"
    path = candidate if candidate.exists() else next(iter(sorted(fontsdir.glob("*.ttf"))), candidate)
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "")


def _escape_drawtext(text: str) -> str:
    """Экранирование для drawtext: одинарные кавычки, двоеточия и переносы."""
    return (
        text.replace("\\", "")
        .replace("'", "")
        .replace(":", " ")
        .replace("%", "")
        .replace("\n", " ")
    )
