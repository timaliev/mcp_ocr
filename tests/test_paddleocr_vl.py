import pytest
import sys
import os
import shutil

def _has_cli():
    """Check if paddleocr-vl CLI binary is available."""
    return shutil.which("paddleocr-vl") is not None or os.environ.get("PADDLEOCR_VL_BIN", "")

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or os.uname().machine != "arm64" or not _has_cli(),
    reason="PaddleOCR-VL requires Apple Silicon + paddleocr-vl CLI"
)

from mcp_ocr.backends.paddleocr_vl import PaddleOCRVlBackend


@pytest.fixture
def backend():
    return PaddleOCRVlBackend()


@pytest.fixture
def sample_image(tmp_path):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (200, 50), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 15), "Hello World", fill="black")
    path = tmp_path / "sample.png"
    img.save(path)
    return str(path)


def test_paddleocr_vl_backend_name():
    be = PaddleOCRVlBackend()
    assert be.name == "paddleocr_vl"


def test_paddleocr_vl_backend_tasks():
    be = PaddleOCRVlBackend()
    assert "text" in be.tasks
    assert "layout" in be.tasks
    assert "table" in be.tasks
    assert "formula" in be.tasks
    assert "chart" in be.tasks


def test_paddleocr_vl_extract_returns_success(backend, sample_image):
    result = backend.extract(sample_image)
    assert result["success"] is True
    assert "text" in result
    assert "lines" in result


def test_paddleocr_vl_table_returns_tables(backend, sample_image):
    result = backend.table(sample_image)
    assert result["success"] is True
    assert "tables" in result


def test_paddleocr_vl_formula_returns_formulas(backend, sample_image):
    result = backend.formula(sample_image)
    assert result["success"] is True
    assert "formulas" in result


def test_paddleocr_vl_missing_file_returns_error(backend):
    result = backend.extract("/nonexistent/path.png")
    assert result["success"] is False


def test_paddleocr_vl_binary_not_found(tmp_path):
    """When binary doesn't exist, return ECONFIG."""
    backend = PaddleOCRVlBackend(bin_path="/nonexistent/paddleocr-vl")
    img = tmp_path / "test.png"
    from PIL import Image
    Image.new("RGB", (10, 10)).save(img)
    result = backend.extract(str(img))
    assert result["success"] is False
    assert "error" in result


def test_paddleocr_vl_extract_default_mode_completes_fast(backend, sample_image):
    """Default mode must be base (~7s), not dynamic (~150s). Completes under 30s."""
    import time
    start = time.monotonic()
    result = backend.extract(sample_image)
    elapsed = time.monotonic() - start
    assert result["success"] is True
    assert elapsed < 30, f"extract took {elapsed:.1f}s, expected < 30s (dynamic mode would be ~150s)"


def test_paddleocr_vl_extract_rejects_lang_param(backend, sample_image):
    """lang parameter was removed — CLI has no --lang support."""
    with pytest.raises(TypeError, match="lang"):
        backend.extract(sample_image, lang="ru")


def test_paddleocr_vl_layout_rejects_lang_param(backend, sample_image):
    """lang parameter was removed from layout too."""
    with pytest.raises(TypeError, match="lang"):
        backend.layout(sample_image, lang="ru")
