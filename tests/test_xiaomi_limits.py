"""Input-size cap and single-flight inference for the Xiaomi backend.

Two failures on 300 DPI pages (3507x2480): the Qwen3-VL processor maps every
32x32 pixel block to one vision token, so a full page becomes ~8.6k tokens and a
single warm call takes ~40 s; two such calls at once take ~85 s each. The backend
therefore (1) caps input pixels and (2) refuses a second concurrent request fast
instead of letting both burn the whole MCP timeout budget.
"""

import threading
import time

from mcp_ocr.backends.base import ErrorCode
from mcp_ocr.backends.xiaomi import XiaomiBackend, fit_dimensions


def _png(tmp_path, name="page.png"):
    path = tmp_path / name
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return str(path)


def _blocking_generator(started, release, output="ok"):
    def generator(path, prompt, max_tokens):
        started.set()
        release.wait(5)
        return output

    return generator


# --- input cap ---------------------------------------------------------------


def test_small_image_is_not_resized():
    assert fit_dimensions(1600, 1131, 4_000_000) == (1600, 1131)


def test_large_image_is_scaled_to_the_pixel_cap():
    width, height = fit_dimensions(3507, 2480, 4_000_000)

    assert width * height <= 4_000_000
    assert width < 3507 and height < 2480
    assert abs((width / height) - (3507 / 2480)) < 0.01


def test_cap_can_be_disabled():
    assert fit_dimensions(3507, 2480, 0) == (3507, 2480)


def test_extreme_aspect_ratio_never_yields_zero():
    width, height = fit_dimensions(1, 10_000_000, 4_000_000)

    assert width >= 1
    assert height >= 1


# --- single-flight inference -------------------------------------------------


def test_second_concurrent_request_gets_ebusy_immediately(tmp_path):
    image = _png(tmp_path)
    started = threading.Event()
    release = threading.Event()
    backend = XiaomiBackend(generator=_blocking_generator(started, release))
    first = {}
    worker = threading.Thread(target=lambda: first.setdefault("result", backend.extract(image)))
    worker.start()
    assert started.wait(2), "first request never entered the model"

    began = time.time()
    second = backend.extract(image)
    elapsed = time.time() - began

    assert second["success"] is False
    assert second["error"] == ErrorCode.EBUSY
    assert elapsed < 1.0, f"busy rejection took {elapsed:.2f}s"

    release.set()
    worker.join(5)
    assert first["result"]["success"] is True


def test_lock_is_released_after_a_failed_request(tmp_path):
    image = _png(tmp_path)
    calls = {"count": 0}

    def generator(path, prompt, max_tokens):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("boom")
        return "ok"

    backend = XiaomiBackend(generator=generator)

    assert backend.extract(image)["error"] == ErrorCode.EPROCESSING
    assert backend.extract(image)["success"] is True


def test_lock_is_released_after_a_successful_request(tmp_path):
    image = _png(tmp_path)
    backend = XiaomiBackend(generator=lambda path, prompt, max_tokens: "ok")

    backend.extract(image)

    started = threading.Event()
    release = threading.Event()
    release.set()
    blocker = XiaomiBackend(generator=_blocking_generator(started, release))
    assert blocker.extract(image)["success"] is True


def test_error_code_exists():
    assert ErrorCode.EBUSY == "EBUSY"
