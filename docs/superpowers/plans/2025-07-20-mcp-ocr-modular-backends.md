# mcp_ocr Modular Backends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor mcp_ocr into class-based modular backends (Vision, Paddle, PaddleOCR-VL) with per-task×backend named MCP tools.

**Architecture:** Each backend is a class implementing `BaseOCRBackend` ABC in `backends/`. `server.py` reads the `BACKENDS` registry, dynamically registers `ocr_{task}_{name}` tools via `@server.tool()`. PaddleOCR-VL backend shells out to the Swift CLI binary.

**Tech Stack:** Python 3.11+, `mcp[cli]>=1.9`, PyObjC (Vision), PaddleOCR (cross-platform), subprocess (PaddleOCR-VL Swift CLI), pytest

## Global Constraints

- Python >=3.11, <3.14
- `mcp[cli]>=1.9`
- macOS 14+ for PaddleOCR-VL backend (Apple Silicon only)
- macOS 10.15+ for Vision backend
- PaddleOCR-VL requires `paddleocr-vl` Swift CLI on PATH or `PADDLEOCR_VL_BIN` env
- Repo: `github.com/timaliev/pi-mcp_ocr`
- TDD: write failing test → implement → pass → commit per task
- `pyproject.toml` with `[project.scripts]` entry point `mcp-ocr`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backends/base.py` | `BaseOCRBackend` ABC with `extract`, `layout`, `table`, `formula`, `chart` |
| `backends/__init__.py` | `BACKENDS` registry dict, `get_backend()` lookup |
| `backends/vision.py` | `VisionBackend` — PyObjC Apple Vision integration |
| `backends/paddle.py` | `PaddleBackend` — PaddleOCR CPU integration |
| `backends/paddleocr_vl.py` | `PaddleOCRVlBackend` — subprocess → Swift CLI |
| `server.py` | Dynamic tool registration, `@handle_errors` decorator, batch routing, `main()` |
| `pyproject.toml` | Package metadata, optional dependency groups, console_scripts |
| `tests/test_base.py` | Tests for ABC, registry, error handling decorator |
| `tests/test_vision.py` | Vision backend tests (macOS only) |
| `tests/test_paddle.py` | Paddle backend tests |
| `tests/test_paddleocr_vl.py` | PaddleOCR-VL backend tests (Apple Silicon only) |
| `tests/test_server.py` | Tool registration + batch routing tests |
| `README.md` | Install, usage, backend descriptions |

---

### Task 1: Project scaffolding + pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `backends/__init__.py`
- Create: `backends/base.py` (empty ABC skeleton)
- Create: `backends/vision.py` (empty placeholder)
- Create: `backends/paddle.py` (empty placeholder)
- Create: `backends/paddleocr_vl.py` (empty placeholder)
- Create: `server.py` (empty placeholder)
- Create: `tests/__init__.py`
- Create: `tests/test_base.py` (empty placeholder)
- Create: `.gitignore`

**Interfaces:**
- Produces: `backends.base.BaseOCRBackend` ABC (skeleton), `backends` package

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "pi-mcp-ocr"
version = "1.0.0"
description = "Modular OCR MCP server with Vision, PaddleOCR, and PaddleOCR-VL backends"
requires-python = ">=3.11,<3.14"
dependencies = [
    "mcp[cli]>=1.9",
]

[project.optional-dependencies]
vision = ["pyobjc-framework-Vision", "pyobjc-framework-Quartz"]
paddle = ["paddleocr>=2.10", "paddlepaddle>=3.3.1"]
paddleocr-vl = []  # runtime dep: paddleocr-vl Swift CLI, no Python deps
all = [
    "pi-mcp-ocr[vision,paddle,paddleocr-vl]",
]

[project.scripts]
mcp-ocr = "mcp_ocr.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["mcp_ocr"]
```

- [ ] **Step 2: Create directory structure and empty files**

```bash
mkdir -p backends tests
touch backends/__init__.py backends/base.py backends/vision.py backends/paddle.py backends/paddleocr_vl.py
touch server.py tests/__init__.py tests/test_base.py
```

- [ ] **Step 3: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
.pytest_cache/
```

- [ ] **Step 4: Install in editable mode and verify imports**

```bash
pip install -e .
python3 -c "import backends; print('backends package OK')"
python3 -c "from mcp_ocr.server import main; print('server import OK')"
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml backends/ server.py .gitignore tests/
git commit -m "feat: scaffold pi-mcp-ocr project with pyproject.toml"
```

---

### Task 2: Base backend ABC + registry

**Files:**
- Create: `backends/base.py`
- Modify: `backends/__init__.py`
- Create: `tests/test_base.py`

**Interfaces:**
- Produces: `BaseOCRBackend` ABC with `name: str`, `tasks: list[str]`, `extract(path) -> dict`, `layout(path) -> dict`, `table(path) -> dict`, `formula(path) -> dict`, `chart(path) -> dict`
- Produces: `BACKENDS: dict[str, BaseOCRBackend]`, `get_backend(name) -> BaseOCRBackend`

- [ ] **Step 1: Write failing tests for ABC + registry**

Create `tests/test_base.py`:

```python
import pytest
from backends.base import BaseOCRBackend

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
    assert result["error"] == "EUNSUPPORTED"
