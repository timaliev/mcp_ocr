"""MCP progress notifications for long OCR calls.

Pi (and other progress-aware clients) send a ``progressToken`` and reset their
per-request timeout on every ``notifications/progress``. A 58-row table page takes
~61 s to decode, so without a heartbeat the 60 s client budget kills it. The server
therefore reports elapsed time while the backend runs, and per-page progress for
batch calls. Clients that do not ask for progress (DSH today) must be unaffected:
``report_progress`` is a no-op there and must never break the result.
"""

import asyncio
import time

import mcp_ocr.server as srv
from mcp_ocr.server import _make_batch_fn, _make_tool_fn, create_server, handle_errors


class FakeContext:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    async def report_progress(self, progress, total=None, message=None):
        if self.fail:
            raise RuntimeError("no progress token")
        self.calls.append({"progress": progress, "total": total, "message": message})


# --- async error contract ----------------------------------------------------


def test_handle_errors_supports_async_success():
    @handle_errors
    async def ok(path):
        return {"success": True, "text": path}

    assert asyncio.run(ok("a.png")) == {"success": True, "text": "a.png"}


def test_handle_errors_supports_async_failure():
    @handle_errors
    async def boom(path):
        raise ValueError("kaboom")

    result = asyncio.run(boom("a.png"))

    assert result["success"] is False
    assert result["error"] == "EPROCESSING"
    assert "kaboom" in result["detail"]


# --- heartbeat for a single slow call ---------------------------------------


def test_slow_call_reports_progress_while_running(monkeypatch):
    monkeypatch.setattr(srv, "PROGRESS_INTERVAL", 0.05)

    def slow(path):
        time.sleep(0.3)
        return {"success": True, "text": "done"}

    tool = _make_tool_fn(slow)
    ctx = FakeContext()

    result = asyncio.run(tool("page.png", ctx=ctx))

    assert result["success"] is True
    assert len(ctx.calls) >= 2, f"expected heartbeats, got {ctx.calls}"
    assert all("OCR" in call["message"] for call in ctx.calls)
    assert ctx.calls[0]["progress"] < ctx.calls[-1]["progress"] or len(ctx.calls) == 1


def test_fast_call_does_not_report_progress(monkeypatch):
    monkeypatch.setattr(srv, "PROGRESS_INTERVAL", 0.05)

    tool = _make_tool_fn(lambda path: {"success": True, "text": "quick"})
    ctx = FakeContext()

    result = asyncio.run(tool("page.png", ctx=ctx))

    assert result["success"] is True
    assert ctx.calls == []


def test_progress_failure_does_not_break_the_result(monkeypatch):
    monkeypatch.setattr(srv, "PROGRESS_INTERVAL", 0.02)

    def slow(path):
        time.sleep(0.1)
        return {"success": True, "text": "still fine"}

    tool = _make_tool_fn(slow)

    result = asyncio.run(tool("page.png", ctx=FakeContext(fail=True)))

    assert result["success"] is True


def test_call_without_context_still_works():
    tool = _make_tool_fn(lambda path: {"success": True, "text": "no ctx"})

    assert asyncio.run(tool("page.png"))["success"] is True


# --- batch progress ----------------------------------------------------------


def test_batch_reports_page_progress(monkeypatch):
    seen = []

    def fake(path, **kwargs):
        seen.append(path)
        return {"success": True, "text": path}

    batch = _make_batch_fn(fake)
    ctx = FakeContext()

    result = asyncio.run(batch(["a.png", "b.png", "c.png"], ctx=ctx))

    assert result["success"] is True
    assert [item["text"] for item in result["results"]] == ["a.png", "b.png", "c.png"]
    assert len(ctx.calls) == 3
    assert [call["total"] for call in ctx.calls] == [3, 3, 3]
    assert [call["progress"] for call in ctx.calls] == [0, 1, 2]


# --- no client-visible schema change ----------------------------------------


def test_context_is_not_exposed_in_tool_schemas():
    tools = asyncio.run(create_server().list_tools())

    assert tools, "server registered no tools"
    for tool in tools:
        properties = tool.input_schema.get("properties", {})
        assert "ctx" not in properties, f"{tool.name} exposes ctx"
        assert "path" in properties or "paths" in properties, tool.name


def test_tool_names_are_unchanged():
    names = {tool.name for tool in asyncio.run(create_server().list_tools())}
    expected = {
        "ocr_text_vision", "ocr_layout_vision", "ocr_table_vision", "ocr_batch_vision",
        "ocr_text_paddle", "ocr_layout_paddle", "ocr_table_paddle", "ocr_batch_paddle",
        "ocr_text_xiaomi", "ocr_layout_xiaomi", "ocr_table_xiaomi", "ocr_formula_xiaomi",
        "ocr_document_xiaomi", "ocr_kie_xiaomi", "ocr_batch_xiaomi",
    }
    assert names == expected
