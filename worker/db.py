"""Supabase access: queue, project/scene state, storage uploads, cost log."""
from __future__ import annotations

import logging
import mimetypes
import time
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from config import Config

log = logging.getLogger("worker.db")

BUCKET = "media"

# Сколько раз пробовать загрузку и с какой паузой. Три попытки с ростом
# паузы переживают короткий обрыв связи и не превращают сбой хранилища в
# повторную оплату клипов.
UPLOAD_ATTEMPTS = 3
UPLOAD_BACKOFF_SEC = 2.0

# Значения дублируются в проверках миграции 0004; тест стережёт расхождение.
PROJECT_TYPES = ("general_video", "product_ad", "image_to_video")
REFERENCE_VIEW_TYPES = ("front", "side", "detail", "packaging", "lifestyle", "unknown")
# Потолок из ТЗ §7: больше пяти снимков товара не улучшают результат, но
# умножают стоимость подготовки и шанс, что в кадр попадёт чужой ракурс.
MAX_REFERENCES_PER_PROJECT = 5


def is_missing_column(error: Exception) -> bool:
    """Отказ базы из-за колонки, которой ещё нет (миграция не применена).

    PostgREST отвечает кодом PGRST204, сам Postgres — 42703. Различать это с
    прочими сбоями нужно, чтобы новый код работал и до миграции, а настоящая
    ошибка базы не пряталась под тем же предлогом.
    """
    code = getattr(error, "code", None)
    if code in ("PGRST204", "42703"):
        return True
    text = str(getattr(error, "message", None) or error).lower()
    return "column" in text and ("schema cache" in text or "does not exist" in text)


def primary_of(references: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Главный референс из готового списка. Вынесен из класса, чтобы конвейер
    мог выбрать его из уже прочитанных строк, не ходя в базу второй раз."""
    if not references:
        return None
    for ref in references:
        if ref.get("is_primary"):
            return ref
    return min(references, key=lambda r: r.get("order_index", 0))


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
        self.heartbeat(project_id)

    def heartbeat(self, project_id: str) -> None:
        """Освежить замок задачи: она жива, хотя и долгая.

        Брошенной считается задача, чей замок старше 30 минут. Проект с
        несколькими клипами по 3–15 минут легко живёт дольше, и второй
        сборщик забирал живую задачу как брошенную — заказывая те же клипы
        ещё раз. Пульс на каждом шаге держит замок свежим.
        """
        try:
            self.client.table("jobs").update(
                {"locked_at": datetime.now(timezone.utc).isoformat()}
            ).eq("project_id", project_id).eq("status", "processing").execute()
        except Exception as e:  # noqa: BLE001 — пульс не важнее самой работы
            log.warning("[%s] пульс задачи не обновлён: %s", project_id[:8], e)

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

    # ---------- задача у провайдера (миграция 0006) ----------
    # Номер задачи пишется в тот миг, когда провайдер её принял: после этого
    # деньги уже потрачены, и повтор обязан забрать результат, а не заказать
    # клип заново. До миграции колонок нет — тогда сборщик работает как
    # раньше, без запоминания, и говорит об этом в логе один раз.

    _provider_columns = True

    def remember_provider_request(self, shot_id: str, **fields: Any) -> bool:
        """Записать состояние задачи у провайдера. False — колонок ещё нет.

        Поля только из миграции 0006 (provider_request_id, provider_status,
        provider_status_url, provider_submitted_at): если смешать их с
        прежними, отказ из-за новой колонки потерял бы и старые.
        """
        if not self._provider_columns:
            return False
        try:
            self.update_shot(shot_id, **fields)
        except Exception as e:  # noqa: BLE001 — разбор ниже
            if not is_missing_column(e):
                raise
            self._provider_columns = False
            log.warning(
                "миграция 0006 не применена — номер задачи провайдера не сохраняется, "
                "повтор после сбоя закажет клип заново: %s", e,
            )
            return False
        return True

    # ---------- референсы ----------
    # Фотография, которую принёс пользователь: снимок товара или кадр для
    # оживления. Референс принадлежит проекту, а не кадру: одна и та же
    # фотография нужна нескольким кадрам сразу, и дублировать её по кадрам
    # значит разослать провайдеру несколько разных «канонических» видов товара.

    def get_references(self, project_id: str) -> list[dict[str, Any]]:
        res = (
            self.client.table("project_references")
            .select("*")
            .eq("project_id", project_id)
            .order("order_index")
            .execute()
        )
        return res.data or []

    def insert_references(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        res = self.client.table("project_references").insert(rows).execute()
        return res.data

    def update_reference(self, reference_id: str, **fields: Any) -> None:
        self.client.table("project_references").update(fields).eq("id", reference_id).execute()

    def primary_reference(self, project_id: str) -> dict[str, Any] | None:
        """Канонический вид товара — с него начинается режим «фото → видео».

        Явная пометка сильнее порядка: пользователь мог загрузить общий план
        вторым, и именно он — товар лицом. Если пометки нет, каноническим
        считается первый загруженный, а не случайный.
        """
        return primary_of(self.get_references(project_id))


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
        """Положить файл в публичное хранилище и вернуть ссылку.

        Повторы здесь не роскошь. Загрузка стоит между оплаченным клипом и
        записью о его оплате: один обрыв сети ронял весь проект, задача
        уходила на повтор, и провайдеру платили второй раз за те же кадры.

        Повторять безопасно: `upsert` перезаписывает файл, а не плодит копии.
        """
        content_type = content_type or mimetypes.guess_type(path)[0] or "application/octet-stream"
        last: Exception | None = None
        for attempt in range(1, UPLOAD_ATTEMPTS + 1):
            try:
                self.client.storage.from_(BUCKET).upload(
                    path, data, {"content-type": content_type, "upsert": "true"}
                )
                return self.client.storage.from_(BUCKET).get_public_url(path)
            except Exception as e:  # noqa: BLE001 — причина сбоя хранилища не типизирована
                last = e
                if attempt == UPLOAD_ATTEMPTS:
                    break
                pause = UPLOAD_BACKOFF_SEC * attempt
                log.warning(
                    "загрузка %s не удалась (попытка %d из %d), повтор через %.0f с: %s",
                    path, attempt, UPLOAD_ATTEMPTS, pause, e,
                )
                time.sleep(pause)
        raise RuntimeError(f"не удалось загрузить {path} за {UPLOAD_ATTEMPTS} попытки: {last}") from last
