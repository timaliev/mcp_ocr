import pytest
from mcp_ocr.backends.base import BaseOCRBackend, ErrorCode

def test_abc_cannot_instantiate_directly():
    """BaseOCRBackend must be subclassed."""
    with pytest.raises(TypeError):
        BaseOCRBackend()

def test_concrete_backend_must_implement_abstract_methods():
    """Subclass without extract/layout/table fails."""
    class IncompleteBackend(BaseOCRBackend):
        name = "incomplete"
        tasks = ["text"]

    with pytest.raises(TypeError):
        IncompleteBackend()


class MinimalBackend(BaseOCRBackend):
    name = "minimal"
    tasks = ["text", "table"]

    def extract(self, path: str) -> dict:
        return {"success": True, "text": "hello", "lines": []}

    def layout(self, path: str) -> dict:
        return {"success": True, "blocks": []}

    def table(self, path: str) -> dict:
        return {"success": True, "tables": []}


def test_minimal_backend_instantiates():
    be = MinimalBackend()
    assert be.name == "minimal"
    assert be.tasks == ["text", "table"]


def test_minimal_backend_extract():
    be = MinimalBackend()
    result = be.extract("foo.png")
    assert result["success"] is True
    assert result["text"] == "hello"


def test_unsupported_task_returns_eunsupported():
    """Calling formula/chart on backend that only supports text/table returns EUNSUPPORTED."""
    be = MinimalBackend()
    result = be.formula("foo.png")
    assert result["success"] is False
    assert result["error"] == ErrorCode.EUNSUPPORTED
