"""Снимок приводится к формату кадра ДО генерации видео.

Модель «кадр → видео» повторяет пропорции поданной картинки: поля формата у
Kling нет. Квадратное фото товара давало квадратный клип, и монтаж потом
выбрасывал 44% ширины, а остаток растягивал. Платили за пиксели, которых
никто не увидит, и портили те, что оставались.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import media  # noqa: E402
import references  # noqa: E402


def _image(path: Path, w: int, h: int) -> Path:
    media.run_ffmpeg([
        "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate=1", "-frames:v", "1", str(path),
    ])
    return path


def test_square_photo_becomes_vertical(tmp_path):
    """Тот самый случай: фото кружки 1216×1214 при формате 9:16."""
    src = _image(tmp_path / "src.png", 1216, 1214)
    out = references.fit_aspect(src, tmp_path / "fit.png", (1080, 1920), "image/png")
    w, h = media.image_size(out["path"])
    assert abs(w / h - 1080 / 1920) < 0.01, f"получилось {w}x{h}"
    assert out["cropped"] is True


def test_already_correct_photo_is_left_alone(tmp_path):
    """Пересжатие ради единообразия стоило бы резкости и не дало бы ничего."""
    src = _image(tmp_path / "src.png", 1080, 1920)
    out = references.fit_aspect(src, tmp_path / "fit.png", (1080, 1920), "image/png")
    assert out["cropped"] is False
    assert media.image_size(out["path"]) == (1080, 1920)


def test_landscape_project_crops_the_other_way(tmp_path):
    src = _image(tmp_path / "src.png", 1200, 1200)
    out = references.fit_aspect(src, tmp_path / "fit.png", (1920, 1080), "image/png")
    w, h = media.image_size(out["path"])
    assert abs(w / h - 1920 / 1080) < 0.01, f"получилось {w}x{h}"


def test_photo_is_never_enlarged(tmp_path):
    """Растянутый товар хуже мелкого: увеличивать нельзя."""
    src = _image(tmp_path / "src.png", 600, 600)
    out = references.fit_aspect(src, tmp_path / "fit.png", (1080, 1920), "image/png")
    w, h = media.image_size(out["path"])
    assert w <= 600 and h <= 600


def test_fitted_photo_survives_the_renderer_without_losing_the_frame(tmp_path):
    """Главная проверка: после приведения монтаж почти ничего не режет.

    Раньше клип 1440×1436 приходил к кадру 1080×1920 с потерей 44% ширины.
    """
    src = _image(tmp_path / "src.png", 1216, 1214)
    fitted = references.fit_aspect(src, tmp_path / "fit.png", (1080, 1920), "image/png")
    w, h = media.image_size(fitted["path"])

    # Так монтаж вписывает кадр: увеличить до заполнения и обрезать лишнее.
    scale = max(1080 / w, 1920 / h)
    kept_width = 1080 / (w * scale)
    assert kept_width > 0.98, f"монтаж всё ещё режет {(1 - kept_width) * 100:.0f}% ширины"


def test_unfitted_square_photo_would_lose_almost_half(tmp_path):
    """Доказательство обратного: без приведения потеря остаётся огромной."""
    w, h = 1440, 1436
    scale = max(1080 / w, 1920 / h)
    kept_width = 1080 / (w * scale)
    assert kept_width < 0.6, "проверка потеряла смысл — пересчитайте ожидание"