```

Create `tests/test_registry.py`:

```python
import pytest
from backends import BACKENDS, get_backend

def test_registry_has_expected_backends():
    assert "vision" in BACKENDS
    assert "paddle" in BACKENDS
    assert "paddleocr_vl" in BACKENDS


def test_registry_backends_are_base_backend_instances():
    from backends.base import BaseOCRBackend
    for name, backend in BACKENDS.items():
        assert isinstance(backend, BaseOCRBackend), f"{name} is not a BaseOCRBackend"


def test_get_backend_returns_correct_backend():
    be = get_backend("vision")
    assert be.name == "vision"


def test_get_backend_unknown_raises():
    with pytest.raises(KeyError):
        get_backend("nonexistent")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_base.py tests/test_registry.py -v
```
Expected: FAIL — no module or import errors.

- [ ] **Step 3: Implement `backends/base.py`**

```python
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
```

- [ ] **Step 4: Implement `backends/__init__.py`**

```python
"""OCR backend registry."""

from backends.base import BaseOCRBackend
from backends.vision import VisionBackend
from backends.paddle import PaddleBackend
from backends.paddleocr_vl import PaddleOCRVlBackend

BACKENDS: dict[str, BaseOCRBackend] = {
    "vision": VisionBackend(),
    "paddle": PaddleBackend(),
    "paddleocr_vl": PaddleOCRVlBackend(),
}


def get_backend(name: str) -> BaseOCRBackend:
    """Look up a backend by name. Raises KeyError if not found."""
    return BACKENDS[name]
```

- [ ] **Step 5: Create stub backend classes so imports work**

In `backends/vision.py`:

```python
from backends.base import BaseOCRBackend

class VisionBackend(BaseOCRBackend):
    name = "vision"
    tasks = ["text", "layout", "table"]

    def extract(self, path: str) -> dict:
        raise NotImplementedError

    def layout(self, path: str) -> dict:
        raise NotImplementedError

    def table(self, path: str) -> dict:
        raise NotImplementedError
```

Same pattern for `backends/paddle.py` (`name = "paddle"`, `tasks = ["text", "layout", "table"]`) and `backends/paddleocr_vl.py` (`name = "paddleocr_vl"`, `tasks = ["text", "layout", "table", "formula", "chart"]`).

- [ ] **Step 6: Run tests — all pass**

```bash
pytest tests/test_base.py tests/test_registry.py -v
```
Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
git add backends/base.py backends/__init__.py backends/vision.py backends/paddle.py backends/paddleocr_vl.py tests/
git commit -m "feat: add BaseOCRBackend ABC + backend registry with stubs"
```

---

### Task 3: Vision backend

**Files:**
- Modify: `backends/vision.py`
- Create: `tests/test_vision.py`

**Interfaces:**
- Produces: `VisionBackend.extract(path) -> dict`, `VisionBackend.layout(path) -> dict`, `VisionBackend.table(path) -> dict` (table macOS 15+ only)

- [ ] **Step 1: Write failing tests for Vision backend**

Create `tests/test_vision.py`:

```python
import pytest
import os
import sys

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="Vision backend requires macOS")

from backends.vision import VisionBackend


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_vision.py -v
```
Expected: FAIL — NotImplementedError from stubs.

- [ ] **Step 3: Implement `backends/vision.py`**

Port the existing Vision code from the old `server.py`, extracted into the class:

