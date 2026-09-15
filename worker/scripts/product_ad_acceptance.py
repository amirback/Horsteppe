#!/usr/bin/env python
"""Приёмка режимов «фото товара → реклама» и «фото → видео».

По умолчанию — **сухой прогон**: ни одного платного вызова. Скрипт считает
раскадровку настоящим планировщиком, спрашивает настоящий маршрутизатор, какие
модели он выберет, и печатает максимальную цену прогона до того, как она
потрачена (ТЗ §36).

Платный прогон включается двумя явными условиями сразу:

    MVP_SAFE_MODE=0 ALLOW_PAID_VIDEO_TESTS=true python scripts/product_ad_acceptance.py --paid

Одного флага мало намеренно. `MVP_SAFE_MODE=0` может остаться в окружении с
прошлой отладки, и тогда единственной защитой от счёта был бы случай.

Запуск (из каталога worker):
    PYTHONUTF8=1 python scripts/product_ad_acceptance.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402,F401 — подхватывает worker/.env, значения ключей не печатаются
import product_brief  # noqa: E402
import providers  # noqa: E402
from steps import shot_plan  # noqa: E402

# Товар из приёмочного теста A.
BOTTLE = {
    "product_name": "Многоразовая бутылка",
    "product_description": "Стальная бутылка на 700 мл",
    "product_benefits": ["не течёт", "лёгкая"],
    "target_audience": "студенты",
    "ad_goal": "sales",
    "call_to_action": "Закажи на сайте",
}
DURATION_SEC = 30
ASPECT = "9:16"
REFERENCES = ["https://example/ref_0.jpg", "https://example/ref_1.jpg", "https://example/ref_2.jpg"]


def plan_ad() -> list[dict]:
    """Раскадровка рекламы настоящим планировщиком, без сети и без модели."""
    brief = product_brief.ProductBrief.from_project({"brief": BOTTLE}, len(REFERENCES))
    beats = brief.structure(DURATION_SEC)
    per_beat = DURATION_SEC / len(beats)
    scenes = [
        {
            "narration": f"{beat} " * 8,
            "audio_duration_sec": per_beat,
            "image_prompt": f"advertising frame, beat {beat}",
            "shots": [
                {"framing": "hero product shot", "action": beat,
                 "product_required": beat in ("product", "benefit", "second_benefit")},
                {"framing": "detail", "action": beat,
                 "product_required": beat in ("product", "benefit")},
            ],
        }
        for beat in beats
    ]
    plans = shot_plan.plan_film_shots(
        scenes, style="product", requested_sec=DURATION_SEC, references=REFERENCES
    )
    return [shot for scene in plans for shot in scene]


def anthropic_key_state(cfg) -> str:
    """Проверка ключа Anthropic без единого цента.

    Список моделей не тарифицируется, но отвечает на оба вопроса сразу:
    действителен ли ключ и доступна ли ему модель. Проверять ключ настоящей
    генерацией было бы и дороже, и медленнее.
    """
    import httpx

    headers = {"x-api-key": cfg.anthropic_api_key, "anthropic-version": "2023-06-01"}
    if cfg.anthropic_workspace_id:
        headers["anthropic-workspace-id"] = cfg.anthropic_workspace_id
    try:
        r = httpx.get("https://api.anthropic.com/v1/models", headers=headers, timeout=20)
    except Exception as e:  # noqa: BLE001 — диагностика не должна падать
        return f"проверить не удалось: {type(e).__name__}"

    if r.status_code == 200:
        ids = [m["id"] for m in r.json().get("data", [])]
        return ("готов" if cfg.llm_model in ids
                else f"ключ рабочий, но модели {cfg.llm_model} в списке нет")
    if r.status_code == 401:
        return "ключ недействителен"
    message = (r.json().get("error", {}).get("message", "") if r.headers.get("content-type", "").startswith("application/json") else "")
    if "workspace" in message.lower():
        return "ключ организации: нужен ANTHROPIC_WORKSPACE_ID или ключ рабочего пространства"
    return f"отказ {r.status_code}"


def who_writes_the_script() -> None:
    """Кто на самом деле напишет сценарий — видно до запуска, а не из логов.

    Значения ключей не печатаются, только факт их наличия (CLAUDE.md §2).
    """
    from config import Config

    cfg = Config()
    print("СЦЕНАРИЙ")
    print(f"  режим: {cfg.effective_script_mode}"
          + ("  (безопасный режим: шаблон вместо модели)" if cfg.effective_script_mode == "mock" else ""))
    print(f"  цепочка: {', '.join(cfg.script_provider_chain)}")
    author = None
    for provider in cfg.script_provider_chain:
        ready = cfg.has_script_key(provider)
        if not ready:
            mark = "ключа нет"
        elif provider == "anthropic":
            mark = anthropic_key_state(cfg)
            ready = mark == "готов"
        else:
            mark = "готов"
        print(f"    {provider:<11} {cfg.script_model(provider):<28} {mark}")
        if ready and author is None:
            author = (provider, cfg.script_model(provider))
    if author:
        print(f"  писать будет: {author[1]} через {author[0]}")
    else:
        print("  писать некому: ни одного ключа")
    print("  цена сценария: ~$0.04 за ролик на Claude Opus 5"
          " (дешёвая модель обходилась в $0.002)")
    print()


def main() -> int:
    paid_requested = "--paid" in sys.argv
    who_writes_the_script()
    safe_mode_off = os.environ.get("MVP_SAFE_MODE", "1").strip().lower() in ("0", "false", "no", "off")
    opted_in = os.environ.get("ALLOW_PAID_VIDEO_TESTS", "").strip().lower() == "true"
    has_key = bool(os.environ.get("FAL_KEY", "").strip())

    shots = plan_ad()
    wanted = [s for s in shots if shot_plan.preferred_mode(s) == "real_video"]

    print("ПРИЁМКА A — фото товара → готовая реклама")
    print(f"  длительность заказа: {DURATION_SEC} с, формат {ASPECT}")
    print(f"  снимков товара: {len(REFERENCES)}")
    print(f"  кадров в раскадровке: {len(shots)}")
    print(f"  кадров с настоящим снимком товара: {sum(1 for s in shots if s.get('first_frame_reference'))}")
    print(f"  кадров, претендующих на настоящее видео: {len(wanted)}")

    total = 0.0
    print("\n  выбор маршрутизатора по кадрам:")
    for shot in wanted:
        # Цена считается так, как если бы ключи были настроены: сухой прогон
        # обязан назвать сумму и на машине без доступа.
        choice = providers.choose(
            "video",
            importance=float(shot["visual_importance"]),
            needs_image_to_video=True,
            needs_reference=bool(shot.get("first_frame_reference")),
            aspect=ASPECT,
            ignore_keys=True,
        )
        if choice is None:
            print(f"    кадр {shot['order_index'] + 1:>2}: модели нет — {providers.why_not('video', needs_image_to_video=True)}")
            continue
        total += choice.cost_usd
        print(f"    кадр {shot['order_index'] + 1:>2} ({shot['purpose']:<10}) → {choice.model}  ${choice.cost_usd:.2f}")

    print(f"\n  МАКСИМАЛЬНАЯ цена платного прогона: ${total:.2f}")
    print(f"  (плюс сценарий и озвучка — порядка $0.02; кадры бесплатны)")

    print("\nПРИЁМКА B — фотография → настоящее движение")
    clips = max(1, round(10 / 5))
    clip_choice = providers.choose(
        "video", importance=1.0, needs_image_to_video=True, aspect=ASPECT, ignore_keys=True
    )
    clip_cost = clips * (clip_choice.cost_usd if clip_choice else 0.0)
    print(f"  ролик 10 с = {clips} клипа по 5 с → ${clip_cost:.2f}")

    print("\nСОСТОЯНИЕ ДОСТУПА")
    print(f"  FAL_KEY задан: {'да' if has_key else 'НЕТ'}")
    print(f"  MVP_SAFE_MODE=0: {'да' if safe_mode_off else 'нет'}")
    print(f"  ALLOW_PAID_VIDEO_TESTS=true: {'да' if opted_in else 'нет'}")

    if not paid_requested:
        print("\nСухой прогон окончен. Платных вызовов не делалось.")
        print("Свободная проверка обоих режимов без денег:")
        print("  PYTHONUTF8=1 python -m pytest tests/test_product_modes.py -q")
        return 0

    if not (safe_mode_off and opted_in and has_key):
        print("\nПлатный прогон НЕ запущен: нужны все три условия сразу.")
        print(f"  MVP_SAFE_MODE=0 ALLOW_PAID_VIDEO_TESTS=true FAL_KEY=… "
              f"python scripts/product_ad_acceptance.py --paid")
        return 1

    print(f"\nВсе условия выполнены. Прогон спишет до ${total + clip_cost:.2f}.")
    print("Запускать настоящую сборку отсюда скрипт не будет: проект ставится")
    print("через сайт, и приёмка должна идти тем же путём, что у пользователя.")
    print("Создайте проект в интерфейсе и убедитесь, что:")
    print("  1) снимки загрузились и видны в форме;")
    print("  2) на странице проекта доля настоящего движения ≥ 70%;")
    print("  3) товар в кадре узнаваем;")
    print("  4) в cost_events сумма не превышает потолок проекта.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
