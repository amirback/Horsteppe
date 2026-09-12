"""Настоящий клип проходит через конвейер и доживает до финального ролика.

ТОЛЬКО ДЛЯ РАЗРАБОТКИ. Платных вызовов не делает, продакшен не меняет.

Зачем. Платить fal сейчас нечем, а главный вопрос открыт: доходит ли
настоящий движущийся клип до финального файла или монтаж подменяет его зумом
по фотографии. Провайдера здесь заменяет **локальный mp4** — для конвейера это
неотличимо от удачного ответа провайдера: тот же `video_url`, тот же
`generation_mode='real_video'`, тот же `clip_path` в монтаже.

Один кадр получает настоящий клип, остальные остаются движением по картинке —
как и будет в бою при частичном покрытии. Заодно проверяется откат: у
остальных кадров провайдер «отказывает», и они обязаны спокойно уйти в
image_motion, не уронив проект.

Доказательство берётся не из логов, а из перехвата: функции монтажа обёрнуты
счётчиком, и видно, какой кадр собран из клипа, а какой — из картинки.

Запуск:

    worker/.venv/bin/python worker/scripts/local_real_video_check.py [путь-к.mp4]

Без аргумента скрипт сам сделает пятисекундный тестовый клип.
VIDEO_MODE и MVP_SAFE_MODE переопределяются только внутри процесса — файл
.env остаётся нетронутым.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

# Переопределяем режимы ДО импорта конфигурации и только в этом процессе.
os.environ.update({
    "MVP_SAFE_MODE": "0",
    "VIDEO_MODE": "provider",
    "SCRIPT_MODE": "mock",
    "IMAGE_PROVIDER": "pollinations",
    "ELEVENLABS_API_KEY": "local-test",
    "FAL_KEY": "local-test",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "local-test",
    "VIDEO_FORMAT": "9:16",
    "TRANSITION_SEC": "0.4",
    "SUBTITLES": "0",
})

import media  # noqa: E402
import pipeline  # noqa: E402
from config import Config  # noqa: E402
from steps import image_step, render_step, tts_step, video_step  # noqa: E402
from test_pipeline_e2e import FakeDb  # noqa: E402

SIZE = (270, 480)  # маленький кадр: проверяем путь, а не качество
OUT_DIR = ROOT / "output" / "local_real_video"
REAL_VIDEO_SHOT = 0  # какой кадр получит настоящий клип


def make_reference_clip(path: Path) -> None:
    """Пятисекундный клип с заведомо сильным движением."""
    media.run_ffmpeg([
        "-f", "lavfi", "-i", f"testsrc2=size={SIZE[0]}x{SIZE[1]}:rate=30:duration=5",
        "-pix_fmt", "yuv420p", str(path),
    ])


def probe(path: Path) -> tuple[float, int, int]:
    proc = subprocess.run(
        [media.ffmpeg_path(), "-hide_banner", "-i", str(path)],
        capture_output=True, text=True,
    )
    import re
    m = re.search(r"Stream #\d+:\d+.*: Video: .*?(\d{2,5})x(\d{2,5})", proc.stderr)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    return media.media_duration_sec(path), w, h


def motion(path: Path, start: float, length: float) -> float:
    """Средняя разница между соседними кадрами на отрезке."""
    raw = subprocess.run(
        [media.ffmpeg_path(), "-v", "error", "-ss", f"{start:.2f}", "-t", f"{length:.2f}",
         "-i", str(path), "-vf", "fps=4,scale=48:48,format=gray", "-f", "rawvideo", "-"],
        capture_output=True,
    ).stdout
    n = 48 * 48
    frames = [raw[i * n:(i + 1) * n] for i in range(len(raw) // n)]
    if len(frames) < 2:
        return 0.0
    diffs = [
        sum(abs(a - b) for a, b in zip(frames[i], frames[i + 1])) / n
        for i in range(len(frames) - 1)
    ]
    return sum(diffs) / len(diffs)


def main(argv: list[str]) -> int:
    source = Path(argv[1]).resolve() if len(argv) > 1 else None
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)

    if source is None:
        source = root / "reference_clip.mp4"
        make_reference_clip(source)
        print(f"  клип не передан — сделан тестовый: {source.name}")
    if not source.exists():
        print(f"  файла нет: {source}")
        return 1

    clip_duration, clip_w, clip_h = probe(source)
    print("=== ИСХОДНЫЙ КЛИП ===")
    print(f"  {source}")
    print(f"  {clip_duration:.2f} с, {clip_w}x{clip_h}")
    if clip_duration <= 0 or clip_w == 0:
        print("  это не видео — проверка невозможна")
        return 1

    # --- подмены: ничего платного, всё локально -------------------------
    storage = root / "storage"
    storage.mkdir()
    project_id = str(uuid.uuid4())
    db = FakeDb(storage, {
        "id": project_id, "topic": "локальная проверка настоящего видео",
        "style": "cinematic", "duration_sec": 20, "aspect_ratio": "9:16",
        "status": "queued",
    })

    def local_provider(cfg, image_url, motion_prompt, out_path):
        """Отдаёт настоящий клип ровно одному кадру, остальным отказывает."""
        index = len([c for c in provider_calls])
        provider_calls.append(index)
        if index == REAL_VIDEO_SHOT:
            out_path.write_bytes(source.read_bytes())
            return 0.0
        raise video_step.VideoError("локальная проверка: клип только для одного кадра")

    def local_image(cfg, prompt, out_path, index=0):
        media.run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c=gray:size={SIZE[0]}x{SIZE[1]}",
            "-frames:v", "1", str(out_path),
        ])
        return 0.0

    def local_tts(cfg, text, out_path):
        media.run_ffmpeg([
            "-f", "lavfi", "-i", "anoisesrc=d=4:c=pink:a=0.3", "-ar", "44100", str(out_path),
        ])
        return 0.0

    provider_calls: list[int] = []
    video_step.generate_clip = local_provider
    image_step.generate_image = local_image
    tts_step.synthesize = local_tts
    media.FORMATS["9:16"] = SIZE

    # --- перехват монтажа: чем на самом деле собран каждый сегмент -------
    from_clip: list[str] = []
    from_image: list[str] = []
    real_clip_segment, real_motion_segment = media.make_clip_segment, media.make_motion_segment

    def spy_clip(clip, out, duration, size):
        from_clip.append(out.name)
        return real_clip_segment(clip, out, duration, size)

    def spy_motion(image, out, duration, size, motion_name=media.DEFAULT_MOTION):
        from_image.append(out.name)
        return real_motion_segment(image, out, duration, size, motion_name)

    media.make_clip_segment = spy_clip
    media.make_motion_segment = spy_motion
    render_step.media.make_clip_segment = spy_clip
    render_step.media.make_motion_segment = spy_motion

    print("\n=== ПРОГОН КОНВЕЙЕРА ===")
    pipeline.run_project(Config(), db, project_id)

    final_src = Path(db.renders[-1][0].replace("file://", ""))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    final = OUT_DIR / "final.mp4"
    final.write_bytes(final_src.read_bytes())

    # --- разбор результата ---------------------------------------------
    shots = sorted(db.shots, key=lambda s: s["order_index"])
    real = [s for s in shots if s.get("generation_mode") == "real_video"]
    target = shots[REAL_VIDEO_SHOT]
    seg_name = f"segment_00_{REAL_VIDEO_SHOT:02d}.mp4"
    reached = seg_name in from_clip

    dur, w, h = probe(final)
    head = float(target["timeline_duration"])
    motion_real = motion(final, 0.2, max(head - 0.4, 0.5))
    later = shots[-1]
    motion_image = motion(final, max(dur - float(later["timeline_duration"]) + 0.2, 0), 1.5)

    print("\n[LOCAL REAL VIDEO TEST]")
    print(f"Shot: {target['order_index']} ({target['purpose']}, {target['timeline_duration']} с)")
    print("Source: local mp4")
    print(f"Mode: {target.get('generation_mode', '?').upper()}")
    print(f"Reached final timeline: {'YES' if reached else 'NO'}")

    print("\n=== ЧЕМ СОБРАН КАЖДЫЙ СЕГМЕНТ ===")
    print(f"  из клипа провайдера:  {from_clip or '—'}")
    print(f"  из картинки (зум):    {len(from_image)} сегментов")
    print(f"  кадров всего: {len(shots)}, из них настоящее видео: {len(real)}")
    print(f"  покрытие настоящим видео: {pipeline.real_video_coverage(shots) * 100:.0f}%")

    print("\n=== ФИНАЛЬНЫЙ РОЛИК ===")
    print(f"  {final}")
    print(f"  {dur:.2f} с, {w}x{h}")
    print(f"  движение на участке настоящего клипа: {motion_real:.2f}")
    print(f"  движение на участке зума по картинке: {motion_image:.2f}")

    checks = {
        "кадр помечен real_video": target.get("generation_mode") == "real_video",
        "сегмент собран из клипа, а не из картинки": reached,
        "остальные кадры остались движением по картинке": len(from_image) == len(shots) - 1,
        "финальный файл валиден": media.validate_final(final, SIZE)["ok"],
        "клип двигается сильнее зума": motion_real > motion_image * 1.5,
    }
    print("\n=== ПРОВЕРКИ ===")
    for name, ok in checks.items():
        print(f"  [{'v' if ok else 'x'}] {name}")

    media.make_clip_segment, media.make_motion_segment = real_clip_segment, real_motion_segment
    media.FORMATS["9:16"] = (1080, 1920)
    tmp.cleanup()

    print(f"\nSTATUS: {'PASS' if all(checks.values()) else 'FAIL'}")
    print("Платных вызовов: 0")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
