"""Слой базы для надёжной платной генерации — миграция 0006.

Номер задачи провайдера пишется, пока колонки есть, и не роняет сборку, пока
их нет. Пульс держит замок долгой задачи свежим. Сама миграция безопасна для
повторного запуска и не оставляет проект «в работе» навсегда.
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import pytest

WORKER_DIR = Path(__file__).resolve().parents[1]
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import db as db_module  # noqa: E402

MIGRATION = WORKER_DIR.parent / "supabase" / "migrations" / "0006_provider_requests_and_feedback.sql"
WORKER_TEXT = WORKER_DIR.parent / "web" / "app" / "lib" / "worker-text.ts"


class MissingColumn(Exception):
    """Так PostgREST отвечает, когда колонки нет в схеме."""

    code = "PGRST204"
    message = "Could not find the 'provider_request_id' column of 'shots' in the schema cache"


class FakeQuery:
    def __init__(self, client: "FakeClient", table: str) -> None:
        self.client, self.table = client, table
        self.fields: dict | None = None
        self.filters: list[tuple[str, object]] = []

    def update(self, fields: dict) -> "FakeQuery":
        self.fields = fields
        return self

    def eq(self, column: str, value: object) -> "FakeQuery":
        self.filters.append((column, value))
        return self

    def execute(self):
        self.client.calls.append((self.table, self.fields, tuple(self.filters)))
        failure = self.client.failures.get(self.table)
        if failure is not None:
            raise failure
        return type("Result", (), {"data": []})()


class FakeClient:
    def __init__(self, **failures: Exception) -> None:
        self.calls: list[tuple] = []
        self.failures = failures

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)


def make_db(**failures: Exception) -> db_module.Db:
    obj = db_module.Db.__new__(db_module.Db)
    obj.client = FakeClient(**failures)
    return obj


# --- номер задачи ------------------------------------------------------------

def test_request_is_written_to_the_shot():
    db = make_db()
    assert db.remember_provider_request("s1", provider_request_id="r1", provider_status="queued")
    assert db.client.calls == [
        ("shots", {"provider_request_id": "r1", "provider_status": "queued"}, (("id", "s1"),))
    ]


def test_missing_migration_is_tolerated_and_asked_only_once(caplog):
    db = make_db(shots=MissingColumn())
    with caplog.at_level(logging.WARNING, logger="worker.db"):
        assert db.remember_provider_request("s1", provider_request_id="r1") is False
        assert db.remember_provider_request("s2", provider_request_id="r2") is False
    assert len(db.client.calls) == 1, "после первого отказа база больше не спрашивается"
    assert "0006" in caplog.text


def test_real_database_error_is_not_hidden():
    db = make_db(shots=RuntimeError("connection reset by peer"))
    with pytest.raises(RuntimeError):
        db.remember_provider_request("s1", provider_request_id="r1")


@pytest.mark.parametrize("error, expected", [
    (MissingColumn(), True),
    (type("PgError", (Exception,), {"code": "42703"})(), True),
    (RuntimeError("column \"provider_status\" does not exist"), True),
    (RuntimeError("connection reset by peer"), False),
    (type("Other", (Exception,), {"code": "23505"})(), False),
])
def test_missing_column_is_told_apart_from_other_failures(error, expected):
    assert db_module.is_missing_column(error) is expected


# --- пульс -------------------------------------------------------------------

def test_progress_refreshes_the_lock_of_the_running_job():
    db = make_db()
    project = "p" * 36
    db.set_progress(project, "Видео: кадр 2/8")
    assert [call[0] for call in db.client.calls] == ["projects", "jobs"]
    _, fields, filters = db.client.calls[1]
    assert set(fields) == {"locked_at"}
    assert ("project_id", project) in filters
    assert ("status", "processing") in filters, "чужую, уже законченную задачу пульс не трогает"


def test_heartbeat_failure_does_not_break_the_build(caplog):
    db = make_db(jobs=RuntimeError("timeout"))
    with caplog.at_level(logging.WARNING, logger="worker.db"):
        db.set_progress("p" * 36, "Монтаж…")
    assert "пульс" in caplog.text


# --- миграция ----------------------------------------------------------------

def test_migration_is_safe_to_run_twice():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    for column in ("provider_request_id", "provider_status", "provider_status_url", "provider_submitted_at"):
        assert f"add column if not exists {column}" in sql, column
    assert "create table if not exists public.project_feedback" in sql
    assert "create index if not exists" in sql
    assert 'drop policy if exists "project_feedback: select own"' in sql
    assert "drop trigger if exists project_feedback_set_updated_at" in sql


def test_exhausted_stale_job_fails_its_project():
    sql = MIGRATION.read_text(encoding="utf-8")
    function = sql[sql.index("create or replace function public.requeue_stale_jobs"):]
    function = function[: function.index("$$;")]
    assert "update public.projects" in function
    assert "status = 'failed'" in function
    assert "p.status in ('queued', 'generating')" in function, "готовый проект не трогаем"


def test_texts_written_by_the_migration_are_translated_by_the_site():
    """Сайт переводит строки сборщика по точному списку. Строка без перевода
    на английской странице превратилась бы в общий текст."""
    sql = MIGRATION.read_text(encoding="utf-8")
    site = WORKER_TEXT.read_text(encoding="utf-8")
    patterns = [re.compile(m.group(1)) for m in re.finditer(r"re: /(.+?)/,", site)]
    for phrase in ("Не удалось сгенерировать видео. Попробуйте ещё раз позже.", "Повторная попытка…"):
        assert phrase in sql, phrase
        assert any(p.fullmatch(phrase) for p in patterns), f"сайт не переводит: {phrase}"


def test_feedback_reasons_match_between_database_and_site_contract():
    sql = MIGRATION.read_text(encoding="utf-8")
    listed = re.search(r"reasons <@ array\[(.+?)\]::text\[\]", sql, re.S)
    assert listed, "список причин в проверке таблицы не найден"
    reasons = re.findall(r"'([a-z_]+)'", listed.group(1))
    assert reasons == ["off_prompt", "visuals", "motion", "sound", "text", "length", "other"]