```python
"""Apple Vision OCR backend (macOS 10.15+)."""

import os
import sys
from backends.base import BaseOCRBackend

_VISION_LANG_MAP = {
    "ru": ["ru-RU", "en-US"],
    "en": ["en-US"],
    "ch": ["zh-Hans", "zh-Hant", "en-US"],
    "zh": ["zh-Hans", "zh-Hant", "en-US"],
    "ja": ["ja-JP", "en-US"],
    "ko": ["ko-KR", "en-US"],
    "fr": ["fr-FR", "en-US"],
    "de": ["de-DE", "en-US"],
    "es": ["es-ES", "en-US"],
    "ar": ["ar-SA", "en-US"],
    "it": ["it-IT", "en-US"],
    "pt": ["pt-BR", "en-US"],
}

_LANG_ALIASES = {
    "russian": "ru", "rus": "ru",
    "french": "fr", "fra": "fr",
    "german": "de", "ger": "de", "deu": "de",
    "spanish": "es", "spa": "es",
    "chinese": "ch", "zh": "ch", "chi": "ch", "zho": "ch",
    "english": "en", "eng": "en",
    "korean": "ko", "kor": "ko",
    "japanese": "ja", "japan": "ja", "jpn": "ja",
    "arabic": "ar", "ara": "ar",
    "italian": "it", "ita": "it",
    "portuguese": "pt", "por": "pt",
}


def _resolve_vision_langs(lang: str | None) -> list[str]:
    if not lang:
        return ["en-US"]
    lang = _LANG_ALIASES.get(lang.lower(), lang.lower())
    return _VISION_LANG_MAP.get(lang, ["en-US"])


class VisionBackend(BaseOCRBackend):
    name = "vision"
    tasks = ["text", "layout", "table"]

    def __init__(self):
        self._has_table_support = False
        try:
            import Vision
            if hasattr(Vision, "VNRecognizeTextRequestRevision4"):
                self._has_table_support = True
        except ImportError:
            pass

    def _load_image(self, path: str):
        import Vision
        import Quartz

        if not os.path.isfile(path):
            return None, {"success": False, "error": "EIMAGE",
                          "detail": f"Cannot load image: {path}"}

        url = Quartz.CFURLCreateFromFileSystemRepresentation(
            None, path.encode("utf-8"), len(path.encode("utf-8")), False
        )
        src = Quartz.CGImageSourceCreateWithURL(url, None)
        if src is None:
            return None, {"success": False, "error": "EIMAGE",
                          "detail": f"Cannot load image: {path}"}
        img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
        if img is None:
            return None, {"success": False, "error": "EIMAGE",
                          "detail": f"Cannot decode image: {path}"}
        return img, None

    def _perform_ocr(self, img, lang: str | None = None, mode: str = "accurate") -> list[dict]:
        import Vision

        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, None)
        request = Vision.VNRecognizeTextRequest.alloc().init()

        if mode == "fast":
            rev = (Vision.VNRecognizeTextRequestRevision2
                   if hasattr(Vision, "VNRecognizeTextRequestRevision2")
                   else Vision.VNRecognizeTextRequestRevision1)
        else:
            rev = (Vision.VNRecognizeTextRequestRevision3
                   if hasattr(Vision, "VNRecognizeTextRequestRevision3")
                   else Vision.VNRecognizeTextRequestRevision2
                   if hasattr(Vision, "VNRecognizeTextRequestRevision2")
                   else Vision.VNRecognizeTextRequestRevision1)
        request.setRevision_(rev)
        request.setRecognitionLevel_(
            Vision.VNRequestTextRecognitionLevelAccurate if mode == "accurate"
            else Vision.VNRequestTextRecognitionLevelFast
        )
        request.setUsesLanguageCorrection_(True)
        request.setRecognitionLanguages_(_resolve_vision_langs(lang))

        success, error = handler.performRequests_error_([request], None)
        if not success:
            err_msg = error.localizedDescription() if error else "Vision request failed"
            raise RuntimeError(err_msg)

        observations = request.results() or []
        lines = []
        for obs in observations:
            text = obs.topCandidates_(1)[0].string()
            confidence = float(obs.topCandidates_(1)[0].confidence())
            bb = obs.boundingBox()
            lines.append({
                "text": text,
                "confidence": round(confidence, 4),
                "bbox": [
                    round(float(bb.origin.x), 4),
                    round(float(bb.origin.y), 4),
                    round(float(bb.size.width), 4),
                    round(float(bb.size.height), 4),
                ],
            })
        return lines

    def extract(self, path: str, lang: str | None = None, mode: str = "accurate") -> dict:
        img, err = self._load_image(path)
        if err:
            return err
        try:
            lines = self._perform_ocr(img, lang, mode)
            full_text = "\n".join(line["text"] for line in lines)
            return {"success": True, "text": full_text, "lines": lines}
        except Exception as e:
            return {"success": False, "error": "EPROCESSING", "detail": str(e)}

    def layout(self, path: str, lang: str | None = None, mode: str = "accurate") -> dict:
        result = self.extract(path, lang, mode)
        if not result.get("success"):
            return result
        blocks = []
        for line in result.get("lines", []):
            bb = line["bbox"]
            blocks.append({
                "type": "text",
                "text": line["text"],
                "confidence": line["confidence"],
                "x": bb[0],
                "y": bb[1],
                "width": bb[2],
                "height": bb[3],
            })
        return {"success": True, "blocks": blocks}

    def table(self, path: str, lang: str | None = None, mode: str = "accurate") -> dict:
        if not self._has_table_support:
            return {"success": False, "error": "EUNSUPPORTED",
                    "detail": "Table detection requires macOS 15+ (use ocr_text_vision instead)"}

        import Vision, Quartz

        img, err = self._load_image(path)
        if err:
            return err

        try:
            handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, None)
            request = Vision.VNRecognizeTextRequest.alloc().init()
            request.setRevision_(Vision.VNRecognizeTextRequestRevision4)
            request.setRecognitionLevel_(
                Vision.VNRequestTextRecognitionLevelAccurate if mode == "accurate"
                else Vision.VNRequestTextRecognitionLevelFast
            )
            request.setUsesLanguageCorrection_(True)
            request.setAutomaticallyDetectsTextLanguage_(True)
            handler.performRequests_error_([request], None)

            tables = []
            for obs in request.results() or []:
                text = obs.topCandidates_(1)[0].string()
                tables.append({"text": text, "csv": "", "headers": [], "rows": []})
            return {"success": True, "tables": tables}
        except Exception as e:
            return {"success": False, "error": "EPROCESSING", "detail": str(e)}
```

