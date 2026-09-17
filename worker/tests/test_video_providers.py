"""Цепочка провайдеров видео.

Ни сети, ни денег: ответы провайдеров подменяются. Проверяется то, из-за
чего платный путь однажды встал целиком — отказ одного провайдера не должен
останавливать проект, когда клип может сделать второй.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config  # noqa: E402
from steps import video_step  # noqa: E402


@pytest.fixture
def cfg(monkeypatch):
    for key, value in {
        "MVP_SAFE_MODE": "0", "VIDEO_MODE": "provider", "SCRIPT_MODE": "mock",
        "ELEVENLABS_API_KEY": "t", "FAL_KEY": "t",
        "SUPABASE_URL": "https://e.co", "SUPABASE_SERVICE_ROLE_KEY": "t",
    }.items():
        monkeypatch.setenv(key, value)
    return Config


def test_default_chain_is_fal(cfg, monkeypatch):
    monkeypatch.delenv("VIDEO_PROVIDER", raising=False)
    assert cfg().video_providers == ["fal"]


def test_chain_is_read_in_order(cfg, monkeypatch):
    monkeypatch.setenv("VIDEO_PROVIDER", "replicate,fal")
    assert cfg().video_providers == ["replicate", "fal"]


def test_unknown_provider_is_ignored_not_crashed(cfg, monkeypatch):
    """Опечатка в настройке не должна ронять весь проект."""
    monkeypatch.setenv("VIDEO_PROVIDER", "runway,replicate")
    assert cfg().video_providers == ["replicate"]


def test_empty_setting_falls_back_to_fal(cfg, monkeypatch):
    monkeypatch.setenv("VIDEO_PROVIDER", "  ")
    assert cfg().video_providers == ["fal"]


def test_second_provider_saves_the_project(cfg, monkeypatch, tmp_path):
    """Заблокированный аккаунт у первого провайдера — не приговор.

    Ровно это и случилось: fal ответил «User is locked», и платный путь
    встал целиком, хотя клип мог сделать кто-то другой.
    """
    monkeypatch.setenv("VIDEO_PROVIDER", "fal,replicate")

    def dead_fal(*a, **kw):
        raise video_step.VideoError("User is locked. Reason: TOP_UP.")

    def working_replicate(cfg_, image_url, prompt, out_path):
        out_path.write_bytes(b"clip")
        return 0.45

    monkeypatch.setattr(video_step, "_via_fal", dead_fal)
    monkeypatch.setattr(video_step, "_via_replicate", working_replicate)

    out = tmp_path / "clip.mp4"
    price = video_step.generate_clip(cfg(), "https://example/i.png", "push in", out)
    assert out.read_bytes() == b"clip"
    assert price == 0.45


def test_all_providers_failing_names_every_reason(cfg, monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PROVIDER", "fal,replicate")

    def dead(*a, **kw):
        raise video_step.VideoError("нет денег")

    monkeypatch.setattr(video_step, "_via_fal", dead)
    monkeypatch.setattr(video_step, "_via_replicate", dead)

    with pytest.raises(video_step.VideoError) as exc:
        video_step.generate_clip(cfg(), "https://example/i.png", "push in", tmp_path / "c.mp4")
    assert "fal" in str(exc.value) and "replicate" in str(exc.value)


def test_replicate_without_a_token_says_so_plainly(cfg, monkeypatch, tmp_path):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    with pytest.raises(video_step.VideoError, match="REPLICATE_API_TOKEN"):
        video_step._via_replicate(cfg(), "https://example/i.png", "push in", tmp_path / "c.mp4")


@pytest.mark.parametrize("output,expected", [
    ("https://x/v.mp4", "https://x/v.mp4"),
    (["https://x/a.mp4", "https://x/b.mp4"], "https://x/b.mp4"),
    ({"video": "https://x/c.mp4"}, "https://x/c.mp4"),
    ({"output": ["https://x/d.mp4"]}, "https://x/d.mp4"),
    (None, None),
    ([], None),
])
def test_output_url_is_found_in_every_shape(output, expected):
    """Модели отдают ссылку то строкой, то списком, то объектом."""
    assert video_step._replicate_output_url(output) == expected
