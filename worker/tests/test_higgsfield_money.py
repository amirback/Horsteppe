"""Деньги на Higgsfield: без двойной оплаты и без лишних трат в журнале.

Сеть подменена, денег нет. Поведение взято из их документации
(docs.higgsfield.ai):

* «Idempotent requests»: повтор постановки с тем же `Idempotency-Key`
  возвращает исходную задачу и второй раз не оплачивается;
* «Billing and retention»: задачи `failed` и `nsfw` не списываются, снятая
  из очереди возвращается;
* «Errors»: 403 — недостаточно средств, 429 — повтор после `Retry-After`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import budget  # noqa: E402
import pipeline  # noqa: E402
from config import Config  # noqa: E402
from steps import video_step  # noqa: E402
from test_pipeline_e2e import FakeDb  # noqa: E402

KLING4 = "kling-video/v4.0/image-to-video"
SEEDANCE25 = "bytedance/seedance-2.5/image-to-video"
STARTED = {"request_id": "r1", "status": "queued", "status_url": "https://hf/requests/r1/status"}
DONE = {"request_id": "r1", "status": "completed", "video": {"url": "https://hf/clip.mp4"}}


class Reply:
    def __init__(self, payload=None, status_code=200, content=b"", headers=None, text=None):
        self._payload, self.status_code, self.content = payload, status_code, content
        self.headers = headers or {}
        self.text = text if text is not None else str(payload)

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class Http:
    """Подделка httpx.Client: помнит заголовки постановок. Исключение — обрыв."""

    def __init__(self, posts=(), gets=()):
        self.posts, self.gets = list(posts), list(gets)
        self.post_urls: list[str] = []
        self.keys: list[str | None] = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, headers=None, **kw):
        self.post_urls.append(url)
        self.keys.append((headers or {}).get("Idempotency-Key"))
        item = self.posts.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def get(self, url, **kw):
        return self.gets.pop(0)


@pytest.fixture
def cfg(monkeypatch):
    for key in ("HF_API_KEY", "HF_API_SECRET", "HIGGSFIELD_VIDEO_MODEL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "MVP_SAFE_MODE": "0", "VIDEO_MODE": "provider", "SCRIPT_MODE": "mock",
        "VIDEO_PROVIDER": "higgsfield", "HF_KEY": "id:secret-not-real",
        "ELEVENLABS_API_KEY": "t", "FAL_KEY": "t",
        "SUPABASE_URL": "https://e.co", "SUPABASE_SERVICE_ROLE_KEY": "t",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(video_step, "HIGGSFIELD_POLL_SEC", 0)
    sleeps: list[float] = []
    import time as _time
    monkeypatch.setattr(_time, "sleep", sleeps.append)
    return Config(), sleeps


def use(monkeypatch, http: Http) -> Http:
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)
    return http


# --- ключ идемпотентности --------------------------------------------------------

def test_lost_answer_is_retried_with_the_same_key(cfg, monkeypatch, tmp_path):
    """Обрыв после отправки: задача могла быть принята. Повтор — с тем же ключом."""
    config, _ = cfg
    http = use(monkeypatch, Http(
        posts=[httpx.ReadTimeout("answer lost"), Reply(STARTED)],
        gets=[Reply(DONE), Reply(content=b"clip")],
    ))
    done = video_step._via_higgsfield(config, "https://img/1.png", "push in", tmp_path / "c.mp4", KLING4)
    assert done.request_id == "r1"
    assert len(http.keys) == 2 and http.keys[0] and http.keys[0] == http.keys[1]
    assert http.post_urls[0] == http.post_urls[1], "та же модель: иначе ключ не защищает"


def test_server_error_is_retried_with_the_same_key(cfg, monkeypatch, tmp_path):
    config, _ = cfg
    http = use(monkeypatch, Http(
        posts=[Reply({"detail": "boom"}, status_code=502), Reply(STARTED)],
        gets=[Reply(DONE), Reply(content=b"clip")],
    ))
    video_step._via_higgsfield(config, "https://img/1.png", "push in", tmp_path / "c.mp4", KLING4)
    assert http.keys[0] == http.keys[1]


def test_each_clip_gets_its_own_key(cfg, monkeypatch, tmp_path):
    """Новый клип — новое намерение. Один ключ на два клипа вернул бы первый клип дважды."""
    config, _ = cfg
    http = use(monkeypatch, Http(
        posts=[Reply(STARTED), Reply({**STARTED, "request_id": "r2"})],
        gets=[Reply(DONE), Reply(content=b"a"), Reply({**DONE, "request_id": "r2"}), Reply(content=b"b")],
    ))
    video_step._via_higgsfield(config, "https://img/1.png", "push in", tmp_path / "a.mp4", KLING4)
    video_step._via_higgsfield(config, "https://img/2.png", "pan", tmp_path / "b.mp4", KLING4)
    assert http.keys[0] and http.keys[1] and http.keys[0] != http.keys[1]


def test_full_queue_waits_as_long_as_they_ask(cfg, monkeypatch, tmp_path):
    config, sleeps = cfg
    use(monkeypatch, Http(
        posts=[Reply({"detail": "account_queue_full"}, status_code=429, headers={"Retry-After": "7"}),
               Reply(STARTED)],
        gets=[Reply(DONE), Reply(content=b"clip")],
    ))
    video_step._via_higgsfield(config, "https://img/1.png", "push in", tmp_path / "c.mp4", KLING4)
    assert sleeps[0] == 7


# --- пустой баланс ---------------------------------------------------------------

def test_empty_balance_stops_the_higgsfield_queue(cfg, monkeypatch, tmp_path):
    """Соседняя модель Higgsfield платит с того же баланса — к ней не идём."""
    config, _ = cfg
    http = use(monkeypatch, Http(posts=[Reply({"detail": "Insufficient balance"}, status_code=403)]))
    with pytest.raises(video_step.InsufficientBalance, match="нет денег"):
        video_step._higgsfield_in_order(config, "https://img/1.png", "push in", tmp_path / "c.mp4",
                                        KLING4, budget_usd=10.0)
    assert len(http.post_urls) == 1


def test_html_403_is_not_mistaken_for_an_empty_balance(cfg, monkeypatch, tmp_path):
    """Страница проверки с кодом 403 — не «нет денег»: очередь моделей идёт дальше."""
    config, _ = cfg
    http = use(monkeypatch, Http(
        posts=[Reply(None, status_code=403, text="<html>check</html>"), Reply(STARTED)],
        gets=[Reply(DONE), Reply(content=b"clip")],
    ))
    # Бюджет нужен: запасная Seedance 2.5 дороже Kling 4.0 и без него не берётся.
    done = video_step._higgsfield_in_order(config, "https://img/1.png", "push in", tmp_path / "c.mp4",
                                           KLING4, budget_usd=10.0)
    assert done.model == SEEDANCE25
    assert http.post_urls[1].endswith(SEEDANCE25)


# --- возврат в журнал ------------------------------------------------------------

def _request(cost: float = 0.63) -> video_step.ProviderRequest:
    return video_step.ProviderRequest(provider="higgsfield", model=KLING4, request_id="r1",
                                      status_url="https://hf/requests/r1/status", cost_usd=cost)


class Choice:
    provider, model, cost_usd = "higgsfield", KLING4, 0.63


@pytest.fixture
def shot(tmp_path, monkeypatch):
    for key, value in {"MVP_SAFE_MODE": "0", "VIDEO_MODE": "provider", "SCRIPT_MODE": "mock"}.items():
        monkeypatch.setenv(key, value)
    db = FakeDb(tmp_path, {"id": "p" * 36})
    db.shots.append({"id": "s1", "order_index": 0, "image_url": "https://img/1.png"})
    state = {"db": db, "shot": db.shots[0], "guard": budget.BudgetGuard(max_budget_usd=5.0),
             "orders": 0}

    def run():
        return pipeline._real_clip(
            Config(), db, state["guard"], "p" * 36, state["shot"], 0, tmp_path / "c.mp4",
            image_url="https://img/1.png", prompt="push in", choose=lambda: (Choice(), None),
        )

    state["run"] = run
    return state


def _order_ends_with(monkeypatch, state, error_for):
    """Новый заказ: задача принята (трата записана), затем — исход из `error_for`."""
    def generate_clip(*args, **kwargs):
        state["orders"] += 1
        request = _request()
        recorded = video_step._notify_accepted(request)
        raise error_for(request, recorded)

    monkeypatch.setattr(video_step, "generate_clip", generate_clip)


def _not_delivered(status, retrievable=False):
    return lambda request, recorded: video_step.AcceptedButNotDelivered(
        status, request=request, status=status, recorded=recorded, retrievable=retrievable)


@pytest.mark.parametrize("status", ["failed", "canceled"])
def test_unbilled_task_is_refunded_once(shot, monkeypatch, status):
    _order_ends_with(monkeypatch, shot, _not_delivered(status))
    assert shot["run"]() is None
    amounts = [amount for _, _, amount in shot["db"].costs]
    assert amounts == [0.63, -0.63], "трата при принятии и возврат после отказа"
    assert shot["guard"].spent_usd == pytest.approx(0.0), "бюджет вернулся следующим кадрам"
    assert shot["shot"]["actual_cost_usd"] == 0
    assert shot["shot"]["provider_request_id"] is None


def test_content_refusal_is_refunded(shot, monkeypatch):
    _order_ends_with(monkeypatch, shot, lambda request, recorded: video_step.ContentRejected(
        "nsfw", request=request, status="nsfw", recorded=recorded))
    shot["run"]()
    assert [a for _, _, a in shot["db"].costs] == [0.63, -0.63]


def test_ip_refusal_is_not_refunded(shot, monkeypatch):
    """`ip_detected` в правилах оплаты не назван — считаем оплаченным."""
    _order_ends_with(monkeypatch, shot, lambda request, recorded: video_step.ContentRejected(
        "ip", request=request, status="ip_detected", recorded=recorded))
    shot["run"]()
    assert [a for _, _, a in shot["db"].costs] == [0.63]
    assert shot["guard"].spent_usd == pytest.approx(0.63)


def test_task_still_running_is_not_refunded(shot, monkeypatch):
    _order_ends_with(monkeypatch, shot, _not_delivered("timeout", retrievable=True))
    shot["run"]()
    assert [a for _, _, a in shot["db"].costs] == [0.63]
    assert shot["shot"]["provider_request_id"] == "r1", "клип ещё может прийти"


def test_no_refund_while_the_task_number_is_still_on_the_shot(shot, monkeypatch):
    """Номер не снялся — повтор увидит задачу снова. Вернуть сейчас значит вернуть дважды."""
    _order_ends_with(monkeypatch, shot, _not_delivered("failed"))

    def broken(shot_id, **fields):
        if "provider_request_id" in fields and fields["provider_request_id"] is None:
            raise RuntimeError("база недоступна")
        shot["db"].update_shot(shot_id, **fields)
        return True

    monkeypatch.setattr(shot["db"], "remember_provider_request", broken)
    shot["run"]()
    assert [a for _, _, a in shot["db"].costs] == [0.63]


def test_unrecorded_failed_task_writes_nothing(shot, monkeypatch):
    """Журнал не узнал о задаче, а провайдер её не списал: писать нечего."""
    def generate_clip(*args, **kwargs):
        raise video_step.AcceptedButNotDelivered(
            "failed", request=_request(), status="failed", recorded=False, retrievable=False)

    monkeypatch.setattr(video_step, "generate_clip", generate_clip)
    shot["run"]()
    assert shot["db"].costs == []


def test_failed_task_from_last_run_is_refunded_then_reordered(shot, monkeypatch):
    shot["shot"].update(provider_request_id="r1", provider="higgsfield", model=KLING4, actual_cost_usd=0.63)
    shot["guard"].record(0.63, "прошлый запуск")

    def resume_clip(cfg_, request, out_path):
        raise video_step.AcceptedButNotDelivered(
            "failed", request=request, status="failed", recorded=True, retrievable=False)

    def generate_clip(*args, **kwargs):
        shot["orders"] += 1
        return video_step.ClipResult("higgsfield", KLING4, 0.63, recorded=False, request_id="r2")

    monkeypatch.setattr(video_step, "resume_clip", resume_clip)
    monkeypatch.setattr(video_step, "generate_clip", generate_clip)
    assert shot["run"]() is not None
    assert [a for _, _, a in shot["db"].costs] == [-0.63]
    assert shot["orders"] == 1, "упавшая задача — не повод бросить кадр"


def test_refund_never_takes_the_budget_below_zero():
    guard = budget.BudgetGuard(max_budget_usd=1.0)
    guard.record(0.2)
    guard.refund(0.5)
    assert guard.spent_usd == 0.0