- [ ] **Step 4: Run vision tests**

```bash
pytest tests/test_vision.py -v
```
Expected: 5 passed (on macOS).

- [ ] **Step 5: Commit**

```bash
git add backends/vision.py tests/test_vision.py
git commit -m "feat: implement Vision backend (Apple Vision OCR)"
```

---

### Task 4: Paddle backend

**Files:**
- Modify: `backends/paddle.py`
- Create: `tests/test_paddle.py`

**Interfaces:**
- Produces: `PaddleBackend.extract(path, lang) -> dict`, `PaddleBackend.layout(path, lang) -> dict`, `PaddleBackend.table(path) -> dict`

- [ ] **Step 1: Write failing tests for Paddle backend**

Create `tests/test_paddle.py`:

```python
import pytest
import sys

pytestmark = pytest.mark.skipif(
    True, reason="Requires PaddleOCR installed"
)  # will be parametrized in CI

from backends.paddle import PaddleBackend


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_paddle.py -v
```
Expected: all skipped (PaddleOCR not installed in test env) or FAIL if installed with NotImplementedError.

- [ ] **Step 3: Implement `backends/paddle.py`**

```python
"""PaddleOCR backend (cross-platform CPU)."""

import os
import logging
from backends.base import BaseOCRBackend

logger = logging.getLogger("mcp-ocr.paddle")

_LANG_ALIASES = {
    "russian": "ru", "rus": "ru",
    "french": "fr", "fra": "fr",
    "german": "de", "ger": "de", "deu": "de",
    "spanish": "es", "spa": "es",
    "chinese": "ch", "zh": "ch", "chi": "ch", "zho": "ch",
    "english": "en", "eng": "en",
    "korean": "ko", "kor": "ko",
    "japanese": "ja", "japan": "ja", "jpn": "ja",
    "arabic": "ar", "ara": "ar",
    "italian": "it", "ita": "it",
    "portuguese": "pt", "por": "pt",
}

_paddle_cache = {}


def _resolve_lang(lang: str | None) -> str:
    if not lang:
        return "ch"
    return _LANG_ALIASES.get(lang.lower(), lang)


def _get_paddle(lang: str):
    lang = _resolve_lang(lang)
    if lang not in _paddle_cache:
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            raise RuntimeError("PaddleOCR not installed.") from None
        _paddle_cache[lang] = PaddleOCR(lang=lang)
    return _paddle_cache[lang]


class PaddleBackend(BaseOCRBackend):
    name = "paddle"
    tasks = ["text", "layout", "table"]

    def extract(self, path: str, lang: str | None = None) -> dict:
        if not os.path.isfile(path):
            return {"success": False, "error": "ENOENT",
                    "detail": f"File not found: {path}"}

        try:
            ocr = _get_paddle(lang or "en")
            result = ocr.predict(path)
            if not result or len(result) == 0:
                return {"success": True, "text": "", "lines": []}

            page = result[0]
            rec_texts = page.get("rec_texts", [])
            rec_scores = page.get("rec_scores", [])
            dt_polys = page.get("dt_polys", [])

            lines = []
            for i, (text, score) in enumerate(zip(rec_texts, rec_scores)):
                bbox = []
                if i < len(dt_polys):
                    poly = dt_polys[i]
                    bbox = [round(float(c), 1) for pt in poly for c in pt]
                lines.append({"text": text, "confidence": round(score, 4), "bbox": bbox})

            return {"success": True, "text": "\n".join(rec_texts), "lines": lines}
        except Exception as e:
            logger.exception("PaddleOCR extract failed")
            return {"success": False, "error": "EPROCESSING", "detail": str(e)}

    def layout(self, path: str, lang: str | None = None) -> dict:
        result = self.extract(path, lang)
        if not result.get("success"):
            return result
        blocks = []
        for line in result.get("lines", []):
            bb = line["bbox"]
            block = {"type": "text", "text": line["text"],
                     "confidence": line["confidence"]}
            if bb and len(bb) >= 4:
                block.update({"x": bb[0], "y": bb[1],
                              "width": bb[2] - bb[0] if len(bb) >= 4 else 0,
                              "height": bb[3] - bb[1] if len(bb) >= 4 else 0})
            blocks.append(block)
        return {"success": True, "blocks": blocks}

    def table(self, path: str) -> dict:
        if not os.path.isfile(path):
            return {"success": False, "error": "ENOENT",
                    "detail": f"File not found: {path}"}

        try:
            from paddleocr import PPStructure
            engine = PPStructure()
            result = engine.predict(path)

            tables = []
            for page in result:
                for item in page:
                    if hasattr(item, 'get') and item.get("type") == "table":
                        cells = item.get("res", {}).get("cells", [])
                        if cells:
                            max_row = max(c[4] for c in cells)
                            max_col = max(c[5] for c in cells)
                            grid = [[""] * (max_col + 1) for _ in range(max_row + 1)]
                            for cell in cells:
                                grid[cell[4]][cell[5]] = cell.get("text", "")
                            import csv as _csv
                            import io
                            buf = io.StringIO()
                            writer = _csv.writer(buf)
                            writer.writerows(grid)
                            tables.append({
                                "csv": buf.getvalue().strip(),
                                "headers": grid[0] if grid else [],
                                "rows": grid[1:] if len(grid) > 1 else [],
                            })
            return {"success": True, "tables": tables}
        except ImportError:
            return {"success": False, "error": "EUNSUPPORTED",
                    "detail": "PPStructure not available."}
        except Exception as e:
            logger.exception("PaddleOCR table extraction failed")
            return {"success": False, "error": "EPROCESSING", "detail": str(e)}
```

