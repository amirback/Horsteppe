"""Замок сборщика: второй процесс не должен перехватить задачу.

Почему этот файл важнее, чем кажется. Дважды за одну сессию забытый старый
сборщик перехватывал задачу и делал её по своим настройкам — он прочитал
.env при запуске и о правках не знал. В первый раз пропала финальная
карточка, во второй — всё настоящее видео. Заметить это можно было только
по неправдоподобно быстрой сборке.

До этого файла у механизма не было ни одного теста.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

WORKER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKER))


@pytest.fixture
def lock_file(tmp_path, monkeypatch):
    path = tmp_path / "worker.lock"
    monkeypatch.setenv("WORKER_LOCK_FILE", str(path))
    import importlib

    import main as main_mod

    importlib.reload(main_mod)
    return path, main_mod


def test_lock_is_taken_and_released(lock_file):
    path, main_mod = lock_file
    with main_mod.only_one_worker():
        assert path.exists()
        assert path.read_text().strip() == str(os.getpid())
    assert not path.exists(), "замок должен сниматься при выходе"


def test_second_worker_is_refused(lock_file):
    path, main_mod = lock_file
    with main_mod.only_one_worker():
        with pytest.raises(SystemExit) as exit_info:
            with main_mod.only_one_worker():
                pass
    assert "уже работает" in str(exit_info.value)


def test_refusal_tells_the_human_how_to_clear_it(lock_file):
    """Основатель не программист: сообщение обязано содержать выход."""
    path, main_mod = lock_file
    with main_mod.only_one_worker():
        with pytest.raises(SystemExit) as exit_info:
            with main_mod.only_one_worker():
                pass
    assert f"rm {path}" in str(exit_info.value)


def test_dead_lock_is_reclaimed(lock_file):
    """Замок от упавшего процесса не должен блокировать работу навсегда."""
    path, main_mod = lock_file
    # Номер, которого заведомо нет: os.kill(0) на нём даст ProcessLookupError.
    dead = _unused_pid()
    path.write_text(str(dead))

    with main_mod.only_one_worker():
        assert path.read_text().strip() == str(os.getpid())
    assert not path.exists()


def test_unreadable_lock_is_reclaimed(lock_file):
    """Обрезанный или пустой файл — не повод отказывать в работе."""
    path, main_mod = lock_file
    path.write_text("это не число")
    with main_mod.only_one_worker():
        assert path.read_text().strip() == str(os.getpid())


def test_lock_removed_by_hand_is_not_recreated_on_exit(lock_file):
    """Чужой замок, появившийся пока мы работали, снимать нельзя."""
    path, main_mod = lock_file
    with main_mod.only_one_worker():
        path.write_text("999999")
    assert path.read_text().strip() == "999999", "снят чужой замок"


def test_two_processes_racing_produce_exactly_one_winner(tmp_path):
    """Гонка между проверкой и записью: оба успевали пройти.

    Проверка настоящими процессами, а не мокой: именно здесь прежняя версия
    и ошибалась — между «файла нет» и «пишу файл» помещался второй сборщик.
    """
    path = tmp_path / "race.lock"
    script = textwrap.dedent(f"""
        import os, sys, time
        os.environ["WORKER_LOCK_FILE"] = {str(path)!r}
        sys.path.insert(0, {str(WORKER)!r})
        import main
        try:
            with main.only_one_worker():
                print("ЗАНЯЛ")
                time.sleep(1.5)
        except SystemExit:
            print("ОТКАЗАНО")
    """)
    runner = tmp_path / "runner.py"
    runner.write_text(script, encoding="utf-8")

    procs = [
        subprocess.Popen([sys.executable, str(runner)], stdout=subprocess.PIPE, text=True)
        for _ in range(6)
    ]
    outputs = [p.communicate()[0] for p in procs]
    winners = sum(1 for o in outputs if "ЗАНЯЛ" in o)
    assert winners == 1, f"замок взяли {winners} процессов вместо одного: {outputs}"


def _unused_pid() -> int:
    """Номер процесса, которого точно нет в системе."""
    for candidate in range(999_000, 1_000_000):
        try:
            os.kill(candidate, 0)
        except ProcessLookupError:
            return candidate
        except PermissionError:
            continue
    raise RuntimeError("не нашлось свободного номера процесса")
