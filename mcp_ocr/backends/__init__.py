"""OCR backend registry."""

from mcp_ocr.backends.base import BaseOCRBackend
from mcp_ocr.backends.vision import VisionBackend
from mcp_ocr.backends.paddle import PaddleBackend
from mcp_ocr.backends.paddleocr_vl import PaddleOCRVlBackend

BACKENDS: dict[str, BaseOCRBackend] = {
    "vision": VisionBackend(),
    "paddle": PaddleBackend(),
    "paddleocr_vl": PaddleOCRVlBackend(),
}


def get_backend(name: str) -> BaseOCRBackend:
    """Look up a backend by name. Raises KeyError if not found."""
    return BACKENDS[name]
