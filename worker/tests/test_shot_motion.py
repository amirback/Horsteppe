"""Движение камеры на уровне кадра.

Проверяется не вид кода, а сам файл: кадры извлекаются из готового сегмента и
сравниваются между собой. Ни сети, ни провайдеров — только локальный FFmpeg.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import media  # noqa: E402

SIZE = (180, 320)  # маленький кадр: тест должен быть быстрым
DURATION = 2.0
GRID = 32


def _source_image(path: Path) -> Path:
    """Картинка с заметной структурой: на однотонном фоне движение не измерить."""
    media.run_ffmpeg([
        "-f", "lavfi", "-i", f"testsrc=size={SIZE[0] * 3}x{SIZE[1] * 3}:rate=1",
        "-frames:v", "1", str(path),
    ])
    return path


def _frames(video: Path, count: int = 6) -> list[bytes]:
    raw = subprocess.run(
        [media.ffmpeg_path(), "-v", "error", "-i", str(video),
         "-vf", f"fps={count / DURATION},scale={GRID}:{GRID},format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True,
    ).stdout
    n = GRID * GRID
    return [raw[i * n:(i + 1) * n] for i in range(len(raw) // n)]


def _difference(a: bytes, b: bytes) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def _column_mass(frame: bytes) -> tuple[float, float]:
    """Средняя яркость левой и правой половин — по ним видно сдвиг по горизонтали."""
    left = right = 0.0
    for row in range(GRID):
        line = frame[row * GRID:(row + 1) * GRID]
        left += sum(line[: GRID // 2])
        right += sum(line[GRID // 2:])
    return left, right


@pytest.fixture(scope="module")
def image(tmp_path_factory):
    return _source_image(tmp_path_factory.mktemp("src") / "src.png")


@pytest.mark.parametrize("motion", sorted(set(media.MOTIONS) - {"static"}))
def test_every_motion_actually_moves_the_picture(motion, image, tmp_path):
    """Кадр обязан меняться от начала к концу.

    Это главная защита от возврата слайдшоу: движение, которого не видно,
    ничем не лучше неподвижной фотографии.
    """
    out = tmp_path / f"{motion}.mp4"
    media.make_motion_segment(image, out, DURATION, SIZE, motion)
    frames = _frames(out)
    assert len(frames) >= 4, "сегмент не разобрался на кадры"
    assert _difference(frames[0], frames[-1]) > 2.0, f"{motion}: картинка почти не изменилась"


def test_static_motion_is_honestly_static(image, tmp_path):
    """`static` существует как осознанный выбор, а не как поломка."""
    out = tmp_path / "static.mp4"
    media.make_motion_segment(image, out, DURATION, SIZE, "static")
    frames = _frames(out)
    assert _difference(frames[0], frames[-1]) < 1.0


def test_opposite_pans_move_opposite_ways(image, tmp_path):
    """Панорама влево и вправо обязаны отличаться, а не быть одним движением."""
    left, right = tmp_path / "l.mp4", tmp_path / "r.mp4"
    media.make_motion_segment(image, left, DURATION, SIZE, "pan_left")
    media.make_motion_segment(image, right, DURATION, SIZE, "pan_right")
    # Последний кадр панорамы вправо не должен совпасть с панорамой влево.
    assert _difference(_frames(left)[-1], _frames(right)[-1]) > 2.0


def test_push_in_and_pull_out_are_mirror_images(image, tmp_path):
    """Наезд и отъезд — одно движение в разные стороны: концы меняются местами."""
    push, pull = tmp_path / "in.mp4", tmp_path / "out.mp4"
    media.make_motion_segment(image, push, DURATION, SIZE, "push_in")
    media.make_motion_segment(image, pull, DURATION, SIZE, "pull_out")
    a, b = _frames(push), _frames(pull)
    # Начало наезда похоже на конец отъезда сильнее, чем на его начало.
    assert _difference(a[0], b[-1]) < _difference(a[0], b[0])


def test_segment_keeps_the_requested_length_and_frame(image, tmp_path):
    out = tmp_path / "len.mp4"
    media.make_motion_segment(image, out, DURATION, SIZE, "pan_right")
    assert abs(media.media_duration_sec(out) - DURATION) < 0.1
    check = media.validate_final(out, SIZE)
    assert "разрешение" not in " ".join(check["errors"])


def test_unknown_motion_falls_back_instead_of_crashing(image, tmp_path):
    """Опечатка в названии движения не должна ронять весь проект."""
    out = tmp_path / "weird.mp4"
    media.make_motion_segment(image, out, DURATION, SIZE, "barrel_roll")
    assert out.exists() and out.stat().st_size > 0


def test_old_name_still_works(image, tmp_path):
    """Монтаж пока зовёт прежнюю функцию — ломать её нельзя."""
    out = tmp_path / "legacy.mp4"
    media.make_kenburns_segment(image, out, DURATION, SIZE)
    assert _difference(_frames(out)[0], _frames(out)[-1]) > 2.0
