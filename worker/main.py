"""Worker entrypoint: poll the Postgres job queue and run the pipeline.

Usage:
    cd worker && python main.py
"""
from __future__ import annotations

import logging
import time

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


def main() -> None:
    cfg = Config()
    db = Db(cfg)
    log.info(
        "worker %s started (script_mode=%s, video_mode=%s, model=%s)",
        cfg.worker_id, cfg.effective_script_mode, cfg.effective_video_mode, cfg.active_llm_model,
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
    main()
