"""Барьер из conftest.py работает: сеть закрыта, а попытка не теряется."""
from __future__ import annotations

import os
import socket

import httpx
import pytest


def test_outbound_connection_is_refused(network_attempts):
    with pytest.raises(ConnectionError):
        socket.create_connection(("api.higgsfield.ai", 443), timeout=1)
    assert network_attempts.drain() == ["api.higgsfield.ai"]


def test_swallowed_attempt_is_still_recorded(network_attempts):
    """Именно так прятались настоящие вызовы: код ловил сбой и шёл дальше."""
    try:
        httpx.get("https://api.anthropic.com/v1/messages", timeout=1)
    except Exception:  # noqa: BLE001 — проглатываем нарочно, как код под тестом
        pass
    assert "api.anthropic.com" in network_attempts.drain()


def test_dummy_keys_are_in_place_before_config_reads_env(network_attempts):
    """Пустышки встали раньше, чем config.py прочитал worker/.env.

    Проверяется порядок, а не итоговые значения: отдельные тесты задают
    свои пустышки поверх, и это нормально. Опасен только случай, когда
    config.py успел загрузить настоящий .env до барьера.
    """
    assert network_attempts.config_was_preloaded is False


def test_dotenv_never_overwrites_what_is_already_set(tmp_path, monkeypatch):
    """На этом стоит первый барьер: настоящий .env не перебивает пустышку."""
    from dotenv import load_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text("HORSTEPPE_GUARD_PROBE=real-value\n", encoding="utf-8")
    monkeypatch.setenv("HORSTEPPE_GUARD_PROBE", "dummy")
    load_dotenv(env_file)
    assert os.environ["HORSTEPPE_GUARD_PROBE"] == "dummy"


def test_local_sockets_stay_allowed():
    """FFmpeg и asyncio пользуются локальными сокетами — их трогать нельзя."""
    a, b = socket.socketpair()
    try:
        a.sendall(b"ok")
        assert b.recv(2) == b"ok"
    finally:
        a.close()
        b.close()
