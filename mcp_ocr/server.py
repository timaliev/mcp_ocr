"""MCP server for OCR — modular backend architecture."""

import asyncio
import os
import sys
import logging
import functools
import inspect
import time

from mcp.server import MCPServer
from mcp.server.mcpserver.context import Context

from mcp_ocr.backends import BACKENDS, get_backend, ErrorCode

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("mcp-ocr")

# Long pages can take far longer than a client's per-request timeout (a dense
# 58-row table takes ~60 s to decode). Clients that ask for progress reset that
# timeout on every notification, so report elapsed time while the backend runs.
PROGRESS_INTERVAL = float(os.environ.get("MCP_OCR_PROGRESS_INTERVAL", "5"))


def handle_errors(func):
    """Decorator that catches exceptions and returns structured error dicts."""
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except FileNotFoundError as e:
                return {"success": False, "error": ErrorCode.ENOENT, "detail": str(e)}
            except ImportError as e:
                return {"success": False, "error": ErrorCode.EUNSUPPORTED, "detail": str(e)}
            except Exception as e:
                logger.exception("Tool failed")
                return {"success": False, "error": ErrorCode.EPROCESSING, "detail": str(e)}

        return async_wrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            return {"success": False, "error": ErrorCode.ENOENT, "detail": str(e)}
        except ImportError as e:
            return {"success": False, "error": ErrorCode.EUNSUPPORTED, "detail": str(e)}
        except Exception as e:
            logger.exception("Tool failed")
            return {"success": False, "error": ErrorCode.EPROCESSING, "detail": str(e)}

    return wrapper


def _consume_task_result(task) -> None:
    """Swallow the result/exception of an inference that outlived its request."""
    try:
        task.exception()
    except Exception:
        pass


async def _run_with_progress(method, kwargs: dict, ctx: Context | None):
    """Run a blocking backend method in a thread, reporting progress meanwhile."""
    if ctx is None:
        return await asyncio.to_thread(method, **kwargs)

    task = asyncio.create_task(asyncio.to_thread(method, **kwargs))
    started = time.monotonic()
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=PROGRESS_INTERVAL)
            if task in done:
                return task.result()
            elapsed = time.monotonic() - started
            try:
                await ctx.report_progress(
                    elapsed, None, f"OCR running ({elapsed:.0f}s)"
                )
            except Exception:
                logger.debug("progress notification failed", exc_info=True)
    except asyncio.CancelledError:
        if not task.done():
            # torch inference cannot be interrupted; let it finish and free the
            # model lock so a retry does not sit in EBUSY forever.
            task.add_done_callback(_consume_task_result)
            logger.info("request cancelled — inference continues in background")
        raise


_BACKEND_DESCRIPTIONS = {
    "vision": (
        "Apple Vision OCR — fast on-device GPU/ANE inference (macOS 10.15+). "
        "Best for CJK + major European languages. Zero install on macOS."
    ),
    "paddle": (
        "PaddleOCR CPU — cross-platform, mature model. "
        "Wider language support than Vision, but slower. Requires PaddleOCR Python package."
    ),
    "xiaomi": (
        "Xiaomi-OCR-0 — local 0.8B document-parsing VLM (transformers; Apple Silicon "
        "MPS, CUDA or CPU). Best structure fidelity: Markdown output, HTML tables, "
        "LaTeX formulas, key-information extraction. Strong on Cyrillic, English, "
        "German and Japanese; Arabic/Korean are weak."
    ),
}


def _build_tool_description(task: str, backend_name: str) -> str:
    """Build a rich description for the AI agent to choose the right tool."""
    task_descriptions = {
        "text": "Extract text from an image. Returns full text, per-line confidence, and bounding boxes.",
        "layout": "Extract text with layout analysis. Returns blocks with bounding boxes.",
        "table": "Extract tables from an image. Returns structured CSV/JSON.",
        "formula": "Extract mathematical formulas from an image. Returns LaTeX.",
        "chart": "Extract chart data from an image. Returns structured data.",
        "document": (
            "Parse a document image into Markdown: tables become HTML tables, "
            "formulas stay LaTeX, reading order preserved. Returns {'markdown': ...}."
        ),
        "kie": (
            "Extract key information from a document image as a JSON object. "
            "Pass 'fields' (list of names) to narrow the output schema."
        ),
        "batch": "OCR multiple images at once. Returns consolidated results.",
    }
    backend_desc = _BACKEND_DESCRIPTIONS.get(backend_name, "")
    return f"{task_descriptions.get(task, '')}\n\nBackend: {backend_name}. {backend_desc}"


