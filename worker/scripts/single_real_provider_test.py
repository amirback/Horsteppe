"""Один кадр из восьми идёт к настоящему fal, остальные — локальные подмены.

ТОЛЬКО ДЛЯ РАЗРАБОТКИ. Продакшен не меняет: режимы переопределяются внутри
процесса, .env остаётся нетронутым.

Зачем именно так. Локальная симуляция доказала, что тридцатисекундный ролик
на 75% настоящего видео собирается правильно. Осталось одно неизвестное:
отвечает ли сам fal и переживает ли его ответ монтаж. Полный прогон стоил бы
шесть клипов — $2.10. Здесь платный вызов ровно один: $0.35.

Кадр, идущий к провайдеру, проходит обычным путём — тот же `video_url`, тот
же `generation_mode`, тот же монтаж. Ничего не подставляется после начала
сборки.

Запуск без траты денег (проверка всех неплатных веток):

    worker/.venv/bin/python worker/scripts/single_real_provider_test.py

Запуск с одним настоящим вызовом:

    ALLOW_SINGLE_REAL_PROVIDER_SHOT=1 REAL_PROVIDER_SHOT_ID=0 \\
        worker/.venv/bin/python worker/scripts/single_real_provider_test.py

REAL_PROVIDER_SHOT_ID — это `order_index` кадра, от нуля. Ноль означает
крючок: первый кадр фильма, самый важный.
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

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

ALLOW_FLAG = "ALLOW_SINGLE_REAL_PROVIDER_SHOT"
SHOT_ID_VAR = "REAL_PROVIDER_SHOT_ID"
PAID_ENABLED = os.environ.get(ALLOW_FLAG) == "1"
SELECTED_SHOT = int(os.environ.get(SHOT_ID_VAR, "0"))

# Режимы — только внутри процесса. База подменяется на память: настоящая
# не должна пострадать ни при каком исходе.
os.environ.update({
    "MVP_SAFE_MODE": "0",
    "VIDEO_MODE": "provider",
    "SCRIPT_MODE": "mock",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "local-test",
    "VIDEO_FORMAT": "9:16",
    "TRANSITION_SEC": "0.4",
    "SUBTITLES": "1",
})
os.environ.setdefault("ELEVENLABS_API_KEY", "local-test")
os.environ.setdefault("FAL_KEY", "local-test")

import media  # noqa: E402
import pipeline  # noqa: E402
from config import COSTS, Config  # noqa: E402
from steps import image_step, render_step, script_step, shot_plan, tts_step, video_step  # noqa: E402
from test_pipeline_e2e import FakeDb  # noqa: E402

# Боевой кадр только для платного прогона: платить за уменьшенный незачем,
# а в сухом прогоне маленький кадр экономит минуты.
SIZE = (1080, 1920) if PAID_ENABLED else (270, 480)
REQUESTED_SEC = 30
OUT_DIR = ROOT / "output" / "single_provider"
MAX_PAID_CALLS = 1


class TooManyPaidCalls(RuntimeError):
    """Жёсткий стоп: больше одного платного вызова быть не должно."""


def probe(path: Path) -> tuple[float, int, int, bool]:
    proc = subprocess.run(
        [media.ffmpeg_path(), "-hide_banner", "-i", str(path)],
        capture_output=True, text=True,
    )
    text = proc.stderr
    m = re.search(r"Stream #\d+:\d+.*: Video: .*?(\d{2,5})x(\d{2,5})", text)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    return media.media_duration_sec(path), w, h, bool(re.search(r": Audio: ", text))


def main() -> int:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)

    substitute = root / "substitute.mp4"
    media.run_ffmpeg([
        "-f", "lavfi", "-i", f"testsrc2=size={SIZE[0]}x{SIZE[1]}:rate=30:duration=5",
        "-pix_fmt", "yuv420p", str(substitute),
    ])

    storage = root / "storage"
    storage.mkdir()
    project_id = str(uuid.uuid4())
    db = FakeDb(storage, {
        "id": project_id, "topic": "основатель запускает стартап ночью",
        "style": "cinematic", "duration_sec": REQUESTED_SEC, "aspect_ratio": "9:16",
        "status": "queued",
    })

    cfg = Config()
    scene_seconds = REQUESTED_SEC / script_step._scene_count(REQUESTED_SEC)

    real_provider = video_step.generate_clip  # настоящий, до подмены
    paid_calls: list[int] = []
    local_calls: list[int] = []
    announced = {"done": False}

    def dispatch(cfg_, image_url, motion_prompt, out_path):
        """К настоящему провайдеру идёт ровно один кадр, остальные — подмена."""
        index = len(paid_calls) + len(local_calls)
        if not (PAID_ENABLED and index == SELECTED_SHOT):
            local_calls.append(index)
            out_path.write_bytes(substitute.read_bytes())
            return 0.0

        if len(paid_calls) >= MAX_PAID_CALLS:
            raise TooManyPaidCalls(
                f"попытка платного вызова номер {len(paid_calls) + 1}; разрешён {MAX_PAID_CALLS}"
            )
        if not announced["done"]:
            print("\n[REAL PROVIDER INTEGRATION TEST]")
            print(f"\nSelected shot:\n{index}")
            print(f"\nPurpose:\n{_purpose_of(db, index)}")
            print(f"\nProvider:\nfal.ai")
            print(f"\nModel:\n{cfg.fal_video_model}")
            print(f"\nRequested generation duration:\n5 sec")
            print(f"\nEstimated cost:\n${COSTS['fal_video_per_clip']:.2f}")
            print(f"\nExpected total paid calls: {MAX_PAID_CALLS}\n")
            announced["done"] = True
        paid_calls.append(index)
        return real_provider(cfg_, image_url, motion_prompt, out_path)

    def local_image(cfg_, prompt, out_path, index=0):
        media.run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c=gray:size={SIZE[0]}x{SIZE[1]}",
            "-frames:v", "1", str(out_path),
        ])
        return 0.0

    def local_tts(cfg_, text, out_path):
        media.run_ffmpeg([
            "-f", "lavfi", "-i", f"anoisesrc=d={scene_seconds:.3f}:c=pink:a=0.3",
            "-ar", "44100", str(out_path),
        ])
        return 0.0

    video_step.generate_clip = dispatch
    image_step.generate_image = local_image
    tts_step.synthesize = local_tts
    media.FORMATS["9:16"] = SIZE

    built_from_clip: list[str] = []
    built_from_image: list[str] = []
    keep_clip, keep_motion = media.make_clip_segment, media.make_motion_segment

    def spy_clip(clip, out, duration, size):
        built_from_clip.append(out.name)
        return keep_clip(clip, out, duration, size)

    def spy_motion(image, out, duration, size, motion_name=media.DEFAULT_MOTION):
        built_from_image.append(out.name)
        return keep_motion(image, out, duration, size, motion_name)

    media.make_clip_segment = render_step.media.make_clip_segment = spy_clip
    media.make_motion_segment = render_step.media.make_motion_segment = spy_motion

    print("=== РЕЖИМ ===")
    print(f"  платный вызов разрешён: {'ДА' if PAID_ENABLED else 'нет (сухой прогон)'}")
    print(f"  кадр к провайдеру: {SELECTED_SHOT}")
    print(f"  кадр рендера: {SIZE[0]}x{SIZE[1]}")

    try:
        pipeline.run_project(cfg, db, project_id)
        final_src = Path(db.renders[-1][0].replace("file://", ""))
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        final = OUT_DIR / "single_provider_30s.mp4"
        final.write_bytes(final_src.read_bytes())
    finally:
        media.make_clip_segment = render_step.media.make_clip_segment = keep_clip
        media.make_motion_segment = render_step.media.make_motion_segment = keep_motion
        media.FORMATS["9:16"] = (1080, 1920)

    shots = sorted(db.shots, key=lambda s: s["order_index"])
    real_shots = [s for s in shots if s.get("video_url")]
    duration, width, height, has_audio = probe(final)
    selected = shots[SELECTED_SHOT]
    selected_segment = _segment_name(shots, SELECTED_SHOT)

    print("\n=== РЕЗУЛЬТАТ ===")
    print(f"  кадров: {len(shots)}, с видео: {len(real_shots)}, с картинкой: {len(shots) - len(real_shots)}")
    print(f"  покрытие настоящим видео: {pipeline.real_video_coverage(shots) * 100:.0f}%")
    print(f"  платных вызовов: {len(paid_calls)}   локальных подмен: {len(local_calls)}")
    print(f"  сегмент кадра {SELECTED_SHOT}: {selected_segment}")
    print(f"  собрано из клипов: {len(built_from_clip)}, из картинок: {len(built_from_image)}")
    print(f"  файл: {final}")
    print(f"  {duration:.2f} с, {width}x{height}, звук: {'есть' if has_audio else 'НЕТ'}")

    checks = {
        "платных вызовов не больше одного": len(paid_calls) <= MAX_PAID_CALLS,
        "выбранный кадр помечен настоящим видео": selected.get("generation_mode") == "real_video",
        "сегмент выбранного кадра собран из клипа": selected_segment in built_from_clip,
        "клип не подменён движением по картинке": selected_segment not in built_from_image,
        "длительность 28-32 секунды": 28.0 <= duration <= 32.0,
        "видеопоток на месте": width > 0 and height > 0,
        "звук на месте": has_audio,
        "финальный файл существует и валиден": final.exists() and media.validate_final(final, SIZE)["ok"],
    }
    if PAID_ENABLED:
        checks["сделан ровно один платный вызов"] = len(paid_calls) == MAX_PAID_CALLS

    print("\n=== ПРОВЕРКИ ===")
    for name, ok in checks.items():
        print(f"  [{'v' if ok else 'x'}] {name}")

    tmp.cleanup()
    ok = all(checks.values())
    print(f"\nPAID CALLS MADE: {len(paid_calls)}")
    print(f"STATUS: {'PASS' if ok else 'FAIL'}")
    if not PAID_ENABLED:
        print(f"Сухой прогон: платная ветка не выполнялась. Включить — {ALLOW_FLAG}=1")
    return 0 if ok else 1


def _purpose_of(db, index: int) -> str:
    for shot in db.shots:
        if shot["order_index"] == index:
            return str(shot.get("purpose", "?")).upper()
    return "?"


def _segment_name(shots: list[dict], index: int) -> str:
    """Имя файла сегмента: монтаж нумерует их сценой и местом внутри сцены."""
    target = shots[index]
    same_scene = [s for s in shots if s["scene_id"] == target["scene_id"]]
    scene_order = sorted({s["scene_id"] for s in shots}, key=lambda sid:
                         min(x["order_index"] for x in shots if x["scene_id"] == sid))
    scene_no = scene_order.index(target["scene_id"])
    within = sorted(same_scene, key=lambda s: s["order_index"]).index(target)
    return f"segment_{scene_no:02d}_{within:02d}.mp4"


if __name__ == "__main__":
    raise SystemExit(main())
