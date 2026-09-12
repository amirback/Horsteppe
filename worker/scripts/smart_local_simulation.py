"""Полный 30-секундный ролик в режиме SMART на локальных клипах.

ТОЛЬКО ДЛЯ РАЗРАБОТКИ. Платных вызовов не делает, продакшен не меняет.

Прошлый шаг доказал, что один настоящий клип доходит до финального файла.
Здесь проверяется весь замысел целиком: планировщик размечает 30-секундный
ролик, шесть кадров из восьми должны получить настоящее видео, два остаться
движением по картинке, а монтаж — собрать это в один файл нужной длины.

Провайдера заменяют локальные mp4. Для конвейера подмена неотличима от
удачного ответа: тот же `video_url`, тот же `generation_mode='real_video'`,
тот же `clip_path` в монтаже. Монтаж настоящий, тот же, что в бою.

Доказательство берётся не из логов, а из перехвата функций монтажа: видно,
какой сегмент собран из клипа, а какой из картинки. Покрытие считается по
фактически использованным ассетам, а не по намерению планировщика.

Запуск:

    worker/.venv/bin/python worker/scripts/smart_local_simulation.py

Режимы переопределяются только внутри процесса — .env остаётся нетронутым.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

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
    "SUBTITLES": "1",
})

import media  # noqa: E402
import pipeline  # noqa: E402
from config import Config  # noqa: E402
from steps import image_step, render_step, script_step, shot_plan, tts_step, video_step  # noqa: E402
from test_pipeline_e2e import FakeDb  # noqa: E402

SIZE = (270, 480)  # ровно 9:16; маленький кадр — проверяем маршрутизацию, не качество
REQUESTED_SEC = 30
OUT_DIR = ROOT / "output" / "smart_simulation"


def make_clip(path: Path, source: str) -> None:
    media.run_ffmpeg([
        "-f", "lavfi", "-i", f"{source}=size={SIZE[0]}x{SIZE[1]}:rate=30:duration=5",
        "-pix_fmt", "yuv420p", str(path),
    ])


def probe(path: Path) -> tuple[float, int, int, bool]:
    proc = subprocess.run(
        [media.ffmpeg_path(), "-hide_banner", "-i", str(path)],
        capture_output=True, text=True,
    )
    text = proc.stderr
    m = re.search(r"Stream #\d+:\d+.*: Video: .*?(\d{2,5})x(\d{2,5})", text)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    has_audio = bool(re.search(r"Stream #\d+:\d+.*: Audio: ", text))
    return media.media_duration_sec(path), w, h, has_audio


def main() -> int:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)

    # Несколько разных клипов: переиспользование одного скрыло бы ошибку
    # «все сегменты собраны из первого файла».
    clips = []
    for i, source in enumerate(("testsrc2", "smptebars", "rgbtestsrc")):
        clip = root / f"clip_{i}.mp4"
        make_clip(clip, source)
        clips.append(clip)

    storage = root / "storage"
    storage.mkdir()
    project_id = str(uuid.uuid4())
    db = FakeDb(storage, {
        "id": project_id, "topic": "основатель запускает стартап ночью",
        "style": "cinematic", "duration_sec": REQUESTED_SEC, "aspect_ratio": "9:16",
        "status": "queued",
    })

    scene_count = script_step._scene_count(REQUESTED_SEC)
    scene_seconds = REQUESTED_SEC / scene_count

    provider_calls: list[str] = []

    def local_provider(cfg, image_url, motion_prompt, out_path):
        """Локальный клип вместо ответа провайдера. Денег не стоит."""
        clip = clips[len(provider_calls) % len(clips)]
        provider_calls.append(clip.name)
        out_path.write_bytes(clip.read_bytes())
        return 0.35  # цена, как у настоящего вызова — для учёта

    def local_image(cfg, prompt, out_path, index=0):
        media.run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c=gray:size={SIZE[0]}x{SIZE[1]}",
            "-frames:v", "1", str(out_path),
        ])
        return 0.0

    def local_tts(cfg, text, out_path):
        """Озвучка нужной длины: длительность ролика идёт ровно за голосом."""
        media.run_ffmpeg([
            "-f", "lavfi", "-i", f"anoisesrc=d={scene_seconds:.3f}:c=pink:a=0.3",
            "-ar", "44100", str(out_path),
        ])
        return 0.0

    video_step.generate_clip = local_provider
    image_step.generate_image = local_image
    tts_step.synthesize = local_tts
    media.FORMATS["9:16"] = SIZE

    # Перехват монтажа: чем на самом деле собран каждый сегмент.
    built_from_clip: list[str] = []
    built_from_image: list[str] = []
    real_clip_segment = media.make_clip_segment
    real_motion_segment = media.make_motion_segment

    def spy_clip(clip, out, duration, size):
        built_from_clip.append(out.name)
        return real_clip_segment(clip, out, duration, size)

    def spy_motion(image, out, duration, size, motion_name=media.DEFAULT_MOTION):
        built_from_image.append(out.name)
        return real_motion_segment(image, out, duration, size, motion_name)

    media.make_clip_segment = render_step.media.make_clip_segment = spy_clip
    media.make_motion_segment = render_step.media.make_motion_segment = spy_motion

    try:
        pipeline.run_project(Config(), db, project_id)
        final_src = Path(db.renders[-1][0].replace("file://", ""))
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        final = OUT_DIR / "smart_30s.mp4"
        final.write_bytes(final_src.read_bytes())
    finally:
        media.make_clip_segment = render_step.media.make_clip_segment = real_clip_segment
        media.make_motion_segment = render_step.media.make_motion_segment = real_motion_segment

    shots = sorted(db.shots, key=lambda s: s["order_index"])

    # Покрытие считаем по фактически использованным ассетам, а не по плану:
    # план — это намерение, а нас интересует, что попало в файл.
    real_sec = sum(float(s["timeline_duration"]) for s in shots if s.get("video_url"))
    image_sec = sum(float(s["timeline_duration"]) for s in shots if not s.get("video_url"))
    total_sec = real_sec + image_sec
    real_shots = [s for s in shots if s.get("video_url")]
    image_shots = [s for s in shots if not s.get("video_url")]

    duration, width, height, has_audio = probe(final)

    print("\n[SMART LOCAL SIMULATION]")
    print(f"\nRequested duration:\n{REQUESTED_SEC} sec")
    print(f"\nTotal shots:\n{len(shots)}")
    print(f"\nREAL_VIDEO shots:\n{len(real_shots)}")
    print(f"\nIMAGE_MOTION shots:\n{len(image_shots)}")
    print(f"\nREAL_VIDEO coverage:\n{100 * real_sec / total_sec:.0f}%")
    print(f"\nIMAGE_MOTION coverage:\n{100 * image_sec / total_sec:.0f}%")
    print(f"\nFinal duration:\n{duration:.2f} sec")

    print("\n=== ОЗВУЧКА ПО СЦЕНАМ ===")
    print(f"  заказано на сцену: {scene_seconds:.2f} с")
    for scene in sorted(db.scenes, key=lambda s: s["order_index"]):
        print(f"    сцена {scene['order_index']}: {scene.get('audio_duration_sec')} с")

    print("\n=== ЧЕМ СОБРАН КАЖДЫЙ СЕГМЕНТ ===")
    print(f"  из клипов провайдера: {len(built_from_clip)} — {built_from_clip}")
    print(f"  из картинок (зум):    {len(built_from_image)} — {built_from_image}")
    print(f"  использованы клипы:   {sorted(set(provider_calls))}")
    print(f"  разрешение: {width}x{height}, звук: {'есть' if has_audio else 'НЕТ'}")

    video_costs = [a for step, _, a in db.costs if step == "video"]
    print(f"  учтено вызовов видео: {len(video_costs)} на ${sum(video_costs):.2f}")

    checks = {
        "кадров примерно восемь": 6 <= len(shots) <= 10,
        "настоящего видео примерно шесть": 5 <= len(real_shots) <= 7,
        "движения по картинке примерно два": 1 <= len(image_shots) <= 3,
        "покрытие настоящим видео 65-85%": 0.65 <= real_sec / total_sec <= 0.85,
        "монтаж собрал клипы, а не пересоздал из картинок":
            len(built_from_clip) == len(real_shots),
        "остальные сегменты собраны из картинок":
            len(built_from_image) == len(image_shots),
        "длительность 28-32 секунды": 28.0 <= duration <= 32.0,
        "видеопоток на месте": width > 0 and height > 0,
        "звук на месте": has_audio,
        "разрешение соответствует формату": (width, height) == SIZE,
        "финальный файл валиден": media.validate_final(final, SIZE)["ok"],
    }

    print("\n=== ПРОВЕРКИ ===")
    for name, ok in checks.items():
        print(f"  [{'v' if ok else 'x'}] {name}")

    print(f"\n  файл: {final}")

    media.FORMATS["9:16"] = (1080, 1920)
    tmp.cleanup()

    ok = all(checks.values())
    print(f"\nPAID API CALLS: 0")
    print(f"STATUS: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
