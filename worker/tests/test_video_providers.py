"""Цепочка провайдеров видео.

Ни сети, ни денег: ответы провайдеров подменяются. Проверяется то, из-за
чего платный путь однажды встал целиком — отказ одного провайдера не должен
останавливать проект, когда клип может сделать второй.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config  # noqa: E402
from steps import video_step  # noqa: E402


@pytest.fixture
def cfg(monkeypatch):
    """Чистая конфигурация, не зависящая от .env разработчика.

    Настоящие ключи с машины однажды уже подменили ожидания теста: HF_KEY из
    .env перебил подставленную пару, и проверка сравнивала чужое значение.
    Поэтому все ключи провайдеров сначала снимаются.
    """
    for key in ("HF_KEY", "HF_API_KEY", "HF_API_SECRET",
                "REPLICATE_API_TOKEN", "VIDEO_PROVIDER", "HIGGSFIELD_VIDEO_MODEL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "MVP_SAFE_MODE": "0", "VIDEO_MODE": "provider", "SCRIPT_MODE": "mock",
        "ELEVENLABS_API_KEY": "t", "FAL_KEY": "t",
        "SUPABASE_URL": "https://e.co", "SUPABASE_SERVICE_ROLE_KEY": "t",
    }.items():
        monkeypatch.setenv(key, value)
    return Config


def test_default_chain_is_fal(cfg, monkeypatch):
    monkeypatch.delenv("VIDEO_PROVIDER", raising=False)
    assert cfg().video_providers == ["fal"]


def test_chain_is_read_in_order(cfg, monkeypatch):
    monkeypatch.setenv("VIDEO_PROVIDER", "replicate,fal")
    assert cfg().video_providers == ["replicate", "fal"]


def test_unknown_provider_is_ignored_not_crashed(cfg, monkeypatch):
    """Опечатка в настройке не должна ронять весь проект."""
    monkeypatch.setenv("VIDEO_PROVIDER", "runway,replicate")
    monkeypatch.setenv("REPLICATE_API_TOKEN", "t")
    assert cfg().video_providers == ["replicate"]


def test_empty_setting_falls_back_to_fal(cfg, monkeypatch):
    monkeypatch.setenv("VIDEO_PROVIDER", "  ")
    assert cfg().video_providers == ["fal"]


def test_second_provider_saves_the_project(cfg, monkeypatch, tmp_path):
    """Заблокированный аккаунт у первого провайдера — не приговор.

    Ровно это и случилось: fal ответил «User is locked», и платный путь
    встал целиком, хотя клип мог сделать кто-то другой.
    """
    monkeypatch.setenv("VIDEO_PROVIDER", "fal,replicate")

    def dead_fal(*a, **kw):
        raise video_step.VideoError("User is locked. Reason: TOP_UP.")

    def working_replicate(cfg_, image_url, prompt, out_path):
        out_path.write_bytes(b"clip")
        return 0.45

    monkeypatch.setattr(video_step, "_via_fal", dead_fal)
    monkeypatch.setattr(video_step, "_via_replicate", working_replicate)

    out = tmp_path / "clip.mp4"
    price = video_step.generate_clip(cfg(), "https://example/i.png", "push in", out)
    assert out.read_bytes() == b"clip"
    assert price == 0.45


def test_all_providers_failing_names_every_reason(cfg, monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PROVIDER", "fal,replicate")

    def dead(*a, **kw):
        raise video_step.VideoError("нет денег")

    monkeypatch.setattr(video_step, "_via_fal", dead)
    monkeypatch.setattr(video_step, "_via_replicate", dead)

    with pytest.raises(video_step.VideoError) as exc:
        video_step.generate_clip(cfg(), "https://example/i.png", "push in", tmp_path / "c.mp4")
    assert "fal" in str(exc.value) and "replicate" in str(exc.value)


def test_replicate_without_a_token_says_so_plainly(cfg, monkeypatch, tmp_path):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    with pytest.raises(video_step.VideoError, match="REPLICATE_API_TOKEN"):
        video_step._via_replicate(cfg(), "https://example/i.png", "push in", tmp_path / "c.mp4")


@pytest.mark.parametrize("output,expected", [
    ("https://x/v.mp4", "https://x/v.mp4"),
    (["https://x/a.mp4", "https://x/b.mp4"], "https://x/b.mp4"),
    ({"video": "https://x/c.mp4"}, "https://x/c.mp4"),
    ({"output": ["https://x/d.mp4"]}, "https://x/d.mp4"),
    (None, None),
    ([], None),
])
def test_output_url_is_found_in_every_shape(output, expected):
    """Модели отдают ссылку то строкой, то списком, то объектом."""
    assert video_step._replicate_output_url(output) == expected


# --- Higgsfield: контракт взят из их openapi.json ---------------------------

class FakeResponse:
    def __init__(self, payload=None, status_code=200, content=b"clip"):
        self._payload = payload or {}
        self.status_code = status_code
        self.content = content
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


class FakeHttp:
    """Подделка httpx.Client: записывает вызовы, отдаёт заготовленные ответы."""

    def __init__(self, posts, gets):
        self.posts = list(posts)
        self.gets = list(gets)
        self.seen_posts: list[tuple] = []
        self.seen_gets: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, headers=None, json=None, **kw):
        self.seen_posts.append((url, headers, json))
        return self.posts.pop(0)

    def get(self, url, headers=None, **kw):
        self.seen_gets.append(url)
        return self.gets.pop(0)


@pytest.fixture
def hf(monkeypatch):
    monkeypatch.setenv("HF_API_KEY", "id-not-a-secret")
    monkeypatch.setenv("HF_API_SECRET", "secret-not-a-secret")
    monkeypatch.setenv("HIGGSFIELD_POLL_SEC", "0")
    monkeypatch.setattr(video_step, "HIGGSFIELD_POLL_SEC", 0)
    return None


def test_credential_is_assembled_as_key_and_secret(cfg, hf):
    assert cfg().higgsfield_credential == "id-not-a-secret:secret-not-a-secret"


def test_single_key_variable_wins(cfg, monkeypatch, hf):
    monkeypatch.setenv("HF_KEY", "whole:thing")
    assert cfg().higgsfield_credential == "whole:thing"


def test_request_matches_the_documented_schema(cfg, hf, monkeypatch, tmp_path):
    """Обязательные поля — prompt и image_url, длительность из набора."""
    started = {"request_id": "r1", "status": "queued",
               "status_url": "https://api/requests/r1/status",
               "cancel_url": "https://api/requests/r1/cancel"}
    done = {"status": "completed", "video": {"url": "https://api/clip.mp4"}}
    http = FakeHttp(posts=[FakeResponse(started)],
                    gets=[FakeResponse(done), FakeResponse(content=b"real-clip")])
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)

    out = tmp_path / "c.mp4"
    video_step._via_higgsfield(cfg(), "https://img/p.png", "slow push in", out)

    url, headers, payload = http.seen_posts[0]
    assert url.endswith("/kling-video/v2.5-turbo/pro/image-to-video")
    assert headers["Authorization"].startswith("Key ")
    assert payload["prompt"] == "slow push in"
    assert payload["image_url"] == "https://img/p.png"
    assert payload["duration"] in (5, 10)
    assert out.read_bytes() == b"real-clip"


def test_nsfw_is_a_verdict_not_a_provider_outage(cfg, hf, monkeypatch, tmp_path):
    """Отклонённое по содержанию не отдаём соседу — он отклонит так же.

    Цепочка обязана остановиться: второй вызов стоил бы денег за тот же
    отказ.
    """
    started = {"request_id": "r1", "status": "queued",
               "status_url": "https://api/requests/r1/status", "cancel_url": "https://api/c"}
    http = FakeHttp(posts=[FakeResponse(started)], gets=[FakeResponse({"status": "nsfw"})])
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)

    with pytest.raises(video_step.ContentRejected):
        video_step._via_higgsfield(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")


def test_content_rejection_stops_the_whole_chain(cfg, monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PROVIDER", "higgsfield,fal")

    def rejected(*a, **kw):
        raise video_step.ContentRejected("nsfw")

    def must_not_run(*a, **kw):
        raise AssertionError("второй провайдер не должен вызываться после отказа по содержанию")

    monkeypatch.setattr(video_step, "_via_higgsfield", rejected)
    monkeypatch.setattr(video_step, "_via_fal", must_not_run)

    with pytest.raises(video_step.ContentRejected):
        video_step.generate_clip(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")


def test_overload_is_retried_then_succeeds(cfg, hf, monkeypatch, tmp_path):
    """Один отказ 429 больше не роняет кадр."""
    started = {"request_id": "r1", "status": "completed", "status_url": "https://api/s",
               "cancel_url": "https://api/c", "video": {"url": "https://api/clip.mp4"}}
    http = FakeHttp(
        posts=[FakeResponse({"detail": "rate limited"}, status_code=429), FakeResponse(started)],
        gets=[FakeResponse(content=b"clip")],
    )
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)
    monkeypatch.setattr(video_step, "HIGGSFIELD_ATTEMPTS", 3)
    import time as _t
    monkeypatch.setattr(_t, "sleep", lambda s: None)

    out = tmp_path / "c.mp4"
    video_step._via_higgsfield(cfg(), "https://img/p.png", "push in", out)
    assert len(http.seen_posts) == 2


def test_missing_credentials_say_which_variables(cfg, monkeypatch, tmp_path):
    for var in ("HF_KEY", "HF_API_KEY", "HF_API_SECRET"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(video_step.VideoError, match="HF_KEY"):
        video_step._via_higgsfield(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")


def test_higgsfield_joins_the_known_chain(cfg, monkeypatch):
    monkeypatch.setenv("VIDEO_PROVIDER", "higgsfield,fal,replicate")
    assert cfg().video_providers == ["higgsfield", "fal", "replicate"]


class HtmlResponse(FakeResponse):
    """Страница анти-бота вместо ответа API."""

    def __init__(self):
        super().__init__(status_code=200)
        self.text = "<html><body>captcha-delivery</body></html>"

    def json(self):
        raise ValueError("Expecting value: line 1 column 1 (char 0)")


def test_anti_bot_page_does_not_crash_the_shot(cfg, hf, monkeypatch, tmp_path):
    """Вместо JSON может прийти HTML с проверкой — их руководство это описывает.

    Без обработки разбор падал бы исключением мимо цепочки провайдеров, и
    кадр терялся бы там, где сосед мог справиться.
    """
    http = FakeHttp(posts=[HtmlResponse()], gets=[])
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)
    with pytest.raises(video_step.VideoError, match="не JSON"):
        video_step._via_higgsfield(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")


def test_anti_bot_page_lets_the_chain_continue(cfg, hf, monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PROVIDER", "higgsfield,replicate")
    http = FakeHttp(posts=[HtmlResponse()], gets=[])
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)

    def rescue(cfg_, image_url, prompt, out_path):
        out_path.write_bytes(b"saved")
        return 0.45

    monkeypatch.setattr(video_step, "_via_replicate", rescue)
    out = tmp_path / "c.mp4"
    video_step.generate_clip(cfg(), "https://img/p.png", "push in", out)
    assert out.read_bytes() == b"saved"


def test_ip_detected_is_also_a_content_verdict(cfg, hf, monkeypatch, tmp_path):
    """Новый повод для отказа не должен притворяться сбоем сети."""
    started = {"request_id": "r1", "status": "queued",
               "status_url": "https://api/s", "cancel_url": "https://api/c"}
    http = FakeHttp(posts=[FakeResponse(started)], gets=[FakeResponse({"status": "ip_detected"})])
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)
    with pytest.raises(video_step.ContentRejected):
        video_step._via_higgsfield(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")


def test_timeout_cancels_the_abandoned_request(cfg, hf, monkeypatch, tmp_path):
    """Брошенный запрос продолжает считаться и тратить кредиты."""
    started = {"request_id": "r1", "status": "queued",
               "status_url": "https://api/s", "cancel_url": "https://api/cancel"}
    http = FakeHttp(posts=[FakeResponse(started), FakeResponse({})],
                    gets=[FakeResponse({"status": "in_progress"})] * 4)
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)
    monkeypatch.setattr(video_step, "HIGGSFIELD_TIMEOUT_SEC", -1)

    with pytest.raises(video_step.VideoError, match="не отдал клип"):
        video_step._via_higgsfield(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4")
    assert any("cancel" in url for url, _, _ in http.seen_posts), http.seen_posts


# --- честность метаданных ---------------------------------------------------

def test_result_names_the_provider_that_actually_worked(cfg, hf, monkeypatch, tmp_path):
    """В базе оставалась ложь: «fal, kling v2.1 pro» там, где работал Higgsfield.

    Маршрутизатор знает только модели fal, а цепочка отдаёт кадр первому
    доступному провайдеру. По этим метаданным считают деньги и выбирают
    модель, поэтому они обязаны говорить правду о том, что произошло.
    """
    monkeypatch.setenv("VIDEO_PROVIDER", "higgsfield,fal")
    started = {"request_id": "r1", "status": "completed",
               "status_url": "https://api/s", "cancel_url": "https://api/c",
               "video": {"url": "https://api/clip.mp4"}}
    http = FakeHttp(posts=[FakeResponse(started)], gets=[FakeResponse(content=b"clip")])
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)

    # Маршрутизатор предлагает модель fal — её не должно оказаться в ответе.
    out = tmp_path / "c.mp4"
    done = video_step.generate_clip(
        cfg(), "https://img/p.png", "push in", out,
        model="fal-ai/kling-video/v2.1/pro/image-to-video", cost_usd=0.35,
    )
    assert done.provider == "higgsfield"
    assert done.model == "kling-video/v2.5-turbo/pro/image-to-video"
    assert "fal" not in done.model


def test_fal_result_reports_the_routed_model(cfg, monkeypatch, tmp_path):
    """Когда работает fal, в ответе должна стоять именно выбранная им модель."""
    monkeypatch.setenv("VIDEO_PROVIDER", "fal")

    def fake_fal(cfg_, image_url, prompt, out_path, model, price):
        out_path.write_bytes(b"clip")
        return video_step.ClipResult("fal", model, price)

    monkeypatch.setattr(video_step, "_via_fal", fake_fal)
    done = video_step.generate_clip(
        cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4",
        model="fal-ai/kling-video/v2.1/standard/image-to-video", cost_usd=0.35,
    )
    assert done.provider == "fal"
    assert done.model.endswith("v2.1/standard/image-to-video")
    assert done.cost_usd == 0.35


# ---- Уровни моделей (2026-11-14): поля запроса, цена в журнал, очередь в уровне

KLING_4 = "kling-video/v4.0/image-to-video"
SEEDANCE_25 = "bytedance/seedance-2.5/image-to-video"


@pytest.mark.parametrize("model, allowed", [
    (KLING_4, {"prompt", "image_url", "duration", "resolution"}),
    (SEEDANCE_25, {"prompt", "image_url", "duration", "resolution", "generate_audio"}),
    ("bytedance/seedance-2.0/image-to-video", {"prompt", "image_url", "duration", "resolution", "generate_audio"}),
    ("alibaba/wan-3.0/image-to-video", {"prompt", "image_url", "duration", "resolution", "generate_audio"}),
    ("kling-video/v3.0/pro/image-to-video", {"prompt", "image_url", "duration", "cfg_scale", "sound"}),
])
def test_each_model_gets_only_its_own_fields(model, allowed):
    """Лишнее поле схема модели может запретить — задача была бы отклонена."""
    payload = video_step._higgsfield_payload(model, "slow push in", "https://img/p.png")
    assert set(payload) <= allowed, set(payload) - allowed
    assert payload["image_url"] == "https://img/p.png"
    assert payload.get("generate_audio", False) is False, "у ролика своя озвучка"
    assert payload.get("sound", "off") == "off"
    if "resolution" in payload:
        assert payload["resolution"] == "720p"
    if model.startswith("bytedance/seedance"):
        assert payload["duration"] >= 4, "Seedance короче 4 секунд не принимает"


def test_old_kling_keeps_its_negative_prompt():
    payload = video_step._higgsfield_payload("kling-video/v2.5-turbo/pro/image-to-video", "p", "https://i/p.png")
    assert "negative_prompt" in payload and "cfg_scale" in payload


def test_ledger_gets_the_price_of_the_model_that_ran(cfg, hf, monkeypatch, tmp_path):
    started = {"request_id": "r1", "status": "queued",
               "status_url": "https://api/requests/r1/status", "cancel_url": "https://api/c"}
    done = {"status": "completed", "video": {"url": "https://api/clip.mp4"}}
    http = FakeHttp(posts=[FakeResponse(started)],
                    gets=[FakeResponse(done), FakeResponse(content=b"real-clip")])
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)

    result = video_step._via_higgsfield(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4", KLING_4)
    assert result.model == KLING_4
    assert result.cost_usd == pytest.approx(0.63)
    assert http.seen_posts[0][0].endswith("/" + KLING_4)


def _queue(cfg, monkeypatch, tmp_path, budget, failure):
    monkeypatch.setenv("VIDEO_PROVIDER", "higgsfield")
    monkeypatch.setenv("HF_KEY", "id:secret-not-real")
    tried = []

    def fake(cfg_, image_url, prompt, out_path, model=None):
        tried.append(model)
        if model == KLING_4:
            raise failure
        return video_step.ClipResult("higgsfield", model, 1.32)

    monkeypatch.setattr(video_step, "_via_higgsfield", fake)
    try:
        video_step.generate_clip(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4",
                                 provider="higgsfield", model=KLING_4, cost_usd=0.63, budget_usd=budget)
    except video_step.VideoError:
        pass
    return tried


def test_seedance_takes_the_shot_when_kling_4_refuses_and_budget_allows(cfg, monkeypatch, tmp_path):
    tried = _queue(cfg, monkeypatch, tmp_path, 5.0, video_step.VideoError("перегрузка"))
    assert tried == [KLING_4, SEEDANCE_25]


def test_no_seedance_when_the_budget_does_not_cover_it(cfg, monkeypatch, tmp_path):
    assert _queue(cfg, monkeypatch, tmp_path, 1.0, video_step.VideoError("перегрузка")) == [KLING_4]
    assert _queue(cfg, monkeypatch, tmp_path, None, video_step.VideoError("перегрузка")) == [KLING_4]


def test_content_rejection_does_not_reach_the_second_model(cfg, monkeypatch, tmp_path):
    """Что отклонил Kling 4.0, отклонит и Seedance — а вызов стоил бы денег."""
    tried = _queue(cfg, monkeypatch, tmp_path, 5.0, video_step.ContentRejected("nsfw"))
    assert tried == [KLING_4]


# ---- Длина клипа = длина кадра (2026-11-14): не платить за обрезки

@pytest.mark.parametrize("model, shot_sec, expected", [
    (KLING_4, 3.2, 4),                                    # вверх до целого
    (KLING_4, 2.4, 3),                                    # Kling 4.0 не короче 3 с
    (KLING_4, 5.0, 5),
    (SEEDANCE_25, 3.0, 4),                                # Seedance не короче 4 с
    ("alibaba/wan-3.0/image-to-video", 2.0, 2),
    ("kling-video/v3.0/pro/image-to-video", 3.75, 4),
])
def test_clip_is_ordered_for_the_length_of_the_shot(model, shot_sec, expected):
    assert video_step._clip_seconds(model, shot_sec) == expected


def test_fixed_length_models_and_unknown_length_keep_the_old_clip():
    """Kling 2.5 Turbo принимает только 5 или 10 секунд — четыре он отвергнет."""
    assert video_step._clip_seconds("kling-video/v2.5-turbo/pro/image-to-video", 3.0) == video_step.HIGGSFIELD_DURATION
    assert video_step._clip_seconds(KLING_4, None) == video_step.HIGGSFIELD_DURATION


def test_shorter_clip_costs_proportionally_less():
    assert video_step._model_cost(KLING_4, 4) == pytest.approx(0.63 * 4 / 5)
    assert video_step._model_cost(KLING_4) == pytest.approx(0.63)
    assert video_step._model_cost("kling-video/v2.5-turbo/pro/image-to-video", 4) == pytest.approx(
        video_step._model_cost("kling-video/v2.5-turbo/pro/image-to-video"))


def test_shot_length_reaches_the_request_and_the_ledger(cfg, hf, monkeypatch, tmp_path):
    started = {"request_id": "r1", "status": "queued",
               "status_url": "https://api/requests/r1/status", "cancel_url": "https://api/c"}
    done = {"status": "completed", "video": {"url": "https://api/clip.mp4"}}
    http = FakeHttp(posts=[FakeResponse(started)],
                    gets=[FakeResponse(done), FakeResponse(content=b"real-clip")])
    monkeypatch.setattr(video_step.httpx, "Client", lambda **kw: http)

    with video_step.tracking(clip_sec=3.2):
        result = video_step._via_higgsfield(cfg(), "https://img/p.png", "push in", tmp_path / "c.mp4", KLING_4)
    assert http.seen_posts[0][2]["duration"] == 4
    assert result.cost_usd == pytest.approx(0.63 * 4 / 5)