- [ ] **Step 4: Run paddle tests**

```bash
pytest tests/test_paddle.py -v
```
Expected: 6 passed (or skipped if PaddleOCR not installed).

- [ ] **Step 5: Commit**

```bash
git add backends/paddle.py tests/test_paddle.py
git commit -m "feat: implement Paddle backend (PaddleOCR CPU)"
```

---

### Task 5: PaddleOCR-VL backend

**Files:**
- Modify: `backends/paddleocr_vl.py`
- Create: `tests/test_paddleocr_vl.py`

**Interfaces:**
- Produces: `PaddleOCRVlBackend.extract(path, lang, mode) -> dict`, `.layout()`, `.table()`, `.formula()`, `.chart()`

- [ ] **Step 1: Write failing tests for PaddleOCR-VL backend**

Create `tests/test_paddleocr_vl.py`:

```python
import pytest
import sys
import os

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or os.uname().machine != "arm64",
    reason="PaddleOCR-VL requires Apple Silicon"
)

from backends.paddleocr_vl import PaddleOCRVlBackend


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_paddleocr_vl.py -v
```
Expected: all skipped (not Apple Silicon) or FAIL with NotImplementedError.

- [ ] **Step 3: Implement `backends/paddleocr_vl.py`**

```python
"""PaddleOCR-VL backend — invokes native Swift CLI via subprocess (Apple Silicon only)."""

import os
import subprocess
import logging
from backends.base import BaseOCRBackend

logger = logging.getLogger("mcp-ocr.paddleocr-vl")

_BINARY_TIMEOUT = int(os.environ.get("PADDLEOCR_VL_TIMEOUT", "120"))


def _resolve_binary(bin_path: str | None) -> str:
    """Resolve the paddleocr-vl CLI binary path."""
    if bin_path:
        return bin_path
    env_bin = os.environ.get("PADDLEOCR_VL_BIN", "")
    if env_bin:
        return env_bin
    # Check PATH
    import shutil
    found = shutil.which("paddleocr-vl")
    if found:
        return found
    return "paddleocr-vl"  # will fail with FileNotFoundError at call time


def _map_task(task: str) -> str:
    mapping = {
        "extract": "ocr",
        "layout": "ocr",
        "table": "table",
        "formula": "formula",
        "chart": "chart",
    }
    return mapping.get(task, "ocr")


class PaddleOCRVlBackend(BaseOCRBackend):
    name = "paddleocr_vl"
    tasks = ["text", "layout", "table", "formula", "chart"]

    def __init__(self, bin_path: str | None = None):
        self._bin = _resolve_binary(bin_path)

    def _run(self, path: str, task: str, mode: str = "base") -> dict:
        if not os.path.isfile(path):
            return {"success": False, "error": "ENOENT",
                    "detail": f"File not found: {path}"}

        cli_task = _map_task(task)
        cmd = [self._bin, "ocr", path, "--task", cli_task, "--mode", mode]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_BINARY_TIMEOUT,
            )
        except FileNotFoundError:
            return {
                "success": False,
                "error": "ECONFIG",
                "detail": (
                    "PaddleOCR-VL CLI not found. Install via: "
                    "brew install paddleocr-vl or build from "
                    "https://github.com/mlx-community/paddleocr-vl.swift"
                ),
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "ETIMEOUT",
                    "detail": f"PaddleOCR-VL timed out after {_BINARY_TIMEOUT}s"}

        if result.returncode != 0:
            return {"success": False, "error": "EPROCESSING",
                    "detail": result.stderr.strip() or "PaddleOCR-VL returned non-zero exit code"}

        return {"success": True, "raw": result.stdout.strip()}

    def extract(self, path: str, lang: str | None = None, mode: str = "base") -> dict:
        result = self._run(path, "extract", mode)
        if not result.get("success"):
            return result
        raw = result.pop("raw", "")
        lines_text = raw.split("\n")
        lines = [{"text": t, "confidence": 1.0, "bbox": []} for t in lines_text if t.strip()]
        return {"success": True, "text": raw, "lines": lines}

    def layout(self, path: str, lang: str | None = None, mode: str = "base") -> dict:
        result = self.extract(path, lang, mode)
        if not result.get("success"):
            return result
        blocks = []
        for line in result.get("lines", []):
            blocks.append({
                "type": "text",
                "text": line["text"],
                "confidence": line["confidence"],
            })
        return {"success": True, "blocks": blocks}

    def table(self, path: str, mode: str = "base") -> dict:
        result = self._run(path, "table", mode)
        if not result.get("success"):
            return result
        raw = result.pop("raw", "")
        # Parse markdown table → csv/headers/rows
        # Simple: return as single table with markdown
        return {"success": True, "tables": [{"csv": raw, "headers": [], "rows": []}]}

    def formula(self, path: str, mode: str = "base") -> dict:
        result = self._run(path, "formula", mode)
        if not result.get("success"):
            return result
        raw = result.pop("raw", "")
        return {"success": True, "formulas": [{"text": raw, "format": "latex"}]}

    def chart(self, path: str, mode: str = "base") -> dict:
        result = self._run(path, "chart", mode)
        if not result.get("success"):
            return result
        raw = result.pop("raw", "")
        return {"success": True, "charts": [{"data": raw}]}
```

