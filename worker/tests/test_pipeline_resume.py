"""Конвейер забирает оплаченный клип, а не заказывает его второй раз.

Провайдер подменён, денег нет. Сначала — решения по одному кадру, потом
сквозной сценарий из ТЗ V1: сборщик умирает посреди ожидания Higgsfield,
повтор проекта забирает ту же задачу, и каждый клип оплачен ровно один раз.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import budget  # noqa: E402
import media  # noqa: E402
import pipeline  # noqa: E402
from steps import video_step  # noqa: E402
from test_pipeline_e2e import FakeDb  # noqa: E402

MODEL = "kling-video/v2.5-turbo/pro/image-to-video"


def make_request(request_id: str = "r1") -> video_step.ProviderRequest:
    return video_step.ProviderRequest(
        provider="higgsfield", model=MODEL, request_id=request_id,
        status_url=f"https://hf/requests/{request_id}/status", cost_usd=0.35,
    )


class Choice:
    provider, model, cost_usd = "higgsfield", MODEL, 0.35


@pytest.fixture
def scene(tmp_path, monkeypatch):
    """Один кадр в базе в памяти и подменённые шаги провайдера."""
    for key, value in {"MVP_SAFE_MODE": "0", "VIDEO_MODE": "provider", "SCRIPT_MODE": "mock"}.items():
        monkeypatch.setenv(key, value)
    from config import Config

    db = FakeDb(tmp_path, {"id": "p" * 36})
    db.shots.append({"id": "s1", "order_index": 0, "image_url": "https://img/1.png"})
    calls = {"resume": [], "order": []}
    state = {"db": db, "shot": db.shots[0], "guard": budget.BudgetGuard(), "calls": calls,
             "cfg": Config(), "clip": tmp_path / "clip.mp4"}

    def run():
        return pipeline._real_clip(
            state["cfg"], db, state["guard"], "p" * 36, state["shot"], 0, state["clip"],
            image_url="https://img/1.png", prompt="push in", choose=lambda: (Choice(), None),
        )

    state["run"] = run
    return state


def fake(monkeypatch, name, behaviour, calls, key):
    def stand_in(*args, **kwargs):
        calls[key].append(args)
        return behaviour()

    monkeypatch.setattr(video_step, name, stand_in)


def finished(recorded: bool = True):
    return video_step.ClipResult("higgsfield", MODEL, 0.35, recorded=recorded, request_id="r1")


def not_delivered(status: str, retrievable: bool, recorded: bool = True):
    def behaviour():
        raise video_step.AcceptedButNotDelivered(
            status, request=make_request(), status=status, recorded=recorded, retrievable=retrievable,
        )
    return behaviour


# --- задача прошлого запуска ----------------------------------------------------

def test_paid_task_from_last_run_is_collected_not_reordered(scene, monkeypatch):
    scene["shot"].update(provider_request_id="r1", provider="higgsfield", model=MODEL, actual_cost_usd=0.35)
    fake(monkeypatch, "resume_clip", finished, scene["calls"], "resume")
    fake(monkeypatch, "generate_clip", finished, scene["calls"], "order")

    done = scene["run"]()
    pipeline._store_clip(scene["db"], scene["guard"], "p" * 36, scene["shot"], 0, done, _clip(scene))

    assert len(scene["calls"]["resume"]) == 1 and scene["calls"]["order"] == []
    assert scene["db"].costs == [], "трата записана ещё в прошлом запуске"
    assert scene["shot"]["generation_mode"] == "real_video"


def test_task_still_running_is_waited_for_not_reordered(scene, monkeypatch):
    scene["shot"].update(provider_request_id="r1", provider="higgsfield")
    fake(monkeypatch, "resume_clip", not_delivered("timeout", True), scene["calls"], "resume")
    fake(monkeypatch, "generate_clip", finished, scene["calls"], "order")

    assert scene["run"]() is None
    assert scene["calls"]["order"] == [], "второй заказ того же кадра — двойная оплата"
    assert scene["shot"]["provider_request_id"] == "r1", "номер остаётся: повтор дождётся клипа"
    assert "timeout" in scene["shot"]["failure_reason"]


def test_forgotten_task_is_replaced_by_a_new_order(scene, monkeypatch):
    scene["shot"].update(provider_request_id="r1", provider="higgsfield")
    fake(monkeypatch, "resume_clip", not_delivered("missing", False), scene["calls"], "resume")
    fake(monkeypatch, "generate_clip", lambda: finished(recorded=False), scene["calls"], "order")

    assert scene["run"]() is not None
    assert len(scene["calls"]["order"]) == 1
    assert scene["shot"]["provider_request_id"] is None


def test_content_rejection_from_last_run_is_not_reordered(scene, monkeypatch):
    scene["shot"].update(provider_request_id="r1", provider="higgsfield")

    def rejected():
        raise video_step.ContentRejected("nsfw")

    fake(monkeypatch, "resume_clip", rejected, scene["calls"], "resume")
    fake(monkeypatch, "generate_clip", finished, scene["calls"], "order")
    assert scene["run"]() is None
    assert scene["calls"]["order"] == []
    assert scene["shot"]["provider_request_id"] is None


# --- новый заказ ----------------------------------------------------------------

def test_new_order_is_paid_for_once_and_remembered(scene, monkeypatch):
    def accepted_then_done():
        assert video_step._notify_accepted(make_request("r7")) is True
        return video_step.ClipResult("higgsfield", MODEL, 0.35, recorded=True, request_id="r7")

    fake(monkeypatch, "generate_clip", accepted_then_done, scene["calls"], "order")
    done = scene["run"]()
    pipeline._store_clip(scene["db"], scene["guard"], "p" * 36, scene["shot"], 0, done, _clip(scene))

    assert scene["db"].costs == [("video", "higgsfield", 0.35)], "одна запись за один клип"
    assert scene["shot"]["provider_request_id"] == "r7"
    assert scene["shot"]["provider_status_url"] == "https://hf/requests/r7/status"
    assert scene["guard"].spent_usd == pytest.approx(0.35)


def test_task_lost_after_acceptance_is_still_paid_for(scene, monkeypatch):
    fake(monkeypatch, "generate_clip", not_delivered("timeout", True, recorded=False), scene["calls"], "order")
    assert scene["run"]() is None
    assert scene["db"].costs == [("video", "higgsfield", 0.35)], "деньги ушли — журнал обязан знать"


def test_handler_record_is_not_doubled_when_delivery_fails(scene, monkeypatch):
    def accepted_then_lost():
        video_step._notify_accepted(make_request("r8"))
        raise video_step.AcceptedButNotDelivered(
            "timeout", request=make_request("r8"), status="timeout", recorded=True, retrievable=True,
        )

    fake(monkeypatch, "generate_clip", accepted_then_lost, scene["calls"], "order")
    assert scene["run"]() is None
    assert scene["db"].costs == [("video", "higgsfield", 0.35)]
    assert scene["shot"]["provider_request_id"] == "r8", "клип ещё может прийти — номер храним"


def test_waiting_keeps_the_job_alive(scene, monkeypatch):
    def accepted_then_waits():
        video_step._notify_accepted(make_request("r9"))
        video_step._notify_status(make_request("r9"), "in_progress")
        return video_step.ClipResult("higgsfield", MODEL, 0.35, recorded=True, request_id="r9")

    fake(monkeypatch, "generate_clip", accepted_then_waits, scene["calls"], "order")
    scene["run"]()
    assert scene["db"].heartbeats == 1
    assert scene["shot"]["provider_status"] == "in_progress"


def _clip(scene) -> Path:
    scene["clip"].write_bytes(b"clip")
    return scene["clip"]


# --- сквозной сценарий: сборщик умер посреди ожидания ----------------------------

class WorkerDied(Exception):
    """Процесс сборщика убит, пока Higgsfield делал клип."""


def local_download(url: str, dest: Path) -> Path:
    """Заглушка сети: file:// вместо https. Повтор начинается с пустой рабочей
    папки — как после настоящего сбоя, — и ассеты приходится скачивать снова."""
    import shutil
    from urllib.parse import unquote, urlparse

    if not dest.exists():
        shutil.copyfile(Path(unquote(urlparse(url).path)), dest)
    return dest


SIZE = (180, 320)


class CrashAndResumeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        storage = root / "storage"
        storage.mkdir()
        clip = root / "provider_clip.mp4"
        media.run_ffmpeg(["-f", "lavfi", "-i", f"testsrc2=size={SIZE[0]}x{SIZE[1]}:rate=30:duration=5",
                          "-pix_fmt", "yuv420p", str(clip)])

        os.environ.update({
            "MVP_SAFE_MODE": "0", "SCRIPT_MODE": "mock", "VIDEO_MODE": "provider",
            "IMAGE_PROVIDER": "pollinations", "VIDEO_FORMAT": "9:16",
            "TRANSITION_SEC": "0.4", "SUBTITLES": "0",
        })
        from config import Config
        from steps import image_step, tts_step

        cls.project_id = str(uuid.uuid4())
        cls.db = FakeDb(storage, {"id": cls.project_id, "topic": "a lighthouse keeper at dawn",
                                  "style": "cinematic", "duration_sec": 20, "aspect_ratio": "9:16",
                                  "status": "queued"})
        cls.orders: list[str] = []
        cls.resumed: list[str] = []
        state = {"crashed": False}

        def order(cfg, image_url, motion_prompt, out_path, model=None, cost_usd=None, provider=None):
            request_id = f"r{len(cls.orders) + 1}"
            cls.orders.append(image_url)
            video_step._notify_accepted(make_request(request_id))
            if not state["crashed"]:
                state["crashed"] = True
                raise WorkerDied("kill -9 посреди ожидания")
            out_path.write_bytes(clip.read_bytes())
            return video_step.ClipResult("higgsfield", MODEL, 0.35, recorded=True, request_id=request_id)

        def resume(cfg, request, out_path):
            cls.resumed.append(request.request_id)
            out_path.write_bytes(clip.read_bytes())
            return video_step.ClipResult("higgsfield", request.model, request.cost_usd,
                                         recorded=True, request_id=request.request_id)

        def image(cfg, prompt, out_path, index=0):
            media.run_ffmpeg(["-f", "lavfi", "-i", f"color=c=gray:size={SIZE[0]}x{SIZE[1]}",
                              "-frames:v", "1", str(out_path)])
            return 0.0

        def voice(cfg, text, out_path):
            media.run_ffmpeg(["-f", "lavfi", "-i", "anoisesrc=d=4:c=pink:a=0.3", "-ar", "44100", str(out_path)])
            return 0.0

        cls._originals = [
            (video_step, "generate_clip", video_step.generate_clip),
            (video_step, "resume_clip", video_step.resume_clip),
            (image_step, "generate_image", image_step.generate_image),
            (tts_step, "synthesize", tts_step.synthesize),
            (pipeline, "_download", pipeline._download),
        ]
        video_step.generate_clip, video_step.resume_clip = order, resume
        image_step.generate_image, tts_step.synthesize = image, voice
        pipeline._download = local_download
        media.FORMATS["9:16"] = SIZE

        try:
            pipeline.run_project(Config(), cls.db, cls.project_id)
        except WorkerDied:
            pass
        cls.after_crash = [dict(s) for s in cls.db.shots]
        pipeline.run_project(Config(), cls.db, cls.project_id)

    @classmethod
    def tearDownClass(cls) -> None:
        for module, name, original in cls._originals:
            setattr(module, name, original)
        media.FORMATS["9:16"] = (1080, 1920)
        cls._tmp.cleanup()

    def test_the_task_number_survived_the_crash(self) -> None:
        pending = [s for s in self.after_crash if s.get("provider_request_id") and not s.get("video_url")]
        self.assertEqual([s["provider_request_id"] for s in pending], ["r1"])

    def test_the_retry_collected_that_task_instead_of_ordering_it_again(self) -> None:
        self.assertEqual(self.resumed, ["r1"])
        crashed_image = self.orders[0]
        self.assertEqual(self.orders.count(crashed_image), 1, "кадр, умерший в ожидании, заказан один раз")

    def test_every_clip_is_paid_for_exactly_once(self) -> None:
        videos = [c for c in self.db.costs if c[0] == "video"]
        self.assertEqual(len(videos), len(self.orders))
        real = [s for s in self.db.shots if s.get("generation_mode") == "real_video"]
        self.assertEqual(len(real), len(self.orders))

    def test_the_film_was_finished(self) -> None:
        self.assertIn(self.db.project["status"], ("done", "done_degraded"))
        self.assertTrue(self.db.renders)
