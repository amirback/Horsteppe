"""Offline test of the ffmpeg render step — no API keys or network needed.

Generates synthetic assets (colored images + spoken-length sine-wave mp3s),
runs render_step in both kenburns and clip modes, and validates the output.

Usage:  worker/.venv/bin/python scripts/test_render.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "worker"))

import media  # noqa: E402
from steps import render_step  # noqa: E402


def gen_image(color: str, out: Path) -> None:
    media.run_ffmpeg(
        ["-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:d=1", "-frames:v", "1", str(out)]
    )


def gen_mp3(freq: int, duration: float, out: Path) -> None:
    media.run_ffmpeg(
        ["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}", "-c:a", "libmp3lame", "-b:a", "128k", str(out)]
    )


def gen_clip(color: str, duration: float, out: Path) -> None:
    """A fake provider clip: NOT 9:16 and NOT matching audio length, on purpose —
    render_step must crop it and pad/trim to the narration duration."""
    media.run_ffmpeg(
        ["-f", "lavfi", "-i", f"color=c={color}:s=1280x720:d={duration}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)]
    )


def main() -> None:
    work = Path(tempfile.mkdtemp(prefix="render_test_"))
    print(f"work dir: {work}")
    try:
        durations = [3.2, 2.5, 4.1]
        colors = ["steelblue", "darkorange", "seagreen"]

        # --- kenburns mode (image + audio) ---
        scenes = []
        for i, (d, c) in enumerate(zip(durations, colors)):
            img, mp3 = work / f"img{i}.png", work / f"a{i}.mp3"
            gen_image(c, img)
            gen_mp3(300 + i * 200, d, mp3)
            real = media.audio_duration_sec(mp3)
            scenes.append({"image_path": img, "audio_path": mp3, "audio_duration": real})
        (work / "kb").mkdir(exist_ok=True)
        out1 = render_step.render_final(scenes, work / "kb", None)
        dur1 = media.media_duration_sec(out1)
        expected = sum(s["audio_duration"] for s in scenes)
        assert abs(dur1 - expected) < 1.0, f"kenburns duration {dur1} vs expected {expected}"
        print(f"OK kenburns: {out1} ({dur1:.2f}s, expected ~{expected:.2f}s)")

        # --- clip mode (short & long provider clips vs narration) ---
        scenes2 = []
        clip_durs = [2.0, 6.0, 3.0]  # shorter, longer, shorter than narration
        for i, (d, c, cd) in enumerate(zip(durations, colors, clip_durs)):
            clip, mp3 = work / f"clip{i}.mp4", work / f"a{i}.mp3"
            gen_clip(c, cd, clip)
            real = media.audio_duration_sec(mp3)
            scenes2.append({"clip_path": clip, "audio_path": mp3, "audio_duration": real})
        (work / "clip").mkdir(exist_ok=True)
        out2 = render_step.render_final(scenes2, work / "clip", None)
        dur2 = media.media_duration_sec(out2)
        assert abs(dur2 - expected) < 1.0, f"clip duration {dur2} vs expected {expected}"
        print(f"OK clip mode: {out2} ({dur2:.2f}s, expected ~{expected:.2f}s)")

        print("ALL RENDER TESTS PASSED")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
