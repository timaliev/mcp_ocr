import pytest
import os
import sys

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="Vision backend requires macOS")

from mcp_ocr.backends.vision import VisionBackend, _resolve_vision_langs
from mcp_ocr.backends.base import ErrorCode


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
    assert result["error"] == ErrorCode.ENOENT


def test_vision_tasks_declared():
    backend = VisionBackend()
    assert "text" in backend.tasks
    assert "layout" in backend.tasks
    assert "table" in backend.tasks


class _FakeRequest:
    """Records the request configuration so tests can assert on it."""

    def __init__(self):
        self.revision = None
        self.level = None
        self.languages = None

    def init(self):
        return self

    def setRevision_(self, value):
        self.revision = value

    def setRecognitionLevel_(self, value):
        self.level = value

    def setUsesLanguageCorrection_(self, value):
        pass

    def setRecognitionLanguages_(self, value):
        self.languages = list(value)

    def results(self):
        return []


class _FakeVision:
    VNRequestTextRecognitionLevelAccurate = "accurate"
    VNRequestTextRecognitionLevelFast = "fast"
    VNRecognizeTextRequestRevision2 = 2
    VNRecognizeTextRequestRevision3 = 3

    def __init__(self):
        self.last_request = None

    @property
    def VNRecognizeTextRequest(self):
        outer = self
        backend = self

        class _Request(_FakeRequest):
            @classmethod
            def alloc(cls):
                request = _Request()
                backend.last_request = request
                return request

        return _Request

    class VNImageRequestHandler:
        @classmethod
        def alloc(cls):
            return cls()

        def initWithCGImage_options_(self, image, options):
            return self

        def performRequests_error_(self, requests, error):
            return True, None


def _fake_vision(monkeypatch):
    fake = _FakeVision()
    monkeypatch.setitem(sys.modules, "Vision", fake)
    backend = VisionBackend()
    monkeypatch.setattr(backend, "_load_image", lambda path: (object(), None))
    return backend, fake


def test_base_mode_uses_accurate_recognizer_and_language(monkeypatch):
    backend, fake = _fake_vision(monkeypatch)

    result = backend.extract("page.png", lang="russian", mode="base")

    assert result["success"] is True
    assert fake.last_request.level == "accurate"
    assert fake.last_request.languages == ["ru-RU", "en-US"]


def test_fast_mode_uses_fast_recognizer(monkeypatch):
    backend, fake = _fake_vision(monkeypatch)

    backend.extract("page.png", mode="fast")

    assert fake.last_request.level == "fast"


def test_table_reports_missing_vision_api_truthfully(monkeypatch, tmp_path):
    _fake_vision(monkeypatch)
    image = tmp_path / "page.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    backend = VisionBackend()

    result = backend.table(str(image))

    assert result["success"] is False
    assert result["error"] == ErrorCode.EUNSUPPORTED
    assert "VNRecognizeDocumentsRequest" in result["detail"]