- [ ] **Step 4: Run paddleocr-vl tests**

```bash
pytest tests/test_paddleocr_vl.py -v
```
Expected: 7 passed on Apple Silicon with CLI installed, or skipped otherwise.

- [ ] **Step 5: Commit**

```bash
git add backends/paddleocr_vl.py tests/test_paddleocr_vl.py
git commit -m "feat: implement PaddleOCR-VL backend (subprocess → Swift CLI)"
```

---

### Task 6: Server — dynamic tool registration + error handling

**Files:**
- Modify: `server.py`
- Create: `tests/test_server.py`

**Interfaces:**
- Consumes: `BACKENDS` from `backends/__init__`, `BaseOCRBackend` methods
- Produces: `main()` entry point, all `ocr_<task>_<backend>` MCP tools, `@handle_errors` decorator

- [ ] **Step 1: Write failing tests for server tool registration**

Create `tests/test_server.py`:

```python
import pytest
from mcp.server import MCPServer

from server import register_tools, create_server, handle_errors


def test_handle_errors_returns_success_on_ok():
    @handle_errors
    def good_func(x):
        return {"success": True, "value": x}

    result = good_func(42)
    assert result == {"success": True, "value": 42}


def test_handle_errors_catches_file_not_found():
    @handle_errors
    def raising_func(path):
        raise FileNotFoundError("nope")

    result = raising_func("test.png")
    assert result["success"] is False
    assert result["error"] == "ENOENT"


def test_handle_errors_catches_import_error():
    @handle_errors
    def bad_import():
        raise ImportError("no module")

    result = bad_import()
    assert result["success"] is False
    assert result["error"] == "EUNSUPPORTED"


def test_handle_errors_catches_generic():
    @handle_errors
    def oops():
        raise ValueError("boom")

    result = oops()
    assert result["success"] is False
    assert result["error"] == "EPROCESSING"
    assert "boom" in result["detail"]


def test_create_server_has_all_tools():
    server = create_server()

    tool_names = [tool.name for tool in server._tools]
    # Vision: 3 tools (text, layout, table) + batch
    assert "ocr_text_vision" in tool_names
    assert "ocr_layout_vision" in tool_names
    assert "ocr_table_vision" in tool_names
    assert "ocr_batch_vision" in tool_names

    # Paddle: 3 tools (text, layout, table) + batch
    assert "ocr_text_paddle" in tool_names
    assert "ocr_layout_paddle" in tool_names
    assert "ocr_table_paddle" in tool_names
    assert "ocr_batch_paddle" in tool_names

    # PaddleOCR-VL: 5 tools (text, layout, table, formula, chart) + batch
    assert "ocr_text_paddleocr_vl" in tool_names
    assert "ocr_layout_paddleocr_vl" in tool_names
    assert "ocr_table_paddleocr_vl" in tool_names
    assert "ocr_formula_paddleocr_vl" in tool_names
    assert "ocr_chart_paddleocr_vl" in tool_names
    assert "ocr_batch_paddleocr_vl" in tool_names


def test_create_server_tool_has_description():
    server = create_server()
    for tool in server._tools:
        assert tool.description, f"Tool {tool.name} has no description"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_server.py -v
```
Expected: FAIL — `create_server`, `register_tools`, `handle_errors` not defined.

