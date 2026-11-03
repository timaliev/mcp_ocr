import pytest
from mcp_ocr.backends import BACKENDS, get_backend


def test_registry_has_expected_backends():
    assert "vision" in BACKENDS
    assert "paddle" in BACKENDS
    assert "xiaomi" in BACKENDS


def test_registry_has_no_removed_backends():
    """PaddleOCR-VL was removed: it hung and exhausted memory without usable output."""
    assert "paddleocr_vl" not in BACKENDS


def test_registry_backends_are_base_backend_instances():
    from mcp_ocr.backends.base import BaseOCRBackend
    for name, backend in BACKENDS.items():
        assert isinstance(backend, BaseOCRBackend), f"{name} is not a BaseOCRBackend"


def test_get_backend_returns_correct_backend():
    be = get_backend("vision")
    assert be.name == "vision"
    assert get_backend("xiaomi").name == "xiaomi"


def test_get_backend_unknown_raises():
    with pytest.raises(KeyError):
        get_backend("nonexistent")


def test_xiaomi_backend_declares_document_and_kie_tasks():
    backend = get_backend("xiaomi")
    assert backend.tasks == ["text", "layout", "table", "formula", "document", "kie"]