def create_server() -> MCPServer:
    """Create and register all tools dynamically from the BACKENDS registry."""
    server = MCPServer("ocr", version="2.0.0")

    for backend_name, backend in BACKENDS.items():
        for task in backend.tasks:
            _register_task_tool(server, backend_name, backend, task)
        _register_batch_tool(server, backend_name, backend)

    return server


def _split_fields(fields):
    """Normalise a fields argument to a list of non-empty names or None."""
    if not fields:
        return None
    if isinstance(fields, str):
        fields = fields.split(",")
    names = [name.strip() for name in fields if name.strip()]
    return names or None


def _make_tool_fn(method):
    """Create a tool function exposing only the parameters ``method`` accepts.

    Every tool is async so the backend can run in a worker thread while progress
    notifications keep clients with a per-request timeout alive. ``ctx`` is
    injected by MCPServer and never appears in the tool's input schema.
    """
    params = inspect.signature(method).parameters
    has_fields = "fields" in params
    has_lang = "lang" in params
    has_mode = "mode" in params

    if has_fields:

        @handle_errors
        async def tool(
            path: str,
            fields: list[str] | None = None,
            ctx: Context | None = None,
        ) -> dict:
            return await _run_with_progress(
                method, {"path": path, "fields": _split_fields(fields)}, ctx
            )

    elif has_lang and has_mode:

        @handle_errors
        async def tool(
            path: str,
            lang: str | None = None,
            mode: str = "accurate",
            ctx: Context | None = None,
        ) -> dict:
            return await _run_with_progress(
                method, {"path": path, "lang": lang, "mode": mode}, ctx
            )

    elif has_lang:

        @handle_errors
        async def tool(
            path: str,
            lang: str | None = None,
            ctx: Context | None = None,
        ) -> dict:
            return await _run_with_progress(
                method, {"path": path, "lang": lang}, ctx
            )

    elif has_mode:

        @handle_errors
        async def tool(
            path: str,
            mode: str = "accurate",
            ctx: Context | None = None,
        ) -> dict:
            return await _run_with_progress(method, {"path": path, "mode": mode}, ctx)

    else:

        @handle_errors
        async def tool(path: str, ctx: Context | None = None) -> dict:
            return await _run_with_progress(method, {"path": path}, ctx)

    return tool


def _make_batch_fn(method):
    """Create a batch tool that runs pages one at a time and reports per page."""
    params = inspect.signature(method).parameters
    has_lang = "lang" in params
    has_mode = "mode" in params

    @handle_errors
    async def batch_tool(
        paths: list[str],
        lang: str | None = None,
        mode: str = "accurate",
        ctx: Context | None = None,
    ) -> dict:
        results = []
        total = len(paths)
        for index, path in enumerate(paths):
            if ctx is not None:
                try:
                    await ctx.report_progress(index, total, f"page {index + 1}/{total}")
                except Exception:
                    logger.debug("progress notification failed", exc_info=True)
            kwargs = {"path": path}
            if has_lang:
                kwargs["lang"] = lang
            if has_mode:
                kwargs["mode"] = mode
            try:
                result = await asyncio.to_thread(method, **kwargs)
            except Exception as e:
                result = {"success": False, "error": "EPROCESSING", "detail": str(e)}
            results.append({"path": path, **result})
        return {"success": True, "results": results}

    return batch_tool


def _register_task_tool(server: MCPServer, backend_name: str, backend, task: str):
    """Register a single task tool for a given backend + task combination."""
    tool_name = f"ocr_{task}_{backend_name}"
    description = _build_tool_description(task, backend_name)
    _method_map = {"text": "extract"}
    method_name = _method_map.get(task, task)
    method = getattr(backend, method_name)

    tool_fn = _make_tool_fn(method)
    server.tool(name=tool_name, description=description)(tool_fn)


def _register_batch_tool(server: MCPServer, backend_name: str, backend):
    """Register a batch tool for a given backend (uses extract method)."""
    batch_name = f"ocr_batch_{backend_name}"
    batch_desc = _build_tool_description("batch", backend_name)
    method = getattr(backend, "extract")
    batch_fn = _make_batch_fn(method)
    server.tool(name=batch_name, description=batch_desc)(batch_fn)


def main():
    import sys
    if "--version" in sys.argv:
        from importlib.metadata import version
        print(f"mcp-ocr {version('mcp-ocr')}")
        return
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
