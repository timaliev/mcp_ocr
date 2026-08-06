"""MCP server for OCR — modular backend architecture."""

import os
import sys
import logging
import functools

from mcp.server import MCPServer

from mcp_ocr.backends import BACKENDS, get_backend, ErrorCode

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("mcp-ocr")


def handle_errors(func):
    """Decorator that catches exceptions and returns structured error dicts."""
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


_BACKEND_DESCRIPTIONS = {
    "vision": (
        "Apple Vision OCR — fast on-device GPU/ANE inference (macOS 10.15+). "
        "Best for CJK + major European languages. Zero install on macOS."
    ),
    "paddle": (
        "PaddleOCR CPU — cross-platform, mature model. "
        "Wider language support than Vision, but slower. Requires PaddleOCR Python package."
    ),
    "paddleocr_vl": (
        "PaddleOCR-VL — 0.9B vision-language model on Apple Silicon (M1+). "
        "Most accurate, 109 languages, supports tables/formulas/charts. "
        "Requires paddleocr-vl Swift CLI."
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


def _make_tool_fn(method):
    """Create a tool function that delegates to a backend method."""
    import inspect as _inspect
    _sig = _inspect.signature(method)
    _has_lang = "lang" in _sig.parameters
    _has_mode = "mode" in _sig.parameters

    @handle_errors
    def tool(path: str, lang: str | None = None, mode: str = "base") -> dict:
        kwargs = {"path": path}
        if _has_lang:
            kwargs["lang"] = lang
        if _has_mode:
            kwargs["mode"] = mode
        return method(**kwargs)

    return tool


def _make_batch_fn(method):
    """Create a batch tool function that delegates to a backend method."""
    import inspect as _inspect
    _sig = _inspect.signature(method)
    _has_lang = "lang" in _sig.parameters
    _has_mode = "mode" in _sig.parameters

    @handle_errors
    def batch_tool(paths: list[str], lang: str | None = None, mode: str = "base") -> dict:
        results = []
        for p in paths:
            kwargs = {"path": p}
            if _has_lang:
                kwargs["lang"] = lang
            if _has_mode:
                kwargs["mode"] = mode
            try:
                r = method(**kwargs)
            except Exception as e:
                r = {"success": False, "error": "EPROCESSING", "detail": str(e)}
            results.append({"path": p, **r})
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
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
