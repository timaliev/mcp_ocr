# PaddleOCR-VL: Mode Parameter Incompatibility

**Date:** 2026-08-06  
**Status:** Open (needs fix in server.py)

---

## Symptom

Calling `ocr_text_paddleocr_vl` MCP tool fails:

```
Error: The value 'accurate' is invalid for '--mode <mode>'.
Please provide one of 'base' and 'dynamic'.
Usage: paddleocr-vl ocr <image-paths> ... --mode <mode>
```

The tool works when `mode: "base"` is passed explicitly, but the default `"accurate"` (inherited from server.py's generic tool template) fails.

---

## Root Cause

**`server.py::_make_tool_fn()` uses a single `mode` parameter default for all backends**, but backends have incompatible mode values:

| Backend | Valid modes |
|---------|-------------|
| **Vision** | `accurate`, `fast` |
| **Paddle** | N/A (CPU only) |
| **PaddleOCR-VL** | `base`, `dynamic` |

The tool function template in `server.py:74` hardcodes `mode: str = "accurate"`:

```python
def tool(path: str, lang: str | None = None, mode: str = "accurate") -> dict:
```

This `"accurate"` is forwarded directly to the PaddleOCR-VL CLI's `--mode` flag, which rejects it.

---

## Fix Options

### Option A: Map in backend (recommended — minimal change)

In `mcp_ocr/backends/paddleocr_vl.py::_run()`, add a mode mapping before passing to CLI:

```python
_MODE_MAP = {
    "accurate": "dynamic",  # best quality → NaViT dynamic resolution
    "fast": "base",         # fast path → fixed 448×448
}

def _run(self, path: str, task: str, mode: str = "base") -> dict:
    cli_mode = _MODE_MAP.get(mode, mode)
    cmd = [self._bin, "ocr", path, "--task", cli_task, "--mode", cli_mode]
    ...
```

### Option B: Per-backend defaults in server.py (more architectural)

Change `server.py` to accept per-backend mode defaults:

```python
_BACKEND_MODE_DEFAULTS = {
    "vision": "accurate",
    "paddle": "accurate",
    "paddleocr_vl": "base",
}

def _make_tool_fn(method, backend_name: str):
    ...
    default_mode = _BACKEND_MODE_DEFAULTS.get(backend_name, "accurate")
    
    @handle_errors
    def tool(path: str, lang: str | None = None, mode: str = default_mode) -> dict:
        ...
```

### Option C: Remove mode parameter from PaddleOCR-VL tools

The simplest fix — hardcode `mode="base"` in the paddleocr_vl backend since there's no meaningful tradeoff for most use cases.

---

## Recommended Fix

**Option A** — add mode mapping in the paddleocr_vl backend. It's the smallest change, doesn't affect other backends, and provides a sensible mapping (`accurate` → `dynamic` for best quality, `fast` → `base` for speed).

Patch location: `mcp_ocr/backends/paddleocr_vl.py`, method `_run()`, line ~47.
