"""Base class for OCR backends."""

from abc import ABC, abstractmethod


class BaseOCRBackend(ABC):
    """Abstract base for OCR backends.

    Subclasses must set `name` and `tasks`, and implement
    `extract`, `layout`, and `table`. `formula` and `chart`
    default to returning EUNSUPPORTED.
    """

    name: str
    tasks: list[str]

    @abstractmethod
    def extract(self, path: str) -> dict:
        """Extract text from an image. Returns {success, text, lines}."""
        ...

    @abstractmethod
    def layout(self, path: str) -> dict:
        """Layout analysis. Returns {success, blocks}."""
        ...

    @abstractmethod
    def table(self, path: str) -> dict:
        """Table extraction. Returns {success, tables}."""
        ...

    def formula(self, path: str) -> dict:
        return {"success": False, "error": "EUNSUPPORTED",
                "detail": f"Formula extraction not supported by {self.name} backend"}

    def chart(self, path: str) -> dict:
        return {"success": False, "error": "EUNSUPPORTED",
                "detail": f"Chart extraction not supported by {self.name} backend"}
