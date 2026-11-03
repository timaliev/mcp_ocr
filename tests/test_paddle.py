import pytest
import sys

try:
    import paddleocr
    _PADDLE_AVAILABLE = True
except ImportError:
    _PADDLE_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _PADDLE_AVAILABLE, reason="Requires PaddleOCR installed"
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


# --- table extraction via the PaddleOCR 3.x structure pipeline -----------------

import sys
import types

from mcp_ocr.backends.base import ErrorCode


class _FakeResult:
    def __init__(self, payload):
        self.json = payload


class _FakePPStructureV3:
    def __init__(self, *args, **kwargs):
        pass

    def predict(self, path):
        return [
            _FakeResult(
                {
                    "res": {
                        "table_res_list": [
                            {
                                "pred_html": (
                                    "<table><tr><td>Наименование</td>"
                                    "<td>Сумма</td></tr>"
                                    "<tr><td>Сервер</td><td>100</td></tr></table>"
                                )
                            }
                        ]
                    }
                }
            )
        ]


def _fake_paddleocr(monkeypatch, **attributes):
    module = types.ModuleType("paddleocr")
    for name, value in attributes.items():
        setattr(module, name, value)
    monkeypatch.setitem(sys.modules, "paddleocr", module)
    return module


def test_paddle_table_parses_structure_output(monkeypatch, tmp_path):
    image = tmp_path / "table.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    _fake_paddleocr(monkeypatch, PPStructureV3=_FakePPStructureV3)

    result = PaddleBackend().table(str(image))

    assert result["success"] is True
    table = result["tables"][0]
    assert table["headers"] == ["Наименование", "Сумма"]
    assert table["rows"] == [["Сервер", "100"]]


def test_paddle_table_without_structure_api_is_unsupported(monkeypatch, tmp_path):
    image = tmp_path / "table.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    _fake_paddleocr(monkeypatch)

    result = PaddleBackend().table(str(image))

    assert result["success"] is False
    assert result["error"] == ErrorCode.EUNSUPPORTED
    assert "PPStructureV3" in result["detail"]


def test_paddle_table_missing_file_is_enoent(monkeypatch):
    _fake_paddleocr(monkeypatch, PPStructureV3=_FakePPStructureV3)

    result = PaddleBackend().table("/nonexistent/table.png")

    assert result["success"] is False
    assert result["error"] == ErrorCode.ENOENT
