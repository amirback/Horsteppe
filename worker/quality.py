"""Инспектор качества: объективные измерения готового ролика.

Слой первый и единственный на сегодня — измеримый: ffmpeg, арифметика, ноль
моделей. Мультимодальный судья (похож ли товар, нет ли лишних пальцев)
появится позже; рисовать его оценку сейчас значило бы показывать выдуманное
число (ТЗ §24: «Do not fake these now»).

Зачем нужен отдельно от `media.validate_final`. Та отвечает на вопрос «файл
не битый»: есть потоки, то разрешение, не чёрный экран. Ролик из четырёх
фотографий с медленным зумом проходит её целиком — и именно он был главной
претензией к продукту. Здесь считается другое: сколько времени в кадре
действительно что-то происходит.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import media

log = logging.getLogger("worker.quality")

# Частота выборки: две точки в секунду. Реже — пропускаем короткие замирания,
# чаще — тратим время на шум сжатия.
SAMPLE_FPS = 2
SAMPLE_SIDE = 32

# Ниже этого порога полусекунда считается почти статичной. Порог подобран по
# замерам: заглушка безопасного режима даёт 0.4–1.2, настоящий кадр с
# движением камеры — 4.4–10.8.
WEAK_MOTION = 1.5
# Ниже этого кадр просто замер: разница на уровне шума кодека.
FROZEN_MOTION = 0.25

# Допустимая неподвижная пауза (ТЗ §4).
MAX_STATIC_HOLD_SEC = 2.5
# Первые секунды решают, досмотрят ли ролик.
OPENING_SEC = 3.0

# Доля почти статичного времени, после которой ролик читается как слайдшоу.
MAX_WEAK_RATIO = 0.35


@dataclass
class Issue:
    """Найденный дефект. `kind` — то, по чему выбирается стратегия починки."""

    kind: str
    severity: str  # "error" — отдавать нельзя; "warning" — записать и жить дальше
    detail: str
    shot_id: str | None = None
    at_sec: float | None = None

    def __str__(self) -> str:
        where = f" на {self.at_sec:.1f} с" if self.at_sec is not None else ""
        return f"{self.kind}{where}: {self.detail}"


@dataclass
class QualityReport:
    ok: bool = True
    duration_sec: float = 0.0
    width: int = 0
    height: int = 0
    has_audio: bool = False
    real_video_coverage: float = 0.0
    weak_motion_ratio: float = 0.0
    opening_motion: float = 0.0
    frozen_sections: list[tuple[float, float]] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def repairable(self) -> list[Issue]:
        """Дефекты, привязанные к конкретному кадру: только их и чинят."""
        return [i for i in self.issues if i.shot_id]

    def summary(self) -> str:
        return (
            f"{self.duration_sec:.1f} с, {self.width}x{self.height}, "
            f"настоящее видео {self.real_video_coverage * 100:.0f}%, "
            f"почти статично  {self.weak_motion_ratio * 100:.0f}%, "
            f"замираний {len(self.frozen_sections)}, замечаний {len(self.issues)}"
        )


def motion_profile(path: Path) -> list[float]:
    """Движение по всему файлу: одна точка на каждые полсекунды.

    Один проход ffmpeg на весь ролик — покадровая выборка кусками была бы
    вдесятеро дороже и ничего бы не добавила.
    """
    proc = subprocess.run(
        [media.ffmpeg_path(), "-v", "error", "-i", str(path),
         "-vf", f"fps={SAMPLE_FPS},scale={SAMPLE_SIDE}:{SAMPLE_SIDE},format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True, timeout=900,
    )
    size = SAMPLE_SIDE * SAMPLE_SIDE
    raw = proc.stdout
    frames = [raw[i * size:(i + 1) * size] for i in range(len(raw) // size)]
    return [
        sum(abs(a - b) for a, b in zip(frames[i], frames[i + 1])) / size
        for i in range(len(frames) - 1)
    ]


def _frozen_runs(profile: list[float], min_sec: float) -> list[tuple[float, float]]:
    """Отрезки, где движения нет дольше `min_sec`."""
    runs: list[tuple[float, float]] = []
    start: int | None = None
    for i, value in enumerate(profile + [WEAK_MOTION * 10]):
        if value < FROZEN_MOTION:
            start = i if start is None else start
            continue
        if start is not None:
            length = (i - start) / SAMPLE_FPS
            if length >= min_sec:
                runs.append((round(start / SAMPLE_FPS, 2), round(length, 2)))
            start = None
    return runs


def _shot_at(shots: list[dict], at_sec: float) -> str | None:
    """Какому кадру принадлежит момент времени."""
    offset = 0.0
    for shot in shots:
        offset += float(shot.get("timeline_duration") or 0)
        if at_sec < offset:
            return shot.get("id")
    return shots[-1].get("id") if shots else None


def inspect(
    path: Path,
    size: tuple[int, int],
    shots: list[dict],
    *,
    requested_sec: float | None = None,
    coverage_target: float = 0.0,
) -> QualityReport:
    """Измерить готовый ролик и собрать список дефектов."""
    base = media.validate_final(path, size)
    report = QualityReport(
        ok=base["ok"],
        duration_sec=float(base.get("duration_sec") or 0),
        width=int(base.get("width") or 0),
        height=int(base.get("height") or 0),
        has_audio=bool(base.get("has_audio")),
    )
    for message in base["errors"]:
        report.issues.append(Issue("BROKEN_FILE", "error", message))
    for message in base["warnings"]:
        report.issues.append(Issue("SUSPICIOUS", "warning", message))
    if not base["ok"]:
        return report

    # --- покрытие настоящим видео ---
    total = sum(float(s.get("timeline_duration") or 0) for s in shots)
    if total > 0:
        real = sum(
            float(s.get("timeline_duration") or 0)
            for s in shots
            if s.get("video_url") and s.get("generation_mode") == "real_video"
        )
        report.real_video_coverage = round(real / total, 4)
    if coverage_target and report.real_video_coverage + 1e-6 < coverage_target:
        report.issues.append(Issue(
            "LOW_COVERAGE", "warning",
            f"настоящее видео закрывает {report.real_video_coverage * 100:.0f}% "
            f"вместо {coverage_target * 100:.0f}%",
        ))

    # --- движение ---
    profile = motion_profile(path)
    if profile:
        weak = sum(1 for v in profile if v < WEAK_MOTION)
        report.weak_motion_ratio = round(weak / len(profile), 4)
        opening = profile[: int(OPENING_SEC * SAMPLE_FPS)]
        report.opening_motion = round(sum(opening) / len(opening), 3) if opening else 0.0

        if report.weak_motion_ratio > MAX_WEAK_RATIO:
            report.issues.append(Issue(
                "SLIDESHOW", "warning",
                f"{report.weak_motion_ratio * 100:.0f}% времени картинка почти неподвижна",
            ))
        if report.opening_motion < WEAK_MOTION:
            report.issues.append(Issue(
                "STATIC_OPENING", "warning",
                f"первые {OPENING_SEC:.0f} с почти без движения — зритель уходит здесь",
                shot_id=_shot_at(shots, 0.0), at_sec=0.0,
            ))

        report.frozen_sections = _frozen_runs(profile, MAX_STATIC_HOLD_SEC)
        for at_sec, length in report.frozen_sections:
            report.issues.append(Issue(
                "FROZEN_VIDEO", "warning",
                f"картинка стоит {length:.1f} с подряд",
                shot_id=_shot_at(shots, at_sec), at_sec=at_sec,
            ))

    # --- длительность ---
    if requested_sec:
        drift = abs(report.duration_sec - requested_sec) / requested_sec
        # Допуск ±20% зафиксирован в CLAUDE.md §8: источник истины —
        # длина голоса, а не заказанные секунды.
        if drift > 0.20:
            report.issues.append(Issue(
                "WRONG_DURATION", "warning",
                f"{report.duration_sec:.1f} с при заказанных {requested_sec:.0f} с",
            ))

    # --- пустые кадры ---
    for shot in shots:
        if not shot.get("image_url") and not shot.get("video_url"):
            report.issues.append(Issue(
                "MISSING_MEDIA", "error", "у кадра нет ни картинки, ни клипа",
                shot_id=shot.get("id"),
            ))
            report.ok = False

    log.info("[QUALITY] %s", report.summary())
    for issue in report.issues:
        log.info("[QUALITY] %s", issue)
    return report
