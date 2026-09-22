"""Деньги записываются в тот миг, когда они потрачены.

Дефект, из-за которого появился файл. Порядок действий был такой: позвать
провайдера, загрузить результат в хранилище, записать трату. Один обрыв
связи на загрузке ронял весь проект — а клипы к тому моменту были уже
оплачены и в журнале не значились. Задача уходила на повтор и платила за те
же кадры второй раз, причём потолок бюджета считал по заниженной цифре.

Проверяется два утверждения:
  1. загрузка переживает короткий обрыв связи;
  2. если не переживает — трата всё равно записана.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db as db_module  # noqa: E402


class FlakyStorage:
    """Хранилище, которое отказывает заданное число раз подряд."""

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.attempts = 0

    def from_(self, bucket):  # noqa: D102 — форма чужого SDK
        return self

    def upload(self, path, data, options):
        self.attempts += 1
        if self.attempts <= self.failures:
            raise ConnectionError("связь оборвалась")

    def get_public_url(self, path):
        return f"https://storage.invalid/{path}"


class FakeClient:
    def __init__(self, storage) -> None:
        self.storage = storage


def _db(storage) -> db_module.Db:
    obj = db_module.Db.__new__(db_module.Db)
    obj.client = FakeClient(storage)
    return obj


@pytest.fixture(autouse=True)
def no_real_waiting(monkeypatch):
    """Паузы между повторами настоящие только в бою."""
    monkeypatch.setattr(db_module.time, "sleep", lambda _s: None)


def test_upload_survives_a_short_outage():
    storage = FlakyStorage(failures=2)
    url = _db(storage).upload("projects/x/clip.mp4", b"data", "video/mp4")
    assert url.endswith("projects/x/clip.mp4")
    assert storage.attempts == 3, "должно было понадобиться три попытки"


def test_upload_gives_up_and_says_why():
    storage = FlakyStorage(failures=99)
    with pytest.raises(RuntimeError) as err:
        _db(storage).upload("projects/x/clip.mp4", b"data", "video/mp4")
    text = str(err.value)
    assert "projects/x/clip.mp4" in text
    assert "связь оборвалась" in text, "причина сбоя должна доходить до человека"
    assert storage.attempts == db_module.UPLOAD_ATTEMPTS


def test_first_try_does_not_wait(monkeypatch):
    """Успешная загрузка не должна ничего стоить по времени."""
    waits = []
    monkeypatch.setattr(db_module.time, "sleep", lambda s: waits.append(s))
    storage = FlakyStorage(failures=0)
    _db(storage).upload("projects/x/a.png", b"data", "image/png")
    assert waits == []


def test_retry_is_safe_to_repeat():
    """Повтор перезаписывает файл, а не плодит копии."""
    seen = {}

    class Recording(FlakyStorage):
        def upload(self, path, data, options):
            seen.update(options)
            super().upload(path, data, options)

    _db(Recording(failures=1)).upload("projects/x/clip.mp4", b"data", "video/mp4")
    assert seen.get("upsert") == "true"


# ------------------------------------------------- порядок учёта денег --

def test_cost_is_recorded_before_the_upload():
    """Главное утверждение: журнал не может отстать от кошелька.

    Читается исходный текст конвейера — проверить порядок иначе значило бы
    поднять весь конвейер ради двух строк.
    """
    source = (Path(__file__).resolve().parents[1] / "pipeline.py").read_text(encoding="utf-8")
    lines = source.splitlines()

    paid_steps = 0
    for i, line in enumerate(lines):
        if "guard.record(" not in line:
            continue
        paid_steps += 1
        # Ближайшая загрузка результата этого шага должна идти ПОСЛЕ записи.
        window = "\n".join(lines[max(0, i - 6):i])
        assert "db.upload(f\"projects/{project_id}/shot" not in window, (
            f"строка {i + 1}: загрузка стоит перед записью траты"
        )
        assert "db.upload(f\"projects/{project_id}/scene" not in window, (
            f"строка {i + 1}: загрузка стоит перед записью траты"
        )

    assert paid_steps >= 4, f"платных шагов найдено {paid_steps}, ожидалось не меньше четырёх"
