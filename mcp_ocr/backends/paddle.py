"""PaddleOCR backend (cross-platform CPU)."""

import os
import logging
from mcp_ocr.backends.base import BaseOCRBackend

logger = logging.getLogger("mcp-ocr.paddle")

_LANG_ALIASES = {
    "russian": "ru", "rus": "ru",
    "french": "fr", "fra": "fr",
    "german": "de", "ger": "de", "deu": "de",
    "spanish": "es", "spa": "es",
    "chinese": "ch", "zh": "ch", "chi": "ch", "zho": "ch",
    "english": "en", "eng": "en",
    "korean": "ko", "kor": "ko",
    "japanese": "ja", "japan": "ja", "jpn": "ja",
    "arabic": "ar", "ara": "ar",
    "italian": "it", "ita": "it",
    "portuguese": "pt", "por": "pt",
}

_paddle_cache = {}


def _resolve_lang(lang: str | None) -> str:
    if not lang:
        return "ch"
    return _LANG_ALIASES.get(lang.lower(), lang)


def _get_paddle(lang: str):
    lang = _resolve_lang(lang)
    if lang not in _paddle_cache:
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            raise RuntimeError("PaddleOCR not installed.") from None
        _paddle_cache[lang] = PaddleOCR(lang=lang)
    return _paddle_cache[lang]


class PaddleBackend(BaseOCRBackend):
    name = "paddle"
    tasks = ["text", "layout", "table"]

    def extract(self, path: str, lang: str | None = None) -> dict:
        if not os.path.isfile(path):
            return {"success": False, "error": "ENOENT",
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
            return {"success": False, "error": "EPROCESSING", "detail": str(e)}

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
        if not os.path.isfile(path):
            return {"success": False, "error": "ENOENT",
                    "detail": f"File not found: {path}"}

        try:
            from paddleocr import PPStructure
            engine = PPStructure()
            result = engine.predict(path)

            tables = []
            for page in result:
                for item in page:
                    if hasattr(item, 'get') and item.get("type") == "table":
                        cells = item.get("res", {}).get("cells", [])
                        if cells:
                            max_row = max(c[4] for c in cells)
                            max_col = max(c[5] for c in cells)
                            grid = [[""] * (max_col + 1) for _ in range(max_row + 1)]
                            for cell in cells:
                                grid[cell[4]][cell[5]] = cell.get("text", "")
                            import csv as _csv
                            import io
                            buf = io.StringIO()
                            writer = _csv.writer(buf)
                            writer.writerows(grid)
                            tables.append({
                                "csv": buf.getvalue().strip(),
                                "headers": grid[0] if grid else [],
                                "rows": grid[1:] if len(grid) > 1 else [],
                            })
            return {"success": True, "tables": tables}
        except ImportError:
            return {"success": False, "error": "EUNSUPPORTED",
                    "detail": "PPStructure not available."}
        except Exception as e:
            logger.exception("PaddleOCR table extraction failed")
            return {"success": False, "error": "EPROCESSING", "detail": str(e)}
