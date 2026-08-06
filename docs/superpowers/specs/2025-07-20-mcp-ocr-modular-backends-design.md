# mcp_ocr: Modular Backend Architecture + PaddleOCR-VL Integration

**Date:** 2025-07-20
**Status:** draft
**Repo:** `github.com/timaliev/pi-mcp_ocr`

## Overview

Refactor `mcp_ocr` from a single `server.py` with hardcoded dual-backend dispatch into a modular, class-based backend architecture. Each backend × task combination becomes a separately named MCP tool (e.g., `ocr_text_vision`, `ocr_table_paddleocr_vl`). Add a new PaddleOCR-VL backend via the native Swift CLI for Apple Silicon.

## Motivation

- Adding backends is currently invasive (edit `server.py` dispatch, add functions inline)
- No way to mix backends per task — user must pick one backend for all OCR
- PaddleOCR-VL (0.9B VLM) provides best-in-class accuracy, 109 languages, table/formula/chart extraction natively on Apple Silicon
- The AI agent should choose the optimal backend per task based on tool descriptions

## Architecture

```
pi-mcp_ocr/
├── pyproject.toml
├── README.md
├── server.py                  # Tool registration (dynamic), batch routing, error handling
├── backends/
│   ├── __init__.py            # Registry: BACKENDS dict, get_backend()
│   ├── base.py                # BaseOCRBackend ABC
│   ├── vision.py              # VisionBackend (PyObjC, macOS only)
│   ├── paddle.py              # PaddleBackend (PaddleOCR, cross-platform CPU)
│   └── paddleocr_vl.py        # PaddleOCRVlBackend (subprocess → Swift CLI, Apple Silicon)
├── tests/
│   ├── test_backends.py
│   └── test_tool_registry.py
└── docs/
    └── superpowers/
        └── specs/
            └── 2025-07-20-mcp-ocr-modular-backends-design.md
```

## Base Class

```python
class BaseOCRBackend(ABC):
    name: str                          # "vision", "paddle", "paddleocr_vl"
    tasks: list[str]                   # subset of ["text","layout","table","formula","chart"]

    def extract(self, path: str) -> dict: ...
    def layout(self, path: str) -> dict: ...
    def table(self, path: str) -> dict: ...
    def formula(self, path: str) -> dict: ...   # defaults to EUNSUPPORTED
    def chart(self, path: str) -> dict: ...     # defaults to EUNSUPPORTED
```

Methods not listed in `self.tasks` return `{"success": false, "error": "EUNSUPPORTED"}` automatically (handled by `server.py` dispatch, not per-backend boilerplate).

## Tool Surface

Tools are generated from the `BACKENDS` registry. Each backend declares its `tasks`, and `server.py` creates `ocr_{task}_{name}` for each combination. Summary:

| Task    | Vision                     | Paddle                     | PaddleOCR-VL                     |
|---------|----------------------------|----------------------------|----------------------------------|
| text    | `ocr_text_vision`          | `ocr_text_paddle`          | `ocr_text_paddleocr_vl`          |
| layout  | `ocr_layout_vision`        | `ocr_layout_paddle`        | `ocr_layout_paddleocr_vl`        |
| table   | `ocr_table_vision` (15+)   | `ocr_table_paddle`         | `ocr_table_paddleocr_vl`         |
| formula | —                          | —                          | `ocr_formula_paddleocr_vl`       |
| chart   | —                          | —                          | `ocr_chart_paddleocr_vl`         |
| batch   | `ocr_batch_vision`         | `ocr_batch_paddle`         | `ocr_batch_paddleocr_vl`         |

Each tool's docstring includes backend characteristics (platform, speed, accuracy, language support) so the AI agent can select optimally at invoke time.

## Backend Details

### Vision (`backends/vision.py`)

- **Platform:** macOS 10.15+ (PyObjC, `Vision` + `Quartz` frameworks)
- **Tasks:** text, layout, table (macOS 15+ for table detection revision 4)
- **Strengths:** Fast (GPU/ANE), zero install, good for CJK + major European languages
- **Weaknesses:** Limited language set, no formula/chart

### Paddle (`backends/paddle.py`)

- **Platform:** Cross-platform (CPU)
- **Tasks:** text, layout, table (PPStructure)
- **Strengths:** Works everywhere, mature PaddleOCR model
- **Weaknesses:** CPU-only, Python dependency heavy, no formula/chart

