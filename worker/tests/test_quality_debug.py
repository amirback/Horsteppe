"""Режим разбора качества: что он сохраняет и чего не сохраняет никогда.

Главная проверка здесь — не про качество, а про секреты. Отладочный режим
пишет на диск тело запроса к платному провайдеру, и файл потом уезжает в
архив или в переписку. Ключ в таком файле — утечка, а не неудобство.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import media  # noqa: E402
import quality_debug  # noqa: E402


@pytest.fixture
def debug_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HORSTEPPE_QUALITY_DEBUG", "1")
    monkeypatch.setenv("HORSTEPPE_DEBUG_DIR", str(tmp_path / "debug"))
    monkeypatch.setenv("HORSTEPPE_DEBUG_STAMP", "test_run")
    return tmp_path / "debug" / "test_run"


def _clip(path: Path, w: int = 640, h: int = 360, seconds: float = 1.0) -> Path:
    media.run_ffmpeg([
        "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate=24",
        "-t", f"{seconds}", "-pix_fmt", "yuv420p", str(path),
    ])
    return path


# ------------------------------------------------------------- секреты --

def test_key_never_reaches_the_file(debug_dir, tmp_path):
    """Даже если провайдер завтра потребует ключ внутри тела запроса."""
    raw = _clip(tmp_path / "shot_01.mp4")
    payload = {
        "prompt": "slow push in",
        "image_url": "https://example.invalid/a.png",
        "api_key": "sk-очень-секретный",
        "nested": {"secret_token": "тоже-секрет", "duration": 5},
    }
    quality_debug.record_clip("shot_01", "higgsfield", "kling/v2.5", payload, raw)

    text = (debug_dir / "shot_01_request_safe.json").read_text(encoding="utf-8")
    assert "sk-очень-секретный" not in text
    assert "тоже-секрет" not in text
    # Но полезное должно остаться — иначе файл бесполезен.
    assert "slow push in" in text
    saved = json.loads(text)
    assert saved["payload"]["nested"]["duration"] == 5
    assert saved["model"] == "kling/v2.5"


def test_redact_leaves_ordinary_data_alone():
    assert quality_debug.redact({"prompt": "тест", "duration": 5}) == {"prompt": "тест", "duration": 5}
    assert quality_debug.redact([{"authorization": "Key abc"}])[0]["authorization"] != "Key abc"


# --------------------------------------------------------------- замеры --

def test_raw_clip_is_measured_and_kept(debug_dir, tmp_path):
    raw = _clip(tmp_path / "shot_02.mp4", 1440, 1436)
    quality_debug.record_clip("shot_02", "higgsfield", "kling/v2.5", {"prompt": "x"}, raw)

    assert (debug_dir / "shot_02_raw.mp4").exists(), "сырой клип должен сохраняться целиком"
    info = json.loads((debug_dir / "shot_02_raw_probe.json").read_text(encoding="utf-8"))
    assert (info["width"], info["height"]) == (1440, 1436)
    assert info["bytes"] > 0


def test_comparison_puts_provider_and_final_side_by_side(debug_dir, tmp_path):
    """Ради этой таблицы режим и существует."""
    quality_debug.record_clip(
        "shot_01", "higgsfield", "kling/v2.5", {"prompt": "x"},
        _clip(tmp_path / "shot_01.mp4", 1440, 1436),
    )
    quality_debug.record_final(_clip(tmp_path / "final.mp4", 1080, 1920))

    table = (debug_dir / "comparison.txt").read_text(encoding="utf-8")
    assert "1440x1436" in table, "нет строки провайдера"
    assert "1080x1920" in table, "нет строки готового ролика"
    assert "ГОТОВЫЙ РОЛИК" in table


# --------------------------------------------------------- выключенный --

def test_disabled_mode_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("HORSTEPPE_QUALITY_DEBUG", raising=False)
    monkeypatch.setenv("HORSTEPPE_DEBUG_DIR", str(tmp_path / "debug"))
    raw = _clip(tmp_path / "shot_01.mp4")

    quality_debug.record_clip("shot_01", "fal", "m", {"prompt": "x"}, raw)
    quality_debug.record_final(raw)

    assert not (tmp_path / "debug").exists(), "выключенный режим не должен создавать каталог"


def test_broken_file_does_not_break_the_build(debug_dir, tmp_path):
    """Отладка не имеет права стоить пользователю заказа."""
    missing = tmp_path / "нет-такого.mp4"
    quality_debug.record_clip("shot_09", "fal", "m", {"prompt": "x"}, missing)  # не должно упасть
    quality_debug.record_final(missing)
