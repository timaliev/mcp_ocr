from mcp_ocr.backends.base import BaseOCRBackend

class PaddleBackend(BaseOCRBackend):
    name = "paddle"
    tasks = ["text", "layout", "table"]

    def extract(self, path: str) -> dict:
        raise NotImplementedError

    def layout(self, path: str) -> dict:
        raise NotImplementedError

    def table(self, path: str) -> dict:
        raise NotImplementedError
