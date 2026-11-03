"""PaddleOCR backend (cross-platform CPU)."""

import csv
import io
import os
import logging
from mcp_ocr.backends.base import BaseOCRBackend, ErrorCode
from mcp_ocr.backends.lang import resolve_lang_code
from mcp_ocr.html_table import parse_html_table

logger = logging.getLogger("mcp-ocr.paddle")

_paddle_cache = {}


def _resolve_lang(lang: str | None) -> str:
    return resolve_lang_code(lang, "en")


def _get_paddle(lang: str):
    lang = _resolve_lang(lang)
    if lang not in _paddle_cache:
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            raise RuntimeError("PaddleOCR not installed.") from None
        _paddle_cache[lang] = PaddleOCR(lang=lang)
    return _paddle_cache[lang]


def _collect_pred_html(value, depth: int = 0) -> list[str]:
    """Collect every ``pred_html`` string inside a PaddleX result tree."""
    if depth > 8:
        return []
    payload = getattr(value, "json", None)
    if payload is not None:
        # PaddleX exposes ``json`` as a property; tolerate a callable too.
        return _collect_pred_html(payload() if callable(payload) else payload, depth + 1)
    if isinstance(value, dict):
        found = []
        for key, item in value.items():
            if key == "pred_html" and isinstance(item, str):
                found.append(item)
            else:
                found.extend(_collect_pred_html(item, depth + 1))
        return found
    if isinstance(value, (list, tuple)):
        found = []
        for item in value:
            found.extend(_collect_pred_html(item, depth + 1))
        return found
    return []


def _table_record(rows: list[list[str]]) -> dict:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    return {
        "csv": buffer.getvalue().strip(),
        "headers": rows[0] if rows else [],
        "rows": rows[1:] if len(rows) > 1 else [],
    }


class PaddleBackend(BaseOCRBackend):
    name = "paddle"
    tasks = ["text", "layout", "table"]

    def extract(self, path: str, lang: str | None = None) -> dict:
        if not os.path.isfile(path):
            return {"success": False, "error": ErrorCode.ENOENT,
                    "detail": f"File not found: {path}"}

        try:
            ocr = _get_paddle(lang or "en")
            result = ocr.predict(path)
            if not result or len(result) == 0:
                return {"success": True, "text": "", "lines": []}

            page = result[0]
            rec_texts = page.get("rec_texts", [])
            rec_scores = page.get("rec_scores", [])
            dt_polys = page.get("dt_polys", [])

            lines = []
            for i, (text, score) in enumerate(zip(rec_texts, rec_scores)):
                bbox = []
                if i < len(dt_polys):
                    poly = dt_polys[i]
                    bbox = [round(float(c), 1) for pt in poly for c in pt]
                lines.append({"text": text, "confidence": round(score, 4), "bbox": bbox})

            return {"success": True, "text": "\n".join(rec_texts), "lines": lines}
        except Exception as e:
            logger.exception("PaddleOCR extract failed")
            return {"success": False, "error": ErrorCode.EPROCESSING, "detail": str(e)}

    def layout(self, path: str, lang: str | None = None) -> dict:
        result = self.extract(path, lang)
        if not result.get("success"):
            return result
        blocks = []
        for line in result.get("lines", []):
            bb = line["bbox"]
            block = {"type": "text", "text": line["text"],
                     "confidence": line["confidence"]}
            if bb and len(bb) >= 4:
                block.update({"x": bb[0], "y": bb[1],
                              "width": bb[2] - bb[0] if len(bb) >= 4 else 0,
                              "height": bb[3] - bb[1] if len(bb) >= 4 else 0})
            blocks.append(block)
        return {"success": True, "blocks": blocks}

    def table(self, path: str) -> dict:
        """Extract table structure with PaddleOCR 3.x ``PPStructureV3``."""
        if not os.path.isfile(path):
            return {"success": False, "error": ErrorCode.ENOENT,
                    "detail": f"File not found: {path}"}

        try:
            from paddleocr import PPStructureV3
        except ImportError:
            return {
                "success": False,
                "error": ErrorCode.EUNSUPPORTED,
                "detail": (
                    "Table extraction requires PaddleOCR>=3.0 (PPStructureV3). "
                    "Upgrade with: uv pip install -U paddleocr"
                ),
            }

        try:
            engine = PPStructureV3()
            predictions = engine.predict(path)
            tables = [
                _table_record(parse_html_table(html))
                for html in _collect_pred_html(predictions)
            ]
            return {"success": True, "tables": [t for t in tables if t["headers"] or t["rows"]]}
        except Exception as e:
            logger.exception("PaddleOCR table extraction failed")
            return {"success": False, "error": ErrorCode.EPROCESSING, "detail": str(e)}
