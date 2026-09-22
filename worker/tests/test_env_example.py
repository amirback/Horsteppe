"""Образец настроек не должен отставать от кода.

Зачем это проверять машиной. Файл `.env.example` — единственная инструкция
по настройке, и основатель заполняет систему по нему. На 2026-09-22 в нём не
хватало 43 настроек из 60, включая `HF_KEY` — ключ того сервиса, которым
делается всё видео. Хуже того, он указывал провайдером по умолчанию fal, у
которого аккаунт заблокирован за исчерпанный баланс.

Такой файл не просто неполон — он ведёт настройку по ложному следу, и
заметить это можно только когда ролик уже не собрался.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

WORKER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKER))

# Служебные переменные, которых в образце быть не должно: их задаёт сам код
# или они нужны только для испытаний.
INTERNAL = {
    # Адрес API Higgsfield. Подменяется в тестах, человеку менять незачем.
    "HIGGSFIELD_BASE_URL",
    # Метка прогона для режима разбора качества: её ставит сам код.
    "HORSTEPPE_DEBUG_STAMP",
}

# Переменные, которые читает только тестовое окружение.
TEST_ONLY = {"PYTEST_CURRENT_TEST"}


def _read_by_code() -> set[str]:
    names: set[str] = set()
    files = list(WORKER.glob("*.py")) + list((WORKER / "steps").glob("*.py"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        # `\s*` обязателен: длинные вызовы переносят имя на следующую
        # строку, и без этого четыре настройки выглядели «непрочитанными».
        names |= set(re.findall(r'os\.environ(?:\.get)?[\(\[]\s*"([A-Z][A-Z0-9_]+)"', text))
        names |= set(re.findall(r'_require\("([A-Z][A-Z0-9_]+)"\)', text))
    return names - INTERNAL - TEST_ONLY


def _in_example() -> set[str]:
    text = (WORKER / ".env.example").read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Z][A-Z0-9_]+)=", text, re.M))


def test_every_setting_the_code_reads_is_documented():
    missing = sorted(_read_by_code() - _in_example())
    assert not missing, (
        "в .env.example не описаны настройки, которые читает код: "
        + ", ".join(missing)
    )


def test_the_example_does_not_invent_settings():
    """Настройка, которой нет в коде, — это обещание, которое никто не держит."""
    extra = sorted(_in_example() - _read_by_code() - INTERNAL)
    assert not extra, "в .env.example есть настройки, которых код не читает: " + ", ".join(extra)


def test_the_money_switch_is_safe_by_default():
    text = (WORKER / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^MVP_SAFE_MODE=1$", text, re.M), "выключатель денег обязан быть закрыт"
    assert re.search(r"^VIDEO_MODE=kenburns$", text, re.M), "платное видео не может быть по умолчанию"


def test_no_real_secret_slipped_into_the_example():
    """Образец лежит в репозитории: настоящего ключа в нём быть не может."""
    text = (WORKER / ".env.example").read_text(encoding="utf-8")
    for line in text.splitlines():
        if not re.match(r"^[A-Z][A-Z0-9_]*=", line):
            continue
        name, _, value = line.partition("=")
        if not any(w in name for w in ("KEY", "SECRET", "TOKEN", "PASSWORD")):
            continue
        assert len(value.strip()) <= 12, f"{name} похоже на настоящее значение"


def test_the_default_video_provider_is_one_we_can_actually_pay():
    """Образец указывал fal, у которого аккаунт заблокирован за баланс."""
    text = (WORKER / ".env.example").read_text(encoding="utf-8")
    line = re.search(r"^VIDEO_PROVIDER=(.+)$", text, re.M)
    assert line, "порядок видео-провайдеров не описан"
    assert line.group(1).split(",")[0].strip() == "higgsfield"