### PaddleOCR-VL (`backends/paddleocr_vl.py`)

- **Platform:** macOS 14+, Apple Silicon (M1/M2/M3/M4)
- **Tasks:** text, layout, table, formula, chart
- **Integration:** `subprocess.run` on the `paddleocr-vl` Swift CLI binary
- **Binary resolution:** `PADDLEOCR_VL_BIN` env → `paddleocr-vl` on PATH → clear error
- **Timeout:** Configurable via `PADDLEOCR_VL_TIMEOUT` env (default 120s)
- **Task mapping:**
  - `extract` → `paddleocr-vl ocr <path> --task ocr`
  - `layout` → `paddleocr-vl ocr <path> --task ocr` (text split into blocks)
  - `table` → `paddleocr-vl ocr <path> --task table` (markdown → CSV/headers/rows)
  - `formula` → `paddleocr-vl ocr <path> --task formula` (LaTeX)
  - `chart` → `paddleocr-vl ocr <path> --task chart` (structured data)
- **Output parsing:** CLI emits plain text; synthetic confidence of 1.0 for VL model output
- **Model caching:** Handled automatically by the Swift CLI via HuggingFace hub (`~/.cache/huggingface/hub/`)

## Error Handling

All tools are wrapped with a `@handle_errors` decorator in `server.py`:

| Exception | Result |
|-----------|--------|
| `FileNotFoundError` (file missing) | `{success: false, error: "ENOENT"}` |
| `ImportError` (backend unavailable) | `{success: false, error: "EUNSUPPORTED"}` |
| `subprocess.TimeoutExpired` | `{success: false, error: "ETIMEOUT"}` |
| Binary not found (paddleocr-vl) | `{success: false, error: "ECONFIG", detail: "PaddleOCR-VL CLI not found..."}` |
| Any other exception | `{success: false, error: "EPROCESSING", detail: str(e)}` |

## Result Format Consistency

All backends return the same shapes per tool type:

- **extract:** `{success, text, lines[{text, confidence, bbox}]}`
- **layout:** `{success, blocks[{type, text, confidence, x, y, width, height}]}`
- **table:** `{success, tables[{csv, headers, rows}]}`
- **formula:** `{success, formulas[{text, format}]}`
- **chart:** `{success, charts[{data}]}`
- **batch:** `{success, results[{path, ...tool_result}]}`

## Installation

### End-user (PyPI — future):
```bash
pip install pi-mcp-ocr[vision,paddleocr-vl]
```

### From GitHub:
```bash
pip install git+https://github.com/timaliev/pi-mcp_ocr.git
```

### Development (editable):
```bash
git clone https://github.com/timaliev/pi-mcp_ocr.git
cd pi-mcp_ocr
pip install -e .[all]
```

### Optional dependency groups:
```bash
pip install pi-mcp-ocr              # framework only, no backends
pip install pi-mcp-ocr[vision]      # + Apple Vision
pip install pi-mcp-ocr[paddle]      # + PaddleOCR (cross-platform)
pip install pi-mcp-ocr[paddleocr-vl] # + PaddleOCR-VL CLI dependency
pip install pi-mcp-ocr[all]         # everything
```

### Pi mcp.json config:
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

The `mcp-ocr` command is exposed via `[project.scripts]` in `pyproject.toml`.

## Testing

- **`tests/test_tool_registry.py`** — verifies all expected tools are generated from BACKENDS dict; checks that unsupported tasks return EUNSUPPORTED
- **`tests/test_backends.py`** — per-backend unit tests with fixture images; tests skipped if backend unavailable on current platform
- Vision tests run only on macOS
- Paddle tests run anywhere PaddleOCR is installed
- PaddleOCR-VL tests run only on Apple Silicon with `paddleocr-vl` CLI on PATH

## Migration from Old mcp_ocr

1. Old tools (`ocr_extract`, `ocr_layout`, `ocr_table`, `ocr_batch`) with `backend` param are **removed** — breaking change
2. Users update their `mcp.json` to point to the new repo
3. AI agents pick backend-specific tools automatically via tool descriptions
4. Old monorepo entry at `~/.local/mcp-servers/mcp_ocr` can be removed post-migration

## Non-Goals

- Backend auto-discovery / plugin system (3 backends don't justify it)
- Python wrapper around MLX Swift (subprocess is simpler, Swift CLI is the contract)
- Backward compatibility with old `backend=` parameter
