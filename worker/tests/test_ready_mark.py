"""Метка «снимок готов» должна быть проверяемой, а не обещанием.

Дефект, из-за которого появился файл. Подготовленный снимок помечается
`_ready` в имени, и повторный прогон его пропускает. Метка ставилась и до
того, как появилась обрезка под формат кадра, — поэтому в боевой базе
осталось четыре снимка с меткой готовности и квадратными пропорциями.
Повтор такого проекта молча возвращал потерю 44% ширины.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pipeline  # noqa: E402

VERTICAL = (1080, 1920)


def _row(path: str, width: int | None, height: int | None) -> dict:
    return {"storage_path": path, "width": width, "height": height}


def test_unprepared_photo_is_not_skipped():
    row = _row("projects/x/references/00.jpg", 1216, 1214)
    assert pipeline._already_fitted(row, VERTICAL) is False


def test_photo_prepared_before_the_aspect_fix_is_redone():
    """Тот самый случай из боевой базы: метка есть, пропорции квадратные."""
    row = _row("projects/x/references/00_ready.png", 1216, 1214)
    assert pipeline._already_fitted(row, VERTICAL) is False, (
        "снимок с меткой готовности, но квадратный, обязан быть переобработан"
    )


def test_correctly_fitted_photo_is_skipped():
    """Повторная обрезка стоила бы резкости и не дала бы ничего."""
    row = _row("projects/x/references/00_ready.png", 682, 1214)
    assert pipeline._already_fitted(row, VERTICAL) is True


def test_rounding_to_even_pixels_does_not_force_rework():
    """Обрезка округляет до чётного — третий знак не повод пересжимать."""
    row = _row("projects/x/references/00_ready.png", 1080, 1920)
    assert pipeline._already_fitted(row, VERTICAL) is True


def test_missing_dimensions_mean_redo_not_trust():
    """Судить не по чему — обработать заново: это стоит секунды."""
    row = _row("projects/x/references/00_ready.png", None, None)
    assert pipeline._already_fitted(row, VERTICAL) is False


def test_landscape_project_rejects_a_vertical_ready_photo():
    row = _row("projects/x/references/00_ready.png", 682, 1214)
    assert pipeline._already_fitted(row, (1920, 1080)) is False


def test_without_a_target_aspect_the_mark_is_enough():
    """Старое поведение сохраняется там, где формат не задан."""
    row = _row("projects/x/references/00_ready.png", 1216, 1214)
    assert pipeline._already_fitted(row, None) is True