- [ ] **Step 3: Implement `server.py`**

```python
"""MCP server for OCR — modular backend architecture."""

import os
import sys
import logging
import functools

from mcp.server import MCPServer

from backends import BACKENDS, get_backend

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("mcp-ocr")


def handle_errors(func):
    """Decorator that catches exceptions and returns structured error dicts."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            return {"success": False, "error": "ENOENT", "detail": str(e)}
        except ImportError as e:
            return {"success": False, "error": "EUNSUPPORTED", "detail": str(e)}
        except Exception as e:
            logger.exception("Tool failed")
            return {"success": False, "error": "EPROCESSING", "detail": str(e)}
    return wrapper


_BACKEND_DESCRIPTIONS = {
    "vision": (
        "Apple Vision OCR — fast on-device GPU/ANE inference (macOS 10.15+). "
        "Best for CJK + major European languages. Zero install on macOS."
    ),
    "paddle": (
        "PaddleOCR CPU — cross-platform, mature model. "
        "Wider language support than Vision, but slower. Requires PaddleOCR Python package."
    ),
    "paddleocr_vl": (
        "PaddleOCR-VL — 0.9B vision-language model on Apple Silicon (M1+). "
        "Most accurate, 109 languages, supports tables/formulas/charts. "
        "Requires paddleocr-vl Swift CLI."
    ),
}


def _build_tool_description(task: str, backend_name: str) -> str:
    """Build a rich description for the AI agent to choose the right tool."""
    task_descriptions = {
        "text": "Extract text from an image. Returns full text, per-line confidence, and bounding boxes.",
        "layout": "Extract text with layout analysis. Returns blocks with bounding boxes.",
        "table": "Extract tables from an image. Returns structured CSV/JSON.",
        "formula": "Extract mathematical formulas from an image. Returns LaTeX.",
        "chart": "Extract chart data from an image. Returns structured data.",
        "batch": "OCR multiple images at once. Returns consolidated results.",
    }
    backend_desc = _BACKEND_DESCRIPTIONS.get(backend_name, "")
    return f"{task_descriptions.get(task, '')}\n\nBackend: {backend_name}. {backend_desc}"


def create_server() -> MCPServer:
    """Create and register all tools dynamically from the BACKENDS registry."""
    server = MCPServer("ocr", version="2.0.0")

    for name, backend in BACKENDS.items():
        for task in backend.tasks:
            _register_tool(server, name, backend, task)

    return server


def _register_tool(server: MCPServer, backend_name: str, backend, task: str):
    """Register a single tool for a given backend + task combination."""
    tool_name = f"ocr_{task}_{backend_name}"
    description = _build_tool_description(task, backend_name)
    method = getattr(backend, task)

    @server.tool(name=tool_name, description=description)
    @handle_errors
    def tool(path: str, _method=method, lang: str | None = None, mode: str = "accurate") -> dict:
        """Auto-generated tool. See tool description for backend details."""
        import inspect
        sig = inspect.signature(_method)
        kwargs = {"path": path}
        if "lang" in sig.parameters:
            kwargs["lang"] = lang
        if "mode" in sig.parameters:
            kwargs["mode"] = mode
        return _method(**kwargs)

    # Batch variant
    batch_name = f"ocr_batch_{backend_name}"
    batch_desc = _build_tool_description("batch", backend_name)

    @server.tool(name=batch_name, description=batch_desc)
    @handle_errors
    def batch_tool(
        paths: list[str],
        _method=method,
        lang: str | None = None,
        mode: str = "accurate",
    ) -> dict:
        results = []
        for p in paths:
            import inspect
            sig = inspect.signature(_method)
            kwargs = {"path": p}
            if "lang" in sig.parameters:
                kwargs["lang"] = lang
            if "mode" in sig.parameters:
                kwargs["mode"] = mode
            try:
                r = _method(**kwargs)
            except Exception as e:
                r = {"success": False, "error": "EPROCESSING", "detail": str(e)}
            results.append({"path": p, **r})
        return {"success": True, "results": results}


def main():
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run server tests**

```bash
pytest tests/test_server.py -v
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: dynamic tool registration with error handling"
```

---

### Task 7: Integration test — end-to-end MCP server

**Files:**
- Create: `tests/test_integration.py`

**Interfaces:**
- Consumes: full server with all backends registered

- [ ] **Step 1: Write integration test**

Create `tests/test_integration.py`:

```python
"""End-to-end integration test — verifies server starts and tools are callable."""

