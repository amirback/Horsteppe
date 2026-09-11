"""Supabase access: queue, project/scene state, storage uploads, cost log."""
from __future__ import annotations

import logging
import mimetypes
from typing import Any

from supabase import Client, create_client

from config import Config

log = logging.getLogger("worker.db")

BUCKET = "media"


class Db:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.client: Client = create_client(cfg.supabase_url, cfg.supabase_service_key)

    # ---------- queue ----------

    def claim_next_job(self) -> dict[str, Any] | None:
        res = self.client.rpc("claim_next_job", {"worker_id": self.cfg.worker_id}).execute()
        rows = res.data or []
        return rows[0] if rows else None

    def requeue_stale_jobs(self) -> int:
        res = self.client.rpc("requeue_stale_jobs", {"stale_minutes": 30}).execute()
        return res.data or 0

    def finish_job(self, job_id: int, status: str, error: str | None = None) -> None:
        self.client.table("jobs").update(
            {"status": status, "last_error": error, "locked_at": None, "locked_by": None}
        ).eq("id", job_id).execute()

    def retry_or_fail_job(self, job: dict[str, Any], error: str) -> str:
        """Returns the resulting job status ('queued' for retry or 'failed')."""
        if job["attempts"] < job["max_attempts"]:
            self.client.table("jobs").update(
                {
                    "status": "queued",
                    "last_error": error,
                    "locked_at": None,
                    "locked_by": None,
                    # small backoff before retry
                    "run_after": "now()",
                }
            ).eq("id", job["id"]).execute()
            return "queued"
        self.finish_job(job["id"], "failed", error)
        return "failed"

    # ---------- projects / scenes ----------

    def get_project(self, project_id: str) -> dict[str, Any]:
        res = self.client.table("projects").select("*").eq("id", project_id).single().execute()
        return res.data

    def update_project(self, project_id: str, **fields: Any) -> None:
        self.client.table("projects").update(fields).eq("id", project_id).execute()

    def set_progress(self, project_id: str, detail: str) -> None:
        log.info("[%s] %s", project_id[:8], detail)
        self.update_project(project_id, status="generating", status_detail=detail)

    def get_scenes(self, project_id: str) -> list[dict[str, Any]]:
        res = (
            self.client.table("scenes")
            .select("*")
            .eq("project_id", project_id)
            .order("order_index")
            .execute()
        )
        return res.data or []

    def insert_scenes(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        res = self.client.table("scenes").insert(rows).execute()
        return res.data

    def update_scene(self, scene_id: str, **fields: Any) -> None:
        self.client.table("scenes").update(fields).eq("id", scene_id).execute()

    # ---------- shots ----------
    # Кадр — единица монтажа внутри сцены. Доступ устроен так же, как у сцен:
    # готовый кадр при повторе пропускается, поэтому провайдерам не платят
    # дважды за то, что уже собрано.

    def get_shots(self, project_id: str) -> list[dict[str, Any]]:
        res = (
            self.client.table("shots")
            .select("*")
            .eq("project_id", project_id)
            .order("order_index")
            .execute()
        )
        return res.data or []

    def insert_shots(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        res = self.client.table("shots").insert(rows).execute()
        return res.data

    def update_shot(self, shot_id: str, **fields: Any) -> None:
        self.client.table("shots").update(fields).eq("id", shot_id).execute()

    def insert_render(self, project_id: str, url: str, duration_sec: float) -> None:
        self.client.table("renders").insert(
            {"project_id": project_id, "final_video_url": url, "duration_sec": round(duration_sec, 3)}
        ).execute()

    # ---------- costs ----------

    def log_cost(self, project_id: str, step: str, provider: str, amount_usd: float, detail: str = "") -> None:
        self.client.table("cost_events").insert(
            {
                "project_id": project_id,
                "step": step,
                "provider": provider,
                "amount_usd": round(amount_usd, 5),
                "detail": detail,
            }
        ).execute()
        # keep the denormalized total on the project fresh
        res = (
            self.client.table("cost_events")
            .select("amount_usd")
            .eq("project_id", project_id)
            .execute()
        )
        total = sum(float(r["amount_usd"]) for r in (res.data or []))
        self.update_project(project_id, cost_usd=round(total, 4))

    # ---------- storage ----------

    def upload(self, path: str, data: bytes, content_type: str | None = None) -> str:
        """Upload bytes to the public media bucket, return the public URL."""
        content_type = content_type or mimetypes.guess_type(path)[0] or "application/octet-stream"
        self.client.storage.from_(BUCKET).upload(
            path, data, {"content-type": content_type, "upsert": "true"}
        )
        return self.client.storage.from_(BUCKET).get_public_url(path)
