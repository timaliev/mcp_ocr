"""First-call warming: the model downloads in the background, the call returns EWARMING.

A 1.75 GB checkpoint cannot be fetched inside a 60 s MCP tool-call budget, so the
backend never blocks on the download. The first call starts a background download
and answers ``EWARMING``; calls made while it runs answer the same way without
starting a second download, and calls after it finishes run normally.
"""

import threading

import pytest

from mcp_ocr.backends.base import ErrorCode
from mcp_ocr.backends.xiaomi import ModelWarmer, XiaomiBackend


def _png(tmp_path, name="page.png"):
    path = tmp_path / name
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return str(path)


def _stub(output="text"):
    def generator(path, prompt, max_tokens):
        return output

    return generator


class _FakeWarmer:
    """Stand-in for ModelWarmer with controllable state."""

    def __init__(self, ready=False, state="downloading", progress=0.25, error=None):
        self.ready_flag = ready
        self.state = state
        self.progress = progress
        self.error = error
        self.ensure_calls = 0

    def ready(self):
        return self.ready_flag

    def ensure(self):
        self.ensure_calls += 1
        return {"state": self.state, "progress": self.progress, "error": self.error}


def test_first_call_returns_ewarming_and_does_not_touch_the_model(tmp_path):
    image = _png(tmp_path)
    warmer = _FakeWarmer(ready=False)
    called = []

    def generator(path, prompt, max_tokens):
        called.append(path)
        return "should not run"

    backend = XiaomiBackend(generator=generator, warmer=warmer)

    result = backend.extract(image)

    assert result["success"] is False
    assert result["error"] == ErrorCode.EWARMING
    assert result["progress"] == 0.25
    assert called == []
    assert warmer.ensure_calls == 1


def test_calls_while_warming_keep_returning_ewarming(tmp_path):
    image = _png(tmp_path)
    warmer = _FakeWarmer(ready=False)
    backend = XiaomiBackend(generator=_stub(), warmer=warmer)

    for _ in range(3):
        assert backend.extract(image)["error"] == ErrorCode.EWARMING


def test_call_proceeds_once_the_model_is_cached(tmp_path):
    image = _png(tmp_path)
    warmer = _FakeWarmer(ready=True)
    backend = XiaomiBackend(generator=_stub("готово"), warmer=warmer)

    result = backend.extract(image)

    assert result["success"] is True
    assert result["text"] == "готово"
    assert warmer.ensure_calls == 0


def test_download_failure_is_reported(tmp_path):
    image = _png(tmp_path)
    warmer = _FakeWarmer(ready=False, state="error", error="HTTP 503")
    backend = XiaomiBackend(generator=_stub(), warmer=warmer)

    result = backend.extract(image)

    assert result["success"] is False
    assert result["error"] == ErrorCode.EPROCESSING
    assert "HTTP 503" in result["detail"]


def test_missing_file_is_enoent_before_any_warming(tmp_path):
    warmer = _FakeWarmer(ready=False)
    backend = XiaomiBackend(generator=_stub(), warmer=warmer)

    result = backend.extract(str(tmp_path / "missing.png"))

    assert result["error"] == ErrorCode.ENOENT
    assert warmer.ensure_calls == 0


def test_injected_generator_skips_warming(tmp_path):
    """Tests and custom pipelines provide the model themselves — no download."""
    image = _png(tmp_path)
    backend = XiaomiBackend(generator=_stub("ok"))

    assert backend.extract(image)["success"] is True


# --- ModelWarmer itself ------------------------------------------------------


def test_warmer_starts_one_background_download():
    started = threading.Event()
    release = threading.Event()
    calls = []

    def download(model_id):
        calls.append(model_id)
        started.set()
        release.wait(2)

    warmer = ModelWarmer(model_id="m", download=download, cache_check=lambda mid: False)

    warmer.ensure()
    warmer.ensure()

    assert started.wait(1)
    assert calls == ["m"]
    assert warmer.ready() is False

    release.set()
    warmer.wait(2)
    assert warmer.status()["state"] == "done"


def test_warmer_reports_download_error():
    def download(model_id):
        raise RuntimeError("boom")

    warmer = ModelWarmer(model_id="m", download=download, cache_check=lambda mid: False)

    warmer.ensure()
    warmer.wait(2)

    status = warmer.status()
    assert status["state"] == "error"
    assert "boom" in status["error"]


def test_warmer_ready_when_model_already_cached():
    warmer = ModelWarmer(
        model_id="m",
        download=lambda model_id: pytest.fail("must not download"),
        cache_check=lambda mid: True,
    )

    status = warmer.ensure()

    assert warmer.ready() is True
    assert status["state"] == "done"
