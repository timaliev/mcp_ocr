import pytest
from mcp_ocr.backends import BACKENDS, get_backend

def test_registry_has_expected_backends():
    assert "vision" in BACKENDS
    assert "paddle" in BACKENDS
    assert "paddleocr_vl" in BACKENDS


def test_registry_backends_are_base_backend_instances():
    from mcp_ocr.backends.base import BaseOCRBackend
    for name, backend in BACKENDS.items():
        assert isinstance(backend, BaseOCRBackend), f"{name} is not a BaseOCRBackend"


def test_get_backend_returns_correct_backend():
    be = get_backend("vision")
    assert be.name == "vision"


def test_get_backend_unknown_raises():
    with pytest.raises(KeyError):
        get_backend("nonexistent")
