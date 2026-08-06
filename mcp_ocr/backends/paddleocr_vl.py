from mcp_ocr.backends.base import BaseOCRBackend

class PaddleOCRVlBackend(BaseOCRBackend):
    name = "paddleocr_vl"
    tasks = ["text", "layout", "table", "formula", "chart"]

    def extract(self, path: str) -> dict:
        raise NotImplementedError

    def layout(self, path: str) -> dict:
        raise NotImplementedError

    def table(self, path: str) -> dict:
        raise NotImplementedError
