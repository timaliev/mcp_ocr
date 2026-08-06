import pytest
import os
import sys

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="Vision backend requires macOS")

from mcp_ocr.backends.vision import VisionBackend


@pytest.fixture
def backend():
    return VisionBackend()


@pytest.fixture
def sample_image(tmp_path):
    """Create a small PNG with text using PIL."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (200, 50), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 15), "Hello World", fill="black")
    path = tmp_path / "sample.png"
    img.save(path)
    return str(path)


def test_vision_extract_returns_success(backend, sample_image):
    result = backend.extract(sample_image)
    assert result["success"] is True
    assert "text" in result
    assert "lines" in result


def test_vision_extract_lines_have_required_fields(backend, sample_image):
    result = backend.extract(sample_image)
    for line in result["lines"]:
        assert "text" in line
        assert "confidence" in line
        assert "bbox" in line


def test_vision_layout_returns_blocks(backend, sample_image):
    result = backend.layout(sample_image)
    assert result["success"] is True
    assert "blocks" in result


def test_vision_missing_file_returns_error(backend):
    result = backend.extract("/nonexistent/path.png")
    assert result["success"] is False
    assert result["error"] == "EIMAGE"


def test_vision_tasks_declared():
    backend = VisionBackend()
    assert "text" in backend.tasks
    assert "layout" in backend.tasks
    assert "table" in backend.tasks
