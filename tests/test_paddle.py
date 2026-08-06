import pytest
import sys

try:
    import paddleocr
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not PADDLE_AVAILABLE, reason="Requires PaddleOCR installed"
)

from mcp_ocr.backends.paddle import PaddleBackend


@pytest.fixture
def backend():
    return PaddleBackend()


@pytest.fixture
def sample_image(tmp_path):
    """Create a small PNG with text."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (200, 50), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 15), "Hello World", fill="black")
    path = tmp_path / "sample.png"
    img.save(path)
    return str(path)


def test_paddle_backend_has_correct_name():
    be = PaddleBackend()
    assert be.name == "paddle"


def test_paddle_backend_tasks():
    be = PaddleBackend()
    assert "text" in be.tasks
    assert "layout" in be.tasks
    assert "table" in be.tasks


def test_paddle_extract_returns_success(backend, sample_image):
    result = backend.extract(sample_image, lang="en")
    assert result["success"] is True
    assert "text" in result
    assert "lines" in result


def test_paddle_extract_lines_have_required_fields(backend, sample_image):
    result = backend.extract(sample_image, lang="en")
    for line in result["lines"]:
        assert "text" in line
        assert "confidence" in line
        assert "bbox" in line


def test_paddle_layout_returns_blocks(backend, sample_image):
    result = backend.layout(sample_image, lang="en")
    assert result["success"] is True
    assert "blocks" in result


def test_paddle_missing_file_returns_error(backend):
    result = backend.extract("/nonexistent/path.png", lang="en")
    assert result["success"] is False
