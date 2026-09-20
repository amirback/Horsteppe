"""Финальный профиль сжатия достаётся ровно одному проходу — последнему.

Почему это важнее, чем выглядит. Финальный профиль сжимает сильнее
промежуточного (crf 20 против 14). Один такой проход — осознанная плата за
вес файла. Два подряд — потеря, за которую никто не голосовал.

Проходов может быть три: склейка, вшивание субтитров, финальная карточка.
Какой из них последний, зависит от заказа: у ролика без озвучки нет
субтитров, у обычного ролика нет карточки бренда. Тест считает вызовы
ffmpeg, а не читает код: перепутанный флаг выглядит совершенно нормально.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import media  # noqa: E402
from steps import render_step  # noqa: E402


@pytest.fixture
def recorded(monkeypatch):
    """Перехватить каждый запуск ffmpeg, не запуская его."""
    calls: list[list[str]] = []
    real = media.run_ffmpeg

    def spy(args, **kwargs):
        calls.append(list(args))
        return real(args, **kwargs)

    monkeypatch.setattr(media, "run_ffmpeg", spy)
    return calls


def _final_video_passes(calls: list[list[str]]) -> list[list[str]]:
    """Вызовы, сжимающие картинку финальным профилем."""
    out = []
    for args in calls:
        if "-crf" not in args:
            continue
        if args[args.index("-crf") + 1] == "20":
            out.append(args)
    return out


def _scene(tmp_path, index: int, with_clip: bool) -> dict:
    audio = tmp_path / f"voice_{index}.m4a"
    media.run_ffmpeg([
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1.2",
        "-c:a", "aac", "-b:a", "128k", str(audio),
    ])
    scene = {
        "audio_path": str(audio),
        "narration": "Тестовая фраза для субтитров.",
        "order_index": index,
    }
    if with_clip:
        clip = tmp_path / f"clip_{index}.mp4"
        media.run_ffmpeg([
            "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=24",
            "-t", "2", "-pix_fmt", "yuv420p", str(clip),
        ])
        scene["clip_path"] = str(clip)
    else:
        still = tmp_path / f"still_{index}.png"
        media.run_ffmpeg([
            "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=1",
            "-frames:v", "1", str(still),
        ])
        scene["image_path"] = str(still)
    return scene


def _render(tmp_path, *, subtitles: bool, end_card: dict | None) -> Path:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    scenes = [_scene(tmp_path, 0, True), _scene(tmp_path, 1, False)]
    return render_step.render_final(
        scenes, work, aspect="9:16", subtitles=subtitles, end_card=end_card,
    )


CARD = {"title": "Войаж", "subtitle": "Кофе рядом", "duration": 1.0}


def test_subtitled_film_with_end_card_compresses_hard_only_once(recorded, tmp_path):
    """Тот самый случай, который был сломан: карточка пересжимала всё заново."""
    out = _render(tmp_path, subtitles=True, end_card=CARD)
    assert out.exists()
    passes = _final_video_passes(recorded)
    assert len(passes) == 1, f"финальных сжатий {len(passes)}, а должно быть одно"


def test_the_last_pass_is_the_one_that_attaches_the_card(recorded, tmp_path):
    _render(tmp_path, subtitles=True, end_card=CARD)
    last = _final_video_passes(recorded)[0]
    assert "concat=n=2:v=1:a=1[v][a]" in " ".join(last), "финальным сжат не тот проход"


def test_film_without_a_card_still_gets_its_final_pass(recorded, tmp_path):
    _render(tmp_path, subtitles=True, end_card=None)
    assert len(_final_video_passes(recorded)) == 1


def test_silent_film_without_subtitles_or_card(recorded, tmp_path):
    """Ни субтитров, ни карточки — финалом становится склейка."""
    _render(tmp_path, subtitles=False, end_card=None)
    assert len(_final_video_passes(recorded)) == 1


def test_silent_film_with_a_card(recorded, tmp_path):
    """Реклама без озвучки: субтитров нет, но карточка есть."""
    _render(tmp_path, subtitles=False, end_card=CARD)
    assert len(_final_video_passes(recorded)) == 1


def test_viewer_gets_a_file_that_starts_playing_before_it_loads(recorded, tmp_path):
    """`+faststart` обязан быть на последнем проходе, иначе браузер ждёт."""
    _render(tmp_path, subtitles=True, end_card=CARD)
    last = _final_video_passes(recorded)[0]
    assert "+faststart" in last
    assert last.count("+faststart") == 1, "флаг продублирован"
