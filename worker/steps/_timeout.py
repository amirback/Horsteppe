"""Ограничение времени для блокирующих вызовов сторонних SDK.

Зачем это нужно. `fal_client.subscribe` ждёт завершения задачи на стороне
провайдера и не принимает параметр таймаута: одна зависшая генерация
останавливает воркер целиком. Возврат зависших задач в очередь
(`requeue_stale_jobs`) здесь не помогает — процесс всё равно занят и подберёт
ту же задачу снова.

Решение: вызов уходит в отдельный поток, ожидание ограничивается сверху.

Поток обязан быть демоном. `ThreadPoolExecutor` для этого не годится: его
рабочие потоки не демоны, и интерпретатор присоединяет их при выходе через
внутренний atexit-обработчик — то есть зависший сетевой вызов задержал бы
остановку воркера, даже если вызвать `shutdown(wait=False)`. Это поведение
поймал `tests/test_provider_timeouts.py::test_worker_thread_is_daemon`.

Прервать сам сетевой вызов Python не позволяет, поэтому ограничивается именно
ожидание: воркер освобождается вовремя, а брошенный поток умирает вместе с
процессом. Если провайдер ответит после срабатывания таймаута, результат
отбрасывается.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, TypeVar

log = logging.getLogger("worker.timeout")

T = TypeVar("T")


class CallTimeout(Exception):
    """Внешний вызов не уложился в отведённое время."""


def call_with_timeout(
    func: Callable[..., T],
    *args: object,
    timeout: float,
    label: str,
    **kwargs: object,
) -> T:
    """Выполнить `func` не дольше `timeout` секунд.

    `label` попадает в лог, в имя потока и в текст ошибки — по нему видно,
    какой именно провайдер завис.
    """
    box: dict[str, object] = {}

    def runner() -> None:
        try:
            box["value"] = func(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 — исключение пробрасывается вызывающему
            box["error"] = exc

    thread = threading.Thread(target=runner, name=label, daemon=True)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        log.warning("%s: превышен таймаут %g с, вызов брошен", label, timeout)
        raise CallTimeout(f"{label}: провайдер не ответил за {timeout:g} с")

    error = box.get("error")
    if error is not None:
        raise error  # type: ignore[misc]
    return box["value"]  # type: ignore[return-value]
