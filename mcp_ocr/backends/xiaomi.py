"""Xiaomi-OCR-0 backend — 0.8B document-parsing VLM (transformers, MPS/CUDA/CPU).

Parses a document page to Markdown (tables as OTSL, formulas as LaTeX), extracts
key fields as JSON, and answers OCR-centric questions. Inference is local and
loaded lazily on first use so the MCP server starts instantly.

Environment:
    XIAOMI_OCR_MODEL   model id or local directory (default xiaomi-research/Xiaomi-OCR-0)
    XIAOMI_OCR_DEVICE  mps | cuda | cpu (default: auto-detect)
    XIAOMI_OCR_MAX_TOKENS  generation budget (default 4096)
"""

from __future__ import annotations

import json
import os
import re
import threading

from mcp_ocr.backends.base import BaseOCRBackend, ErrorCode
from mcp_ocr.otsl import markdown_with_html_tables, otsl_to_html, parse_otsl

DEFAULT_MODEL = "xiaomi-research/Xiaomi-OCR-0"
MAX_TOKENS = int(os.environ.get("XIAOMI_OCR_MAX_TOKENS", "4096"))

DOCUMENT_PROMPT = (
    "Extract all information from the main body of the document image and represent it "
    "in markdown format, ignoring headers and footers. Tables should be expressed in OTSL "
    "format, formulas in the document should be represented using LATEX format, and the "
    "parsing should be organized according to the reading order."
)
TEXT_PROMPT = "Extract the text in the image."
TABLE_PROMPT = "Parse the table in the image into OTSL."
FORMULA_PROMPT = "Identify the formula in the image and represent it using LATEX format."
KIE_PROMPT = "Extract key information in the image"

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


class _Runtime:
    """Lazily loaded model + processor, shared by all calls in the process."""

    _lock = threading.Lock()
    _instance = None

    def __init__(self) -> None:
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        model_id = os.environ.get("XIAOMI_OCR_MODEL", DEFAULT_MODEL)
        device = os.environ.get("XIAOMI_OCR_DEVICE") or self._auto_device(torch)
        dtype = torch.float32 if device == "cpu" else torch.float16

        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = (
            AutoModelForImageTextToText.from_pretrained(model_id, dtype=dtype)
            .to(device)
            .eval()
        )
        self.torch = torch
        self.device = device

    @staticmethod
    def _auto_device(torch) -> str:
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    @classmethod
    def get(cls) -> "_Runtime":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def generate(self, path: str, prompt: str, max_tokens: int) -> str:
        from PIL import Image

        image = Image.open(path).convert("RGB")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = {
            key: value.to(self.device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }
        with self.torch.inference_mode():
            generated = self.model.generate(
                **inputs, max_new_tokens=max_tokens, do_sample=False
            )
        new_tokens = generated[:, inputs["input_ids"].shape[1] :]
        return self.processor.batch_decode(new_tokens, skip_special_tokens=True)[0]


def default_generator(path: str, prompt: str, max_tokens: int) -> str:
    """Run one request against the local model."""
    return _Runtime.get().generate(path, prompt, max_tokens)


class XiaomiBackend(BaseOCRBackend):
    """Document parsing and OCR-centric understanding via Xiaomi-OCR-0."""

    name = "xiaomi"
    tasks = ["text", "layout", "table", "formula", "document", "kie"]

    def __init__(self, generator=None) -> None:
        self._generator = generator or default_generator

    # -- helpers ---------------------------------------------------------
    def _model_text(self, path: str, prompt: str, max_tokens: int = MAX_TOKENS):
        """Return model text, or an error dict when the call cannot be made."""
        if not os.path.isfile(path):
            return {
                "success": False,
                "error": ErrorCode.ENOENT,
                "detail": f"File not found: {path}",
            }
        try:
            return self._generator(path, prompt, max_tokens)
        except ImportError as exc:
            return {
                "success": False,
                "error": ErrorCode.ECONFIG,
                "detail": (
                    "Xiaomi-OCR-0 dependencies are missing. Install with: "
                    "uv tool install 'mcp-ocr[xiaomi]' "
                    f"({exc})"
                ),
            }
        except Exception as exc:  # model load or inference failure
            return {
                "success": False,
                "error": ErrorCode.EPROCESSING,
                "detail": f"Xiaomi-OCR-0 inference failed: {exc}",
            }

    @staticmethod
    def _lines(text: str) -> list[dict]:
        return [
            {"text": line.strip(), "confidence": 1.0, "bbox": []}
            for line in text.splitlines()
            if line.strip()
        ]

    # -- tasks -----------------------------------------------------------
    def extract(self, path: str) -> dict:
        text = self._model_text(path, TEXT_PROMPT)
        if isinstance(text, dict):
            return text
        lines = self._lines(text)
        return {"success": True, "text": text.strip(), "lines": lines}

    def layout(self, path: str) -> dict:
        result = self.extract(path)
        if not result.get("success"):
            return result
        blocks = [
            {"type": "text", "text": line["text"], "confidence": line["confidence"]}
            for line in result["lines"]
        ]
        return {"success": True, "blocks": blocks}

    def document(self, path: str) -> dict:
        text = self._model_text(path, DOCUMENT_PROMPT)
        if isinstance(text, dict):
            return text
        markdown = markdown_with_html_tables(text.strip())
        return {"success": True, "markdown": markdown}

    def table(self, path: str) -> dict:
        text = self._model_text(path, TABLE_PROMPT, MAX_TOKENS)
        if isinstance(text, dict):
            return text
        otsl = text.strip()
        if "<fcel>" not in otsl and "<ecel>" not in otsl:
            return {
                "success": False,
                "error": ErrorCode.EPROCESSING,
                "detail": "Model output did not contain an OTSL table",
            }
        rows = parse_otsl(otsl)
        return {
            "success": True,
            "tables": [
                {
                    "csv": "\n".join(",".join(_csv_cell(cell) for cell in row) for row in rows),
                    "headers": rows[0] if rows else [],
                    "rows": rows[1:] if len(rows) > 1 else [],
                    "otsl": otsl,
                    "html": otsl_to_html(otsl),
                }
            ],
        }

    def formula(self, path: str) -> dict:
        text = self._model_text(path, FORMULA_PROMPT)
        if isinstance(text, dict):
            return text
        return {"success": True, "latex": text.strip(), "text": text.strip()}

    def kie(self, path: str, fields: list[str] | None = None) -> dict:
        prompt = KIE_PROMPT
        if fields:
            schema = {field: "" for field in fields}
            prompt = (
                f"{KIE_PROMPT}\n\n"
                "Please output the key information in JSON format according to the "
                f"following schema:\n{json.dumps(schema, ensure_ascii=False, indent=4)}"
            )
        text = self._model_text(path, prompt)
        if isinstance(text, dict):
            return text
        parsed = _parse_json_object(text)
        if parsed is None:
            return {
                "success": False,
                "error": ErrorCode.EPROCESSING,
                "detail": "Model output is not a JSON object",
                "raw": text,
            }
        return {"success": True, "data": parsed, "raw": text}


def _csv_cell(value: str) -> str:
    if any(character in value for character in (',', '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value


def _parse_json_object(text: str):
    """Extract the first JSON object from model output (code fences allowed)."""
    cleaned = _FENCE_RE.sub("", text.strip())
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None
