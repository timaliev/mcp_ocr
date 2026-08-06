"""PaddleOCR-VL backend — invokes native Swift CLI via subprocess (Apple Silicon only)."""

import os
import subprocess
import logging
from mcp_ocr.backends.base import BaseOCRBackend

logger = logging.getLogger("mcp-ocr.paddleocr-vl")

_BINARY_TIMEOUT = int(os.environ.get("PADDLEOCR_VL_TIMEOUT", "120"))


def _resolve_binary(bin_path: str | None) -> str:
    """Resolve the paddleocr-vl CLI binary path."""
    if bin_path:
        return bin_path
    env_bin = os.environ.get("PADDLEOCR_VL_BIN", "")
    if env_bin:
        return env_bin
    # Check PATH
    import shutil
    found = shutil.which("paddleocr-vl")
    if found:
        return found
    return "paddleocr-vl"  # will fail with FileNotFoundError at call time


def _map_task(task: str) -> str:
    mapping = {
        "extract": "ocr",
        "layout": "ocr",
        "table": "table",
        "formula": "formula",
        "chart": "chart",
    }
    return mapping.get(task, "ocr")


_MODE_MAP = {
    "accurate": "dynamic",  # best quality → NaViT dynamic resolution
    "fast": "base",         # fast path → fixed 448×448
}


class PaddleOCRVlBackend(BaseOCRBackend):
    name = "paddleocr_vl"
    tasks = ["text", "layout", "table", "formula", "chart"]

    def __init__(self, bin_path: str | None = None):
        self._bin = _resolve_binary(bin_path)

    def _run(self, path: str, task: str, mode: str = "base") -> dict:
        if not os.path.isfile(path):
            return {"success": False, "error": "ENOENT",
                    "detail": f"File not found: {path}"}

        cli_task = _map_task(task)
        cli_mode = _MODE_MAP.get(mode, mode)
        cmd = [self._bin, "ocr", path, "--task", cli_task, "--mode", cli_mode]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_BINARY_TIMEOUT,
            )
        except FileNotFoundError:
            return {
                "success": False,
                "error": "ECONFIG",
                "detail": (
                    "PaddleOCR-VL CLI not found. Install via: "
                    "brew install paddleocr-vl or build from "
                    "https://github.com/mlx-community/paddleocr-vl.swift"
                ),
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "ETIMEOUT",
                    "detail": f"PaddleOCR-VL timed out after {_BINARY_TIMEOUT}s"}

        if result.returncode != 0:
            return {"success": False, "error": "EPROCESSING",
                    "detail": result.stderr.strip() or "PaddleOCR-VL returned non-zero exit code"}

        return {"success": True, "raw": result.stdout.strip()}

    def extract(self, path: str, lang: str | None = None, mode: str = "base") -> dict:
        result = self._run(path, "extract", mode)
        if not result.get("success"):
            return result
        raw = result.pop("raw", "")
        lines_text = raw.split("\n")
        lines = [{"text": t, "confidence": 1.0, "bbox": []} for t in lines_text if t.strip()]
        return {"success": True, "text": raw, "lines": lines}

    def layout(self, path: str, lang: str | None = None, mode: str = "base") -> dict:
        result = self.extract(path, lang, mode)
        if not result.get("success"):
            return result
        blocks = []
        for line in result.get("lines", []):
            blocks.append({
                "type": "text",
                "text": line["text"],
                "confidence": line["confidence"],
            })
        return {"success": True, "blocks": blocks}

    def table(self, path: str, mode: str = "base") -> dict:
        result = self._run(path, "table", mode)
        if not result.get("success"):
            return result
        raw = result.pop("raw", "")
        # Parse markdown table → csv/headers/rows
        # Simple: return as single table with markdown
        return {"success": True, "tables": [{"csv": raw, "headers": [], "rows": []}]}

    def formula(self, path: str, mode: str = "base") -> dict:
        result = self._run(path, "formula", mode)
        if not result.get("success"):
            return result
        raw = result.pop("raw", "")
        return {"success": True, "formulas": [{"text": raw, "format": "latex"}]}

    def chart(self, path: str, mode: str = "base") -> dict:
        result = self._run(path, "chart", mode)
        if not result.get("success"):
            return result
        raw = result.pop("raw", "")
        return {"success": True, "charts": [{"data": raw}]}
