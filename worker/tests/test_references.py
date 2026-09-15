"""Слой данных референсов: фотографии, которые принёс пользователь.

Без сети и без ключей. Клиент Supabase подменяется заглушкой, которая
записывает, к какой таблице и с какими условиями обратился код: так ловится
опечатка в имени таблицы или колонки — то, что иначе всплывает только на
боевой базе.

Отдельная проверка стережёт расхождение между значениями в Python и
ограничениями в миграции 0004: они обязаны совпадать, иначе insert падает в
проде на строке, которая в тестах проходила.

Запуск (из каталога worker):
    PYTHONUTF8=1 python -m pytest tests/test_references.py -q
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from typing import Any

WORKER_DIR = Path(__file__).resolve().parent.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import db as db_module  # noqa: E402
from db import Db, primary_of  # noqa: E402

MIGRATION = WORKER_DIR.parent / "supabase" / "migrations" / "0004_project_references.sql"


class _Result:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeTable:
    """Запоминает построенный запрос вместо того, чтобы его выполнять."""

    def __init__(self, name: str, log: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
        self.call: dict[str, Any] = {"table": name}
        self.rows = rows
        log.append(self.call)

    def select(self, columns: str) -> "FakeTable":
        self.call["select"] = columns
        return self

    def insert(self, rows: list[dict[str, Any]]) -> "FakeTable":
        self.call["insert"] = rows
        return self

    def eq(self, column: str, value: Any) -> "FakeTable":
        self.call.setdefault("eq", []).append((column, value))
        return self

    def order(self, column: str) -> "FakeTable":
        self.call["order"] = column
        return self

    def execute(self) -> _Result:
        return _Result(self.call.get("insert", self.rows))


class FakeClient:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.rows = rows or []

    def table(self, name: str) -> FakeTable:
        return FakeTable(name, self.calls, self.rows)


def make_db(rows: list[dict[str, Any]] | None = None) -> Db:
    """Db без конструктора: настоящий __init__ полез бы в Supabase за сетью."""
    instance = Db.__new__(Db)
    instance.client = FakeClient(rows)  # type: ignore[attr-defined]
    return instance


def ref(order_index: int, primary: bool = False, **extra: Any) -> dict[str, Any]:
    return {"order_index": order_index, "is_primary": primary, **extra}


class TestQueries(unittest.TestCase):
    def test_reads_own_table_filtered_and_ordered(self) -> None:
        database = make_db([ref(0)])
        database.get_references("p-1")
        call = database.client.calls[0]  # type: ignore[attr-defined]
        self.assertEqual(call["table"], "project_references")
        self.assertEqual(call["eq"], [("project_id", "p-1")])
        self.assertEqual(call["order"], "order_index")

    def test_insert_returns_written_rows(self) -> None:
        database = make_db()
        rows = [ref(0, True, project_id="p-1", storage_path="a.jpg")]
        written = database.insert_references(rows)
        self.assertEqual(written, rows)
        self.assertEqual(database.client.calls[0]["table"], "project_references")  # type: ignore[attr-defined]

    def test_empty_table_is_not_an_error(self) -> None:
        database = make_db([])
        self.assertEqual(database.get_references("p-1"), [])
        self.assertIsNone(database.primary_reference("p-1"))


class TestPrimaryChoice(unittest.TestCase):
    """Какой снимок считается каноническим видом товара."""

    def test_explicit_mark_wins_over_order(self) -> None:
        chosen = primary_of([ref(0), ref(1, True), ref(2)])
        self.assertEqual(chosen["order_index"], 1)

    def test_without_mark_falls_back_to_first_uploaded(self) -> None:
        chosen = primary_of([ref(2), ref(0), ref(1)])
        self.assertEqual(chosen["order_index"], 0)

    def test_nothing_uploaded(self) -> None:
        self.assertIsNone(primary_of([]))

    def test_db_method_matches_helper(self) -> None:
        rows = [ref(0), ref(1, True)]
        self.assertEqual(make_db(rows).primary_reference("p-1"), primary_of(rows))


class TestMigrationAgreesWithCode(unittest.TestCase):
    """Значения в Python и ограничения в SQL обязаны совпадать."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")

    def _check_values(self, column: str) -> list[str]:
        match = re.search(rf"{column}\s+in\s*\(([^)]*)\)", self.sql)
        self.assertIsNotNone(match, f"в миграции нет проверки значений для {column}")
        return re.findall(r"'([^']+)'", match.group(1))

    def test_project_types_match(self) -> None:
        self.assertEqual(self._check_values("project_type"), list(db_module.PROJECT_TYPES))

    def test_view_types_match(self) -> None:
        self.assertEqual(self._check_values("view_type"), list(db_module.REFERENCE_VIEW_TYPES))

    def test_default_type_keeps_old_projects_working(self) -> None:
        self.assertIn("default 'general_video'", self.sql)

    def test_single_primary_is_enforced_by_the_database(self) -> None:
        self.assertIn("create unique index project_references_primary_idx", self.sql)
        self.assertIn("where is_primary", self.sql)

    def test_budget_ceiling_cannot_be_negative(self) -> None:
        self.assertIn("max_budget_usd >= 0", self.sql)


if __name__ == "__main__":
    unittest.main()
