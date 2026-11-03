"""Тесты не выходят в сеть и не видят настоящих ключей. Никогда.

Зачем это здесь, а не в отдельных тестах. Защита от сети стояла в двух файлах
из тридцати, и этого не хватило: шесть тестов сценария подменяли OpenRouter,
но цепочка провайдеров бралась из настоящего worker/.env и начиналась с
Anthropic. Каждый прогон `pytest` отправлял шесть настоящих запросов с
настоящим ключом. Пока ключ не работал, это было незаметно; заработай он —
каждый прогон тестов стоил бы денег, а сами тесты начали бы падать.

Два барьера, потому что каждый в одиночку обходится:

1. **Ключи-пустышки.** До того как config.py прочитает worker/.env, здесь
   задаются безвредные значения для каждого секрета. python-dotenv не
   перезаписывает то, что уже задано, поэтому настоящие ключи в тесты не
   попадают вовсе. Тест, которому нужен ключ, задаёт его сам.
2. **Сеть закрыта физически.** Любое соединение и любой DNS-запрос к чужому
   адресу отказывает сразу. Отказ записывается, и тест, который его вызвал,
   падает — даже если код под тестом проглотил исключение и пошёл дальше
   (так и было: цепочка сценария молча переходила к следующему провайдеру).

Локальные адреса и UNIX-сокеты разрешены: FFmpeg и цикл событий asyncio
пользуются ими, а наружу они не ведут.
"""
from __future__ import annotations

import os
import socket
import sys

import pytest

# Барьер обязан встать раньше, чем config.py прочитает worker/.env. Если
# модуль уже загружен, настоящие ключи в окружении — и тест это заметит.
_CONFIG_WAS_PRELOADED = "config" in sys.modules

# Каждый секрет из worker/.env.example. Значения — заведомо не ключи.
_DUMMY_SECRETS = {
    "SUPABASE_URL": "https://tests.invalid",
    "SUPABASE_SERVICE_ROLE_KEY": "test-not-a-key",
    "ANTHROPIC_API_KEY": "test-not-a-key",
    "OPENROUTER_API_KEY": "test-not-a-key",
    "ELEVENLABS_API_KEY": "test-not-a-key",
    "FAL_KEY": "test-not-a-key",
    "TOGETHER_API_KEY": "test-not-a-key",
    "REPLICATE_API_TOKEN": "test-not-a-key",
    "HF_KEY": "test-not-a-key:test-not-a-secret",
    "HF_API_KEY": "",
    "HF_API_SECRET": "",
}
for _name, _value in _DUMMY_SECRETS.items():
    os.environ[_name] = _value


class NetworkInTests(ConnectionError):
    """Тест попытался выйти в сеть. Наследник ConnectionError — чтобы код
    под тестом видел обычный сетевой сбой, а не что-то экзотическое."""


_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "", None}
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_getaddrinfo = socket.getaddrinfo
_attempts: list[str] = []


def _is_local(host) -> bool:
    return host in _LOCAL_HOSTS or (isinstance(host, str) and host.startswith("127."))


def _refuse(host) -> None:
    _attempts.append(str(host))
    raise NetworkInTests(f"тест попытался выйти в сеть: {host}")


def _guarded_connect(self, address, *args, **kwargs):
    if isinstance(address, tuple) and not _is_local(address[0]):
        _refuse(address[0])
    return _real_connect(self, address, *args, **kwargs)


def _guarded_connect_ex(self, address, *args, **kwargs):
    if isinstance(address, tuple) and not _is_local(address[0]):
        _refuse(address[0])
    return _real_connect_ex(self, address, *args, **kwargs)


def _guarded_getaddrinfo(host, *args, **kwargs):
    if not _is_local(host):
        _refuse(host)
    return _real_getaddrinfo(host, *args, **kwargs)


socket.socket.connect = _guarded_connect
socket.socket.connect_ex = _guarded_connect_ex
socket.getaddrinfo = _guarded_getaddrinfo


class _Attempts:
    """Доступ к журналу попыток для теста, который проверяет сам барьер."""

    config_was_preloaded = _CONFIG_WAS_PRELOADED

    @staticmethod
    def drain() -> list[str]:
        taken = list(_attempts)
        _attempts.clear()
        return taken


@pytest.fixture
def network_attempts() -> type[_Attempts]:
    return _Attempts


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    # Журнал чистится до подготовки теста: попытка из setUpClass достанется
    # первому тесту класса и уронит его, а не пропадёт.
    _attempts.clear()
    yield


@pytest.fixture(autouse=True)
def _fail_on_network_attempt():
    yield
    if _attempts:
        hosts = ", ".join(sorted(set(_attempts)))
        _attempts.clear()
        pytest.fail(
            f"тест попытался выйти в сеть ({hosts}). Подмените провайдера в тесте; "
            "настоящие вызовы в тестах запрещены (CLAUDE.md §1).",
            pytrace=False,
        )
