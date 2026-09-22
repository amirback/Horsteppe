"""Worker entrypoint: poll the Postgres job queue and run the pipeline.

Usage:
    cd worker && python main.py
"""
from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path

import pipeline
from config import Config
from db import Db
from steps.script_step import ScriptRefusedError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("worker")


def process_job(cfg: Config, db: Db, job: dict) -> None:
    project_id = job["project_id"]
    log.info("job %s -> project %s (attempt %d/%d)", job["id"], project_id[:8], job["attempts"], job["max_attempts"])
    try:
        pipeline.run_project(cfg, db, project_id)
        db.finish_job(job["id"], "done")
    except ScriptRefusedError as e:
        # Content moderation: retrying won't help — fail immediately with a clear message.
        db.finish_job(job["id"], "failed", str(e))
        db.update_project(project_id, status="failed", error_message=str(e), status_detail=None)
        log.warning("job %s refused: %s", job["id"], e)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        log.exception("job %s failed: %s", job["id"], error)
        status = db.retry_or_fail_job(job, error)
        if status == "failed":
            db.update_project(
                project_id,
                status="failed",
                error_message="Не удалось сгенерировать видео. Попробуйте ещё раз позже.",
                status_detail=None,
            )
        else:
            db.set_progress(project_id, "Повторная попытка…")


LOCK_PATH = Path(os.environ.get("WORKER_LOCK_FILE", "/tmp/horsteppe-worker.lock"))


def _lock_owner() -> int | None:
    """Номер процесса, записанный в замке. None — замок нечитаем."""
    try:
        return int(LOCK_PATH.read_text().strip())
    except (OSError, ValueError):
        return None


def _is_alive(pid: int | None) -> bool:
    """Жив ли процесс. Сигнал 0 ничего не делает, только проверяет."""
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Процесс есть, но принадлежит другому пользователю. Живой.
        return True
    return True


@contextmanager
def only_one_worker():
    """Не дать запуститься второму сборщику на этой машине.

    Дважды за одну сессию забытый старый процесс перехватывал задачу и делал
    её по своим настройкам: он прочитал .env при запуске и о правках не знал.
    В первый раз пропала финальная карточка, во второй — всё настоящее видео,
    и заметить это можно было только по неправдоподобно быстрой сборке.

    Замок создаётся одним неделимым действием (`O_EXCL`), а не проверкой с
    последующей записью: между «файла нет» и «пишу файл» успевали пройти оба
    процесса, и защита от двойного запуска сама себя обходила.

    Мёртвый замок от упавшего процесса не блокирует новый запуск.
    """
    for _ in range(2):
        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            owner = _lock_owner()
            if _is_alive(owner):
                raise SystemExit(
                    f"Сборщик уже работает (процесс {owner}). Закройте старое окно и "
                    "запустите заново — иначе задачу заберёт он, со своими прежними "
                    f"настройками.\n\nЕсли окна нет, а это сообщение осталось:\n"
                    f"    rm {LOCK_PATH}"
                )
            log.info("замок остался от мёртвого процесса %s, забираю", owner)
            try:
                LOCK_PATH.unlink()
            except FileNotFoundError:
                pass  # успел убрать кто-то другой — просто пробуем снова
            continue
        except OSError as e:
            raise SystemExit(f"не удалось создать замок {LOCK_PATH}: {e}") from e
        else:
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
    else:
        raise SystemExit(f"замок {LOCK_PATH} занят и не освобождается — уберите его вручную")

    try:
        yield
    finally:
        # Снимаем только свой замок: чужой мог появиться, пока мы работали,
        # если кто-то удалил наш файл руками.
        try:
            if _lock_owner() == os.getpid():
                LOCK_PATH.unlink()
        except (OSError, FileNotFoundError):
            pass


def main() -> None:
    cfg = Config()
    db = Db(cfg)
    log.info(
        "worker %s started (script_mode=%s, video_mode=%s, video_providers=%s, model=%s)",
        cfg.worker_id, cfg.effective_script_mode, cfg.effective_video_mode,
        ",".join(cfg.video_providers), cfg.active_llm_model,
    )

    started = time.monotonic()
    last_stale_check = 0.0
    while True:
        if cfg.max_runtime_sec and time.monotonic() - started > cfg.max_runtime_sec:
            # Выходим между задачами, а не посреди сборки: недоделанный проект
            # вернётся в очередь целым и его подхватит следующий запуск.
            log.info("отработано %.0f с, выхожу по лимиту времени", cfg.max_runtime_sec)
            break
        try:
            now = time.monotonic()
            if now - last_stale_check > 300:
                requeued = db.requeue_stale_jobs()
                if requeued:
                    log.info("requeued %d stale jobs", requeued)
                last_stale_check = now

            job = db.claim_next_job()
            if job:
                process_job(cfg, db, job)
            else:
                time.sleep(cfg.poll_interval_sec)
        except KeyboardInterrupt:
            log.info("worker stopped")
            break
        except Exception:
            log.exception("worker loop error, sleeping 10s")
            time.sleep(10)


if __name__ == "__main__":
    with only_one_worker():
        main()
