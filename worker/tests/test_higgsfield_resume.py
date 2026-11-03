"""Принятая задача Higgsfield не теряется и не оплачивается дважды.

Сеть подменена. Проверяется то, что ТЗ V1 требует от Phase 1: номер задачи
сообщается до ожидания, сбой связи посреди ожидания не бросает оплаченную
задачу, после принятия кадр не уходит соседу, а результат прошлой задачи
можно забрать без нового заказа.
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import safe_mode  # noqa: E402
from config import Config  # noqa: E402
from steps import video_step  # noqa: E402

STARTED = {"request_id": "r1", "status": "queued",
           "status_url": "https://hf/requests/r1/status",
           "cancel_url": "https://hf/requests/r1/cancel"}
DONE = {"request_id": "r1", "status": "completed", "video": {"url": "https://hf/clip.mp4"}}


class Reply:
    def __init__(self, payload=None, status_code=200, content=b"", text=None):
        self._payload, self.status_code, self.content = payload, status_code, content
        self.text = text if text is not None else str(payload)

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class Http:
    """Подделка httpx.Client. Исключение в списке ответов — сбой связи."""

    def __init__(self, posts=(), gets=()):
        self.posts, self.gets = list(posts), list(gets)
        self.seen_posts: list[str] = []
        self.seen_gets: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, **kw):
        self.seen_posts.append(url)
        return self.posts.pop(0)

    def get(self, url, **kw):
        self.seen_gets.append(url)
        item = self.gets.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def cfg(monkeypatch):
    for key in ("HF_API_KEY", "HF_API_SECRET", "REPLICATE_API_TOKEN", "HIGGSFIELD_VIDEO_MODEL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "MVP_SAFE_MODE": "0", "VIDEO_MODE": "provider", "SCRIPT_MODE": "mock",
        "VIDEO_PROVIDER": "higgsfield,fal", "HF_KEY": "id:secret-not-real",
        "ELEVENLABS_API_KEY": "t", "FAL_KEY": "t",
        "SUPABASE_URL": "https://e.co", "SUPABASE_SERVICE_ROLE_KEY": "t",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(video_step, "HIGGSFIELD_POLL_SEC", 0)
    import time as _time
    monkeypatch.setattr(_time, "sleep", lambda s: None)
    return Config


def use(monkeypatch, http: Http) -> Http:
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)
    return http


# --- задача принята -----------------------------------------------------------

def test_accepted_task_is_reported_before_waiting(cfg, monkeypatch, tmp_path):
    http = use(monkeypatch, Http(posts=[Reply(STARTED)], gets=[Reply(DONE), Reply(content=b"clip")]))
    seen = []

    def accepted(request):
        seen.append((request.request_id, request.status_url, len(http.seen_gets)))
        return True

    with video_step.tracking(on_accepted=accepted):
        done = video_step.generate_clip(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")

    assert seen == [("r1", "https://hf/requests/r1/status", 0)], "номер сообщён до первого опроса"
    assert done.recorded is True and done.request_id == "r1"


def test_without_tracking_the_pipeline_records_as_before(cfg, monkeypatch, tmp_path):
    use(monkeypatch, Http(posts=[Reply(STARTED)], gets=[Reply(DONE), Reply(content=b"clip")]))
    done = video_step.generate_clip(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")
    assert done.recorded is False


def test_handler_failure_does_not_lose_the_paid_clip(cfg, monkeypatch, tmp_path):
    use(monkeypatch, Http(posts=[Reply(STARTED)], gets=[Reply(DONE), Reply(content=b"clip")]))

    def broken(request):
        raise RuntimeError("database is down")

    out = tmp_path / "c.mp4"
    with video_step.tracking(on_accepted=broken):
        done = video_step.generate_clip(cfg(), "https://img/p.png", "push in", out)
    assert out.read_bytes() == b"clip"
    assert done.recorded is False, "трату тогда запишет конвейер, как раньше"


def test_status_changes_are_reported(cfg, monkeypatch, tmp_path):
    running = {**STARTED, "status": "in_progress"}
    use(monkeypatch, Http(posts=[Reply(STARTED)],
                          gets=[Reply(running), Reply(running), Reply(DONE), Reply(content=b"clip")]))
    states = []
    with video_step.tracking(on_status=lambda request, state: states.append(state)):
        video_step.generate_clip(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")
    assert states == ["in_progress", "completed"]


# --- сбои посреди ожидания ----------------------------------------------------

def test_network_blip_while_waiting_does_not_reorder(cfg, monkeypatch, tmp_path):
    """Обрыв, 503 и страница анти-бота посреди ожидания — повод подождать, а не заказать снова."""
    http = use(monkeypatch, Http(
        posts=[Reply(STARTED)],
        gets=[httpx.ConnectError("reset"), Reply({"detail": "busy"}, status_code=503),
              Reply(None, text="<html>captcha</html>"), Reply(DONE), Reply(content=b"clip")],
    ))
    out = tmp_path / "c.mp4"
    video_step.generate_clip(cfg(), "https://img/p.png", "push in", out)
    assert out.read_bytes() == b"clip"
    assert http.seen_posts == ["https://api.higgsfield.ai/kling-video/v2.5-turbo/pro/image-to-video"]


def test_after_acceptance_the_chain_never_pays_a_second_provider(cfg, monkeypatch, tmp_path):
    use(monkeypatch, Http(posts=[Reply(STARTED)], gets=[Reply({**STARTED, "status": "failed", "error": "gpu"})]))

    def must_not_run(*a, **kw):
        raise AssertionError("после принятия задачи сосед не вызывается: кадр оплачен")

    monkeypatch.setattr(video_step, "_via_fal", must_not_run)
    with pytest.raises(video_step.AcceptedButNotDelivered) as caught:
        video_step.generate_clip(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")
    assert caught.value.status == "failed" and caught.value.retrievable is False


def test_refusal_before_acceptance_still_lets_the_neighbour_try(cfg, monkeypatch, tmp_path):
    """До ответа на постановку денег не взяли — запасной провайдер вправе помочь."""
    use(monkeypatch, Http(posts=[Reply({"detail": "bad key"}, status_code=403)]))
    called = []

    def fal(cfg_, image_url, prompt, out_path, model, price):
        called.append(True)
        out_path.write_bytes(b"fal")
        return video_step.ClipResult("fal", "m", price)

    monkeypatch.setattr(video_step, "_via_fal", fal)
    done = video_step.generate_clip(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")
    assert called and done.provider == "fal"


def test_timeout_of_a_running_task_keeps_it_for_a_retry(cfg, monkeypatch, tmp_path):
    http = use(monkeypatch, Http(posts=[Reply(STARTED), Reply({"detail": "started"}, status_code=400)]))
    monkeypatch.setattr(video_step, "HIGGSFIELD_TIMEOUT_SEC", -1)
    with pytest.raises(video_step.AcceptedButNotDelivered) as caught:
        video_step.generate_clip(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")
    assert caught.value.status == "timeout" and caught.value.retrievable is True
    assert http.seen_posts[-1] == "https://hf/requests/r1/cancel"


def test_timeout_of_a_queued_task_cancels_it(cfg, monkeypatch, tmp_path):
    use(monkeypatch, Http(posts=[Reply(STARTED), Reply(None, status_code=202)]))
    monkeypatch.setattr(video_step, "HIGGSFIELD_TIMEOUT_SEC", -1)
    with pytest.raises(video_step.AcceptedButNotDelivered) as caught:
        video_step.generate_clip(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")
    assert caught.value.status == "canceled" and caught.value.retrievable is False


def test_failed_download_keeps_the_ready_clip_for_a_retry(cfg, monkeypatch, tmp_path):
    use(monkeypatch, Http(posts=[Reply(STARTED)],
                          gets=[Reply(DONE), httpx.ReadTimeout("slow"), Reply(status_code=502), Reply(status_code=502)]))
    with pytest.raises(video_step.AcceptedButNotDelivered) as caught:
        video_step.generate_clip(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")
    assert caught.value.status == "completed" and caught.value.retrievable is True


# --- продолжение задачи прошлого запуска ----------------------------------------

def request(**overrides) -> video_step.ProviderRequest:
    base = dict(provider="higgsfield", model="kling-video/v2.5-turbo/pro/image-to-video",
                request_id="r1", status_url="https://hf/requests/r1/status", cost_usd=0.35)
    return video_step.ProviderRequest(**{**base, **overrides})


def test_resume_collects_the_result_without_ordering_again(cfg, monkeypatch, tmp_path):
    http = use(monkeypatch, Http(gets=[Reply(DONE), Reply(content=b"old-clip")]))
    out = tmp_path / "c.mp4"
    done = video_step.resume_clip(cfg(), request(), out)
    assert http.seen_posts == [], "ни одного нового заказа"
    assert out.read_bytes() == b"old-clip"
    assert done.recorded is True, "трата записана ещё при постановке"
    assert done.provider == "higgsfield" and done.request_id == "r1"


def test_resume_waits_for_a_task_still_running(cfg, monkeypatch, tmp_path):
    running = {"request_id": "r1", "status": "in_progress"}
    http = use(monkeypatch, Http(gets=[Reply(running), Reply(DONE), Reply(content=b"clip")]))
    video_step.resume_clip(cfg(), request(), tmp_path / "c.mp4")
    assert http.seen_posts == []


def test_resume_uses_the_documented_status_address(cfg, monkeypatch, tmp_path):
    http = use(monkeypatch, Http(gets=[Reply(DONE), Reply(content=b"clip")]))
    video_step.resume_clip(cfg(), request(request_id="r9", status_url=""), tmp_path / "c.mp4")
    assert http.seen_gets[0] == "https://api.higgsfield.ai/requests/r9/status"


def test_resume_of_a_forgotten_task_is_final(cfg, monkeypatch, tmp_path):
    use(monkeypatch, Http(gets=[Reply({"detail": "not found"}, status_code=404)]))
    with pytest.raises(video_step.AcceptedButNotDelivered) as caught:
        video_step.resume_clip(cfg(), request(), tmp_path / "c.mp4")
    assert caught.value.status == "missing" and caught.value.retrievable is False


def test_resume_never_touches_the_network_in_safe_mode(cfg, monkeypatch, tmp_path):
    monkeypatch.setenv("MVP_SAFE_MODE", "1")
    http = use(monkeypatch, Http())
    with pytest.raises(safe_mode.PaidCallBlocked):
        video_step.resume_clip(cfg(), request(), tmp_path / "c.mp4")
    assert http.seen_gets == [] and http.seen_posts == []


def test_resume_of_another_provider_is_refused_plainly(cfg, monkeypatch, tmp_path):
    use(monkeypatch, Http())
    with pytest.raises(video_step.VideoError, match="только у Higgsfield"):
        video_step.resume_clip(cfg(), request(provider="fal"), tmp_path / "c.mp4")
