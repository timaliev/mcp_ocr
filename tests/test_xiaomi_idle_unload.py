"""Idle unload: the 3 GB model leaves memory after a period without requests.

Measured on this machine: model loaded 3,253 MB, one page OCR 2,909 MB, after
dropping the runtime + ``mps.empty_cache()`` 511 MB, reload from warm cache 3.3 s.
An agent session therefore keeps ~3 GB per OCR server process forever unless the
backend unloads the model when idle.
"""

import threading

from mcp_ocr.backends.xiaomi import (
    IDLE_UNLOAD_SECONDS,
    IdleUnloadTimer,
    XiaomiBackend,
)


def _png(tmp_path, name="page.png"):
    path = tmp_path / name
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return str(path)


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class _UnloadRecorder:
    def __init__(self, results=None):
        self.calls = 0
        self.results = list(results or [])

    def __call__(self):
        self.calls += 1
        return self.results.pop(0) if self.results else True


class _FakeTimer:
    timeout = 300

    def __init__(self):
        self.touches = 0
        self.starts = 0
        self.checks = 0

    def touch(self):
        self.touches += 1

    def start(self):
        self.starts += 1

    def check(self):
        self.checks += 1
        return False


# --- timer semantics ---------------------------------------------------------


def test_default_idle_timeout_is_five_minutes():
    assert IDLE_UNLOAD_SECONDS == 300


def test_model_is_unloaded_only_after_the_timeout():
    clock = _Clock()
    unload = _UnloadRecorder()
    timer = IdleUnloadTimer(300, unload, clock=clock)
    timer.touch()

    clock.advance(299)
    assert timer.check() is False
    assert unload.calls == 0

    clock.advance(2)
    assert timer.check() is True
    assert unload.calls == 1

    clock.advance(1000)
    assert timer.check() is False, "must not unload twice without new activity"
    assert unload.calls == 1


def test_never_mode_keeps_the_model_resident():
    clock = _Clock()
    unload = _UnloadRecorder()
    timer = IdleUnloadTimer(-1, unload, clock=clock)
    timer.touch()

    clock.advance(24 * 3600)

    assert timer.check() is False
    assert unload.calls == 0


def test_immediate_mode_unloads_after_each_request():
    clock = _Clock()
    unload = _UnloadRecorder()
    timer = IdleUnloadTimer(0, unload, clock=clock)
    timer.touch()

    assert timer.check(now=clock()) is True
    assert unload.calls == 1


def test_timer_without_activity_never_unloads():
    clock = _Clock()
    unload = _UnloadRecorder()
    timer = IdleUnloadTimer(1, unload, clock=clock)

    clock.advance(10_000)

    assert timer.check() is False
    assert unload.calls == 0


def test_busy_unload_is_retried_on_the_next_check():
    clock = _Clock()
    unload = _UnloadRecorder(results=[False, True])
    timer = IdleUnloadTimer(10, unload, clock=clock)
    timer.touch()
    clock.advance(11)

    assert timer.check() is False, "inference lock was busy — retry later"
    assert timer.check() is True
    assert unload.calls == 2


def test_watchdog_thread_can_be_started_and_stopped():
    timer = IdleUnloadTimer(1, lambda: True, interval=0.01)
    timer.start()
    assert timer.running is True
    timer.start()  # idempotent
    timer.stop()
    timer._thread.join(2)
    assert timer.running is False


# --- backend integration -----------------------------------------------------


def test_backend_touches_the_timer_after_a_request(tmp_path):
    timer = _FakeTimer()
    backend = XiaomiBackend(
        generator=lambda path, prompt, max_tokens: "ok", idle_timer=timer
    )

    backend.extract(_png(tmp_path))

    assert timer.touches == 1
    assert timer.starts == 1


def test_backend_touches_the_timer_even_when_inference_fails(tmp_path):
    def generator(path, prompt, max_tokens):
        raise RuntimeError("boom")

    timer = _FakeTimer()
    backend = XiaomiBackend(generator=generator, idle_timer=timer)

    assert backend.extract(_png(tmp_path))["error"] == "EPROCESSING"
    assert timer.touches == 1


def test_backend_does_not_touch_the_timer_while_warming(tmp_path):
    class _NotReadyWarmer:
        def ready(self):
            return False

        def ensure(self):
            return {"state": "downloading", "progress": 0.1, "error": None}

    timer = _FakeTimer()
    backend = XiaomiBackend(
        generator=lambda path, prompt, max_tokens: "ok",
        warmer=_NotReadyWarmer(),
        idle_timer=timer,
    )

    assert backend.extract(_png(tmp_path))["error"] == "EWARMING"
    assert timer.touches == 0
