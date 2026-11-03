"""Один настоящий клип Higgsfield — ручная проверка платного пути.

Зачем отдельный скрипт. Конвейер проверен на подменённом провайдере, а ТЗ V1
требует доказать путь на настоящем: задача создаётся у Higgsfield, её номер
сохраняется, ожидание переживает смерть процесса, клип скачивается и
открывается. Полный ролик заказал бы шесть клипов; здесь — ровно один.

Без запасных провайдеров: цепочка в процессе сужена до Higgsfield, и чужой
клип не выдаётся за его результат. Повторов заказа нет.

Режимы (запуск из каталога worker):

    # сухой прогон — ни одного обращения к провайдеру
    .venv/bin/python scripts/smoke_real_video.py

    # честная ошибка на неверном ключе — бесплатно, задача не создаётся
    .venv/bin/python scripts/smoke_real_video.py --bad-key

    # один платный клип (~$0.09 по счёту, $0.35 по нашему учёту)
    ALLOW_PAID_SMOKE_TEST=1 MVP_SAFE_MODE=0 .venv/bin/python scripts/smoke_real_video.py

    # то же, но процесс «умирает» сразу после постановки задачи...
    ALLOW_PAID_SMOKE_TEST=1 MVP_SAFE_MODE=0 .venv/bin/python scripts/smoke_real_video.py --kill-after-accept
    # ...и второй запуск забирает ту же задачу без нового заказа
    MVP_SAFE_MODE=0 .venv/bin/python scripts/smoke_real_video.py --resume

Картинка — наша собственная с сайта (SMOKE_IMAGE_URL переопределяет): чужих
прав и лиц в ней нет, а база для проверки не нужна.

Номер принятой задачи пишется в output/smoke/last_request.json в тот же миг,
когда Higgsfield её принял. Ключи не печатаются никогда.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ALLOW_FLAG = "ALLOW_PAID_SMOKE_TEST"
OUT_DIR = ROOT / "output" / "smoke"
OUT_PATH = OUT_DIR / "real_video_test.mp4"
JOURNAL = OUT_DIR / "last_request.json"
DEFAULT_IMAGE = "https://horsteppe.vercel.app/og.png"
PROMPT = "slow cinematic camera push-in, soft light drifting across the frame, subtle natural motion"


def _probe(path: Path) -> dict:
    """Что внутри файла — по разбору вывода ffmpeg, без ffprobe в системе."""
    import media

    text = subprocess.run(
        [media.ffmpeg_path(), "-hide_banner", "-i", str(path)], capture_output=True, text=True,
    ).stderr
    video = re.search(r"Stream #\d+:\d+.*?: Video: (\w+).*?(\d{2,5})x(\d{2,5})", text)
    return {
        "bytes": path.stat().st_size,
        "duration_sec": round(media.media_duration_sec(path), 2),
        "codec": video.group(1) if video else None,
        "width": int(video.group(2)) if video else 0,
        "height": int(video.group(3)) if video else 0,
    }


def _report(title: str, rows: dict, ok: bool) -> int:
    print(f"\n{title}")
    for key, value in rows.items():
        print(f"  {key:<16} {value}")
    print(f"\nSTATUS: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def _config(*, paid: bool):
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    # Только Higgsfield: запасной провайдер подменил бы собой то, что проверяем.
    os.environ["VIDEO_PROVIDER"] = "higgsfield"
    if paid:
        os.environ["VIDEO_MODE"] = "provider"
    from config import Config

    return Config()


def _verify(done, started_at: float, mode: str) -> int:
    problems = []
    info = _probe(OUT_PATH) if OUT_PATH.exists() and OUT_PATH.stat().st_size else {}
    if not info:
        problems.append("файл не создан или пуст")
    elif info["duration_sec"] <= 0 or not info["width"]:
        problems.append("в файле нет видеопотока")
    return _report("REAL VIDEO SMOKE TEST — " + mode, {
        "Provider": done.provider,
        "Model": done.model,
        "Request ID": done.request_id,
        "Ledger cost": f"${done.cost_usd:.2f} (по нашему учёту; счёт Higgsfield — в кабинете)",
        "Output": OUT_PATH,
        "Duration": f"{info.get('duration_sec', 0)} с",
        "Resolution": f"{info.get('width', 0)}x{info.get('height', 0)} ({info.get('codec')})",
        "Size": f"{info.get('bytes', 0)} байт",
        "Wall time": f"{time.monotonic() - started_at:.0f} с",
        **({"Problems": "; ".join(problems)} if problems else {}),
    }, not problems)


def bad_key() -> int:
    """Неверный ключ: Higgsfield отказывает на постановке, задача не создаётся."""
    _config(paid=False)  # окружение из .env; настоящий ключ ниже подменяется
    os.environ["HF_KEY"] = "smoke-invalid-id:smoke-invalid-secret"
    os.environ.pop("HF_API_KEY", None)
    os.environ.pop("HF_API_SECRET", None)
    from config import Config
    from steps import video_step

    cfg = Config()
    try:
        video_step._via_higgsfield(cfg, os.environ.get("SMOKE_IMAGE_URL") or DEFAULT_IMAGE, PROMPT,
                                   OUT_DIR / "never_written.mp4")
    except video_step.AcceptedButNotDelivered as e:
        return _report("BAD KEY CHECK", {"Result": f"задача принята с чужим ключом?! {e}"}, False)
    except video_step.VideoError as e:
        honest = "401" in str(e) or "403" in str(e)
        return _report("BAD KEY CHECK", {
            "Error shown": str(e)[:200],
            "Task created": "нет — отказ до постановки, денег не взято",
        }, honest)
    return _report("BAD KEY CHECK", {"Result": "клип выдан с неверным ключом — так быть не может"}, False)


def resume() -> int:
    """Забрать задачу из журнала без нового заказа."""
    if not JOURNAL.exists():
        print(f"  ОСТАНОВЛЕНО: журнала {JOURNAL} нет — продолжать нечего.")
        return 1
    saved = json.loads(JOURNAL.read_text(encoding="utf-8"))
    cfg = _config(paid=True)
    if cfg.mvp_safe_mode:
        print("  ОСТАНОВЛЕНО: MVP_SAFE_MODE включён — к провайдеру не обращаемся.")
        return 1
    from steps import video_step

    request = video_step.ProviderRequest(
        provider=saved["provider"], model=saved["model"], request_id=saved["request_id"],
        status_url=saved.get("status_url") or "", cost_usd=float(saved.get("cost_usd") or 0),
    )
    print(f"=== ПРОДОЛЖЕНИЕ ЗАДАЧИ {request.request_id} (нового заказа нет) ===")
    started_at = time.monotonic()
    try:
        done = video_step.resume_clip(cfg, request, OUT_PATH)
    except video_step.VideoError as e:
        status = getattr(e, "status", "?")
        return _report("REAL VIDEO SMOKE TEST — resume", {
            "Request ID": request.request_id, "Status": status, "Error": str(e)[:300],
            "Retrievable": getattr(e, "retrievable", "?"),
        }, False)
    return _verify(done, started_at, "resume")


def order(kill_after_accept: bool) -> int:
    """Один платный клип. Номер задачи — в журнал в миг принятия."""
    if os.environ.get(ALLOW_FLAG) != "1":
        print(f"  ОСТАНОВЛЕНО: нет разрешения на трату. Запустите с {ALLOW_FLAG}=1 и MVP_SAFE_MODE=0.")
        print("  Платный вызов НЕ выполнялся.")
        return 1
    cfg = _config(paid=True)
    if cfg.mvp_safe_mode:
        print("  ОСТАНОВЛЕНО: MVP_SAFE_MODE включён — платные вызовы запрещены.")
        print("  Платный вызов НЕ выполнялся.")
        return 1
    if not cfg.higgsfield_credential:
        print("  ОСТАНОВЛЕНО: HF_KEY (или HF_API_KEY и HF_API_SECRET) не задан.")
        return 1

    from config import COSTS
    from steps import video_step

    image = os.environ.get("SMOKE_IMAGE_URL") or DEFAULT_IMAGE
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=== ОДИН НАСТОЯЩИЙ КЛИП HIGGSFIELD ===")
    print(f"  модель:         {cfg.higgsfield_video_model}")
    print(f"  длительность:   {video_step.HIGGSFIELD_DURATION} с")
    print(f"  оценка расхода: ${COSTS['higgsfield_video_per_clip']:.2f} по учёту (≈$0.09 по счёту основателя)")
    print(f"  исходный кадр:  {image}")
    print("  ключ:           задан (значение не печатается)")

    def accepted(request) -> bool:
        JOURNAL.write_text(json.dumps({
            "provider": request.provider, "model": request.model, "request_id": request.request_id,
            "status_url": request.status_url, "cost_usd": request.cost_usd,
            "accepted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  задача принята: {request.request_id} → номер записан в {JOURNAL.name}")
        if kill_after_accept:
            print("  --kill-after-accept: процесс завершается, не дождавшись клипа.")
            os._exit(3)
        return False

    def status(request, state: str) -> None:
        print(f"  состояние:      {state}")

    started_at = time.monotonic()
    try:
        with video_step.tracking(on_accepted=accepted, on_status=status):
            done = video_step.generate_clip(cfg, image, PROMPT, OUT_PATH, provider="higgsfield")
    except video_step.VideoError as e:
        return _report("REAL VIDEO SMOKE TEST — order", {
            "Error": str(e)[:300], "Status": getattr(e, "status", "до постановки"),
            "Retrievable": getattr(e, "retrievable", False),
        }, False)
    return _verify(done, started_at, "order")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--resume", action="store_true", help="забрать задачу из журнала без нового заказа")
    parser.add_argument("--kill-after-accept", action="store_true", help="умереть сразу после постановки")
    parser.add_argument("--bad-key", action="store_true", help="бесплатная проверка честной ошибки ключа")
    parser.add_argument("--dry-run", action="store_true", help="ничего не вызывать")
    args = parser.parse_args()

    if args.bad_key:
        return bad_key()
    if args.resume:
        return resume()
    if args.dry_run or os.environ.get(ALLOW_FLAG) != "1":
        print("=== СУХОЙ ПРОГОН: к провайдеру не обращаемся ===")
        print(f"  платный клип: {ALLOW_FLAG}=1 MVP_SAFE_MODE=0 .venv/bin/python scripts/smoke_real_video.py")
        print(f"  журнал задачи: {JOURNAL}")
        return 0
    return order(args.kill_after_accept)


if __name__ == "__main__":
    raise SystemExit(main())