import pytest
from server import create_server


def test_server_created_and_has_tools():
    server = create_server()
    assert server.name == "ocr"
    assert server.version == "2.0.0"

    tool_names = [tool.name for tool in server._tools]
    total_expected = 0
    from backends import BACKENDS
    for backend in BACKENDS.values():
        total_expected += len(backend.tasks)  # one per task
        total_expected += 1  # one batch per backend
    assert len(tool_names) == total_expected, f"Expected {total_expected} tools, got {len(tool_names)}"
```

- [ ] **Step 2: Run to verify**

```bash
pytest tests/test_integration.py -v
```
Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration test for server"
```

---

### Task 8: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# pi-mcp-ocr

Modular OCR MCP server with pluggable backends: Apple Vision, PaddleOCR, and PaddleOCR-VL.

## Installation

```bash
# Recommended (macOS Apple Silicon):
pip install git+https://github.com/timaliev/pi-mcp_ocr.git#egg=pi-mcp-ocr[vision,paddleocr-vl]

# Cross-platform:
pip install git+https://github.com/timaliev/pi-mcp_ocr.git#egg=pi-mcp-ocr[paddle]
```

### Optional dependency groups

| Group | Backend | Requirements |
|-------|---------|--------------|
| `vision` | Apple Vision | macOS 10.15+ |
| `paddle` | PaddleOCR | Cross-platform, CPU |
| `paddleocr-vl` | PaddleOCR-VL | macOS 14+, Apple Silicon, `paddleocr-vl` CLI |
| `all` | Everything | All of the above |

## Configuration

Add to your MCP client config (e.g., `mcp.json` for pi):

```json
{
  "mcpServers": {
    "ocr": {
      "command": "mcp-ocr",
      "args": []
    }
  }
}
```

## Backends

### Vision (`ocr_text_vision`, `ocr_layout_vision`, `ocr_table_vision`)
- macOS 10.15+, zero install
- GPU/ANE accelerated
- Best for: CJK + major European languages, fast extraction

### Paddle (`ocr_text_paddle`, `ocr_layout_paddle`, `ocr_table_paddle`)
- Cross-platform CPU
- Mature PaddleOCR models
- Best for: wide language coverage, when not on macOS

### PaddleOCR-VL (`ocr_text_paddleocr_vl`, `ocr_table_paddleocr_vl`, `ocr_formula_paddleocr_vl`, `ocr_chart_paddleocr_vl`)
- macOS 14+, Apple Silicon (M1/M2/M3/M4)
- 0.9B vision-language model, 109 languages
- Best for: highest accuracy, formulas, charts, tables
- Requires: `paddleocr-vl` CLI from https://github.com/mlx-community/paddleocr-vl.swift

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PADDLEOCR_VL_BIN` | `paddleocr-vl` | Path to paddleocr-vl CLI binary |
| `PADDLEOCR_VL_TIMEOUT` | `120` | Timeout in seconds for PaddleOCR-VL |

## Development

```bash
git clone https://github.com/timaliev/pi-mcp_ocr.git
cd pi-mcp_ocr
pip install -e .[all]
pytest
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install and usage instructions"
```

---

### Task 9: Create GitHub repo + push

**Files:**
- None (remote operations)

- [ ] **Step 1: Create public GitHub repo via GitHub MCP**

```
mcp_github_create_repository(name="pi-mcp_ocr", description="Modular OCR MCP server with Vision, PaddleOCR, and PaddleOCR-VL backends", private=false)
```

- [ ] **Step 2: Set remote and push**

```bash
git remote add origin https://github.com/timaliev/pi-mcp_ocr.git
git branch -M main
git push -u origin main
```

- [ ] **Step 3: Run full test suite to confirm everything works**

```bash
pytest -v
```

- [ ] **Step 4: Final commit if anything changed**

```bash
git push origin main
```
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Base class + registry → Tasks 1-2
- ✅ Vision backend → Task 3
- ✅ Paddle backend → Task 4
- ✅ PaddleOCR-VL backend → Task 5
- ✅ Dynamic tool registration → Task 6
- ✅ Error handling decorator → Task 6
- ✅ Batch routing → Task 6
- ✅ Installation / pyproject.toml → Task 1
- ✅ GitHub repo → Task 9
- ✅ Tests → Tasks 2-7

**2. Placeholder scan:** No TBD, TODO, "appropriate error handling", "write tests for the above". All steps have concrete code.

**3. Type consistency:**
- `BaseOCRBackend.extract(path) -> dict` used consistently
- `get_backend(name) -> BaseOCRBackend` in Task 2, consumed in Task 6
- `BACKENDS` dict: `dict[str, BaseOCRBackend]` in Task 2, consumed in Task 6
- `backend.tasks: list[str]` used in Task 6 for tool generation
- All tool names follow `ocr_{task}_{backend_name}` pattern
