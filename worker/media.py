"""FFmpeg helpers: Ken Burns segments, clip normalization, transitions,
subtitles, concat and music mix.

Uses the static ffmpeg binary bundled with imageio-ffmpeg, so nothing needs
to be installed system-wide. Override with FFMPEG_PATH env var if desired.

Every segment is normalized to the project's frame size, 30 fps and H.264,
so segments can be joined either losslessly (hard cuts) or with xfade
transitions.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path

from mutagen.mp3 import MP3

log = logging.getLogger("worker.media")

FPS = 30

# Поддерживаемые форматы кадра. Ключ приходит из настроек проекта.
FORMATS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}
DEFAULT_FORMAT = "9:16"


def frame_size(aspect: str | None) -> tuple[int, int]:
    return FORMATS.get((aspect or DEFAULT_FORMAT).strip(), FORMATS[DEFAULT_FORMAT])


def ffmpeg_path() -> str:
    override = os.environ.get("FFMPEG_PATH", "").strip()
    if override:
        return override
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(args: list[str], cwd: Path | None = None) -> None:
    cmd = [ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=900, cwd=str(cwd) if cwd else None
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {proc.returncode}): {' '.join(cmd)}\n{proc.stderr[-2000:]}"
        )


def audio_duration_sec(mp3_path: Path) -> float:
    """Fast estimate from the mp3 header — good enough for storing per-scene
    timing, but it overshoots the decoded length by roughly one frame."""
    return float(MP3(mp3_path).info.length)


def exact_duration_sec(path: Path) -> float:
    """Decoded length, accurate to the sample.

    The header estimate runs ~40 ms long per file; across five scenes that is
    enough to visibly desynchronise subtitles from speech, so the render
    timeline is always built from this value.
    """
    try:
        return media_duration_sec(path)
    except Exception:  # noqa: BLE001 — деградируем до оценки, а не падаем
        log.warning("exact duration failed for %s, falling back to header", path)
        return audio_duration_sec(path)


def media_duration_sec(path: Path) -> float:
    """Duration of any media file, parsed from ffmpeg output (no ffprobe needed)."""
    cmd = [ffmpeg_path(), "-hide_banner", "-i", str(path), "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    matches = re.findall(r"time=(\d+):(\d+):(\d+\.?\d*)", proc.stderr)
    if not matches:
        raise RuntimeError(f"Could not determine duration of {path}")
    h, m, s = matches[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


# --------------------------------------------------------------- сегменты --

_ENCODE = [
    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    "-pix_fmt", "yuv420p",
]


def make_kenburns_segment(
    image: Path, out: Path, duration: float, size: tuple[int, int]
) -> None:
    """Animate a still image with a slow zoom for `duration` seconds.

    Video only — audio is assembled separately so that transitions never cut
    into the narration. Costs nothing: this is the local, no-provider path.
    """
    w, h = size
    frames = max(int(round(duration * FPS)), FPS)
    # Upscale 2x before zoompan to avoid the jitter zoompan produces at 1x.
    vf = (
        f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,"
        f"crop={w * 2}:{h * 2},"
        f"zoompan=z='min(1+0.0008*on,1.25)'"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={w}x{h}:fps={FPS},"
        f"format=yuv420p"
    )
    run_ffmpeg(
        ["-loop", "1", "-i", str(image), "-vf", vf, "-t", f"{duration:.3f}",
         *_ENCODE, "-an", str(out)]
    )


def make_clip_segment(
    clip: Path, out: Path, duration: float, size: tuple[int, int]
) -> None:
    """Normalize a provider-generated clip to the target frame and fit it to
    `duration`: if the clip is shorter, freeze the last frame; if longer, trim.

    Freezing reads as a deliberate hold; looping reads as a glitch.
    """
    w, h = size
    clip_dur = media_duration_sec(clip)
    pad = max(duration - clip_dur, 0) + 0.5  # headroom; -t trims precisely
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"fps={FPS},"
        f"tpad=stop_mode=clone:stop_duration={pad:.3f},"
        f"format=yuv420p"
    )
    run_ffmpeg(
        ["-i", str(clip), "-vf", vf, "-t", f"{duration:.3f}", *_ENCODE, "-an", str(out)]
    )


# ------------------------------------------------------------- соединение --


def concat_segments(segments: list[Path], out: Path) -> None:
    """Join segments with hard cuts, without re-encoding."""
    list_file = out.with_suffix(".txt")
    q = chr(39)
    lines = [f"file {q}{str(p.resolve()).replace(q, q + chr(92) + q + q)}{q}" for p in segments]
    list_file.write_text("\n".join(lines), encoding="utf-8")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out)])
    list_file.unlink(missing_ok=True)


def concat_with_transitions(
    segments: list[Path], out: Path, scene_durations: list[float], transition: float
) -> None:
    """Join segments with crossfades.

    Each segment except the last was rendered `transition` seconds longer than
    its narration, so the overlap consumes exactly that tail and the final
    duration still equals the sum of the narration lengths — the video never
    drifts away from the voice track.
    """
    if len(segments) == 1:
        run_ffmpeg(["-i", str(segments[0]), "-c", "copy", str(out)])
        return

    inputs: list[str] = []
    for seg in segments:
        inputs += ["-i", str(seg)]

    steps: list[str] = []
    label = "0:v"
    offset = 0.0
    for i in range(len(segments) - 1):
        offset += scene_durations[i]
        nxt = f"v{i}"
        steps.append(
            f"[{label}][{i + 1}:v]xfade=transition=fade"
            f":duration={transition:.3f}:offset={offset:.3f}[{nxt}]"
        )
        label = nxt

    run_ffmpeg(
        [*inputs, "-filter_complex", ";".join(steps), "-map", f"[{label}]",
         *_ENCODE, "-an", str(out)]
    )


def concat_audio(audio_files: list[Path], out: Path) -> None:
    """Join narration files back to back — never crossfaded, so no word is cut."""
    inputs: list[str] = []
    for a in audio_files:
        inputs += ["-i", str(a)]
    n = len(audio_files)
    filt = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
    run_ffmpeg(
        [*inputs, "-filter_complex", filt, "-map", "[a]",
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(out)]
    )


def mux(video: Path, audio: Path, out: Path, duration: float | None = None) -> None:
    """Combine picture and voice.

    `duration` is passed explicitly instead of relying on -shortest: copying a
    video stream stops at the last whole frame, which silently clipped the tail
    of the final phrase.
    """
    trim = ["-t", f"{duration:.3f}"] if duration else ["-shortest"]
    run_ffmpeg(
        ["-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
         *trim, str(out)]
    )


def mix_music(video: Path, music: Path, out: Path, music_volume: float = 0.15) -> None:
    """Overlay looping background music under the voice-over."""
    run_ffmpeg(
        ["-i", str(video), "-stream_loop", "-1", "-i", str(music),
         "-filter_complex",
         f"[1:a]volume={music_volume}[m];"
         f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]",
         "-map", "0:v:0", "-map", "[a]", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-shortest", str(out)]
    )


# -------------------------------------------------------------- субтитры --

# Короткие строки читаются на телефоне; длинные — нет.
MAX_CHARS_PER_CUE = 38
MAX_WORDS_PER_CUE = 7


def _chunk(text: str) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    cur: list[str] = []
    for w in words:
        candidate = " ".join(cur + [w])
        if cur and (len(candidate) > MAX_CHARS_PER_CUE or len(cur) >= MAX_WORDS_PER_CUE):
            chunks.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        chunks.append(" ".join(cur))
    return chunks or [text.strip()]


def _ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _cues(scenes: list[dict]) -> list[tuple[float, float, str]]:
    """Split narration into short phrases and time them inside each scene,
    proportionally to how much text each phrase carries."""
    cues: list[tuple[float, float, str]] = []
    clock = 0.0
    for scene in scenes:
        text = (scene.get("narration") or "").strip()
        duration = float(scene["audio_duration"])
        if not text:
            clock += duration
            continue
        chunks = _chunk(text)
        weights = [max(len(c), 1) for c in chunks]
        total = sum(weights)
        start = clock
        for chunk, weight in zip(chunks, weights):
            span = duration * weight / total
            cues.append((start, start + span, chunk))
            start += span
        clock += duration
    return cues


def build_srt(scenes: list[dict]) -> str:
    """Subtitles as .srt — the file the user can download and re-use."""
    lines: list[str] = []
    for i, (start, end, text) in enumerate(_cues(scenes), start=1):
        lines += [str(i), f"{_ts(start)} --> {_ts(end)}", text, ""]
    return "\n".join(lines)


def _ass_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _ass_text(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def build_ass(scenes: list[dict], size: tuple[int, int], family: str | None) -> str:
    """Build burn-in subtitles as ASS.

    SRT is burned through libass, which lays the script out in its own
    coordinate space — by default 384x288 — and then scales it to the video.
    Font sizes and margins written in pixels therefore came out roughly seven
    times too large and the caption landed off the top of a 1080x1920 frame.
    Declaring PlayResX/PlayResY equal to the real frame removes the scaling
    entirely: every number below is in actual pixels.
    """
    w, h = size
    portrait = h >= w
    font_size = int(h / 26) if portrait else int(h / 22)
    margin_v = int(h * (0.13 if portrait else 0.08))
    margin_h = int(w * 0.08)
    outline = max(round(font_size * 0.055), 2)
    font = family or "Arial"

    head = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {w}",
        f"PlayResY: {h}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour,"
        " BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle,"
        " BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Main,{font},{font_size},&H00FFFFFF,&H000000FF,&H00181818,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,{outline},0,2,{margin_h},{margin_h},{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    events: list[str] = []
    for start, end, text in _cues(scenes):
        events.append(
            f"Dialogue: 0,{_ass_ts(start)},{_ass_ts(end)},Main,,0,0,0,,{_ass_text(text)}"
        )
    return "\n".join(head + events) + "\n"


_FONT_CANDIDATES = [
    # Сначала шрифт, положенный рядом с воркером — единственный вариант,
    # который гарантированно переживёт переезд в контейнер.
    Path(__file__).parent / "assets" / "fonts",
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/noto"),
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
]


def resolve_font() -> tuple[Path | None, str | None]:
    """Find a font directory that contains a face with Cyrillic coverage.

    Returns (fontsdir, family). Both may be None — then libass falls back to
    fontconfig, which in a slim container usually means empty boxes instead of
    text. That is exactly why SUBTITLE_FONT_FILE exists.
    """
    override = os.environ.get("SUBTITLE_FONT_FILE", "").strip()
    if override:
        p = Path(override)
        if p.exists():
            return p.parent, p.stem
        log.warning("SUBTITLE_FONT_FILE points to a missing file: %s", override)

    preferred = ["DejaVuSans.ttf", "NotoSans-Regular.ttf", "Arial Unicode.ttf", "Arial.ttf"]
    for directory in _FONT_CANDIDATES:
        if not directory.is_dir():
            continue
        for name in preferred:
            if (directory / name).exists():
                return directory, Path(name).stem
        for f in sorted(directory.glob("*.ttf")):
            return directory, f.stem
    log.warning("No bundled subtitle font found — relying on system fontconfig")
    return None, None


def burn_subtitles(video: Path, ass: Path, out: Path) -> None:
    """Burn the ASS subtitles into the picture.

    The subtitle path is passed as a bare filename with cwd set to its
    directory: ffmpeg filter arguments treat ':' and '\\' as syntax, and
    Windows paths are full of both.
    """
    fontsdir, _ = resolve_font()
    subs = f"ass={ass.name}"
    if fontsdir:
        subs += f":fontsdir='{fontsdir}'"
    run_ffmpeg(
        ["-i", str(video.resolve()), "-vf", subs, *_ENCODE, "-c:a", "copy", str(out.resolve())],
        cwd=ass.parent,
    )
