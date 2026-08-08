# mcp_ocr

Modular OCR MCP server with pluggable backends: Apple Vision, PaddleOCR, and PaddleOCR-VL.

> **Bundled skill:** `ocr-recipes` — 12 pluggable OCR workflows (receipt scanner,
> business card, QR→shopping, document OCR, batch processing, preprocessing guide).
> Auto-loads in Pi.
>
> **Requires [pi-mcp-bridge](https://github.com/timaliev/pi-mcp-bridge)** to connect to [pi](https://pi.dev).

## Quick start

### One-line install (pi + pi-mcp-bridge)

Add to `~/.pi/agent/settings.json` under `mcpBridge.servers`:

```json
{
  "name": "ocr",
  "command": "mcp-ocr",
  "args": [],
  "setupCommands": [
    "uv tool install --force --python 3.11 \"mcp-ocr[all] @ git+https://github.com/timaliev/mcp_ocr.git\""
  ]
}
```

> `setupCommands` runs before each session start. It auto-installs the server with all
> backends from GitHub. Requires `uv` on `PATH`. Requires pi-mcp-bridge ≥1.0.0.

Restart pi. Done — Vision, Paddle, and PaddleOCR-VL are all available.

### Manual install (standalone MCP client)

```bash
# All backends (macOS)
uv tool install --python 3.11 "mcp-ocr[all] @ git+https://github.com/timaliev/mcp_ocr.git"

# Vision only (macOS, zero extra deps)
uv tool install --python 3.11 "mcp-ocr[vision] @ git+https://github.com/timaliev/mcp_ocr.git"

# Paddle only (cross-platform, CPU)
uv tool install --python 3.11 "mcp-ocr[paddle] @ git+https://github.com/timaliev/mcp_ocr.git"
```

Then configure your MCP client to run `mcp-ocr`.

## Backend dependencies

| Group | Backend | Python deps | External deps |
|-------|---------|-------------|---------------|
| `vision` | Apple Vision | `pyobjc-framework-vision`, `pyobjc-framework-quartz` | macOS 10.15+ |
| `paddle` | PaddleOCR | `paddleocr`, `paddlepaddle` (~2.5 GB) | Nothing |
| `paddleocr-vl` | PaddleOCR-VL | None (calls CLI via subprocess) | `paddleocr-vl` CLI + model weights (~1.8 GB) |
| `all` | Everything | vision + paddle | vision + paddle + paddleocr-vl |

### Installing PaddleOCR-VL CLI

The VL backend is the hardest to set up. See the full guide below.

The Python package `mcp-ocr[paddleocr-vl]` installs only the subprocess wrapper — not the CLI itself.

## Configuration

### pi-mcp-bridge with auto-install (recommended)

```json
{
  "mcpBridge": {
    "servers": [
      {
        "name": "ocr",
        "command": "mcp-ocr",
        "args": [],
        "setupCommands": [
          "uv tool install --force --python 3.11 \"mcp-ocr[all] @ git+https://github.com/timaliev/mcp_ocr.git\""
        ]
      }
    ]
  }
}
```

The `setupCommands` field (added in pi-mcp-bridge) runs before the server starts. Replace `[all]` with `[vision]` or `[vision,paddle]` to install only specific backends.

### Standalone MCP client

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

### Quick comparison

|  | Vision | Paddle | PaddleOCR-VL |
|------|--------|--------|-------------|
| **Speed** | ⚡ Instant | 🐢 30–90s | 🐢 2–7s (base) / 150s (dynamic) |
| **Accuracy** | ★★★★ | ★★★ | ★★ (Cyrillic: ★) |
| **Languages** | CJK + major European | 80+ languages | Claims 109, poor Cyrillic |
| **Platform** | macOS 10.15+ | Cross-platform | macOS 14+, Apple Silicon |
| **RAM usage** | ~50 MB | ~2.5 GB | ~100 MB (CLI) / 2.5 GB (Python lib) |
| **GPU** | ANE/GPU | CPU only | Apple Silicon GPU |
| **Install** | `pip install mcp-ocr[vision]` | `pip install mcp-ocr[paddle]` | `brew install paddleocr-vl` |
| **First run** | Zero | Downloads models (1–2 GB) | Downloads models (1.8 GB) |
| **Text** | ✅ | ✅ | ⚠️ Fast but inaccurate for non-CJK |
| **Layout** | ✅ | ✅ | ⚠️ Same as text |
| **Table** | ✅ | ✅ | ⚠️ Experimental |
| **Formula** | ❌ | ❌ | ❌ (upstream hang) |
| **Chart** | ❌ | ❌ | ❌ (upstream hang) |

**Recommendation**: Use **Vision** for everyday OCR. It's instant, accurate for European languages, and has zero dependencies on macOS. Use PaddleOCR-VL only for CJK text where Vision falls short. Avoid Paddle (Python) backend — it loads 2.5 GB of C++ libraries for comparable results.

### Vision (`ocr_text_vision`, `ocr_layout_vision`, `ocr_table_vision`)
- macOS 10.15+, zero install
- GPU/ANE accelerated
- Best for: CJK + major European languages, fast extraction

### Paddle (`ocr_text_paddle`, `ocr_layout_paddle`, `ocr_table_paddle`)
- Cross-platform CPU
- Mature PaddleOCR models
- Best for: wide language coverage, when not on macOS

### PaddleOCR-VL (`ocr_text_paddleocr_vl`, `ocr_layout_paddleocr_vl`, `ocr_table_paddleocr_vl`)
- macOS 14+, Apple Silicon (M1/M2/M3/M4)
- 0.9B vision-language model, 109 languages (Cyrillic quality is poor)
- **Default mode is `base`** (fast, ~2–7s). `dynamic` mode is 20× slower and produces garbled output
- **Formula and chart tasks disabled** — the CLI hangs on these (upstream bug)
- Model downloads 1.8 GB on first run; subsequent runs use cache
- Best for: CJK text, when Vision is not available

## Installing PaddleOCR-VL CLI

> **⚠️ The CLI has known build issues.** `swift build` alone is not enough.
> You must compile Metal shaders and download model weights manually.

### 1. Clone and build the CLI

```bash
git clone https://github.com/mlx-community/paddleocr-vl.swift
cd paddleocr-vl.swift
swift build -c release
```

### 2. Compile Metal shaders (metallib)

`swift build` does not compile `.metal` files. Without this step the CLI crashes
with `Failed to load the default metallib`.

```bash
cd .build/checkouts/mlx-swift/Source/Cmlx/mlx-c
mkdir -p build && cd build
cmake .. -G Ninja && ninja

# Copy the compiled metallib next to the binary
cp build/_deps/mlx-build/mlx/backend/metal/kernels/mlx.metallib \
  /path/to/paddleocr-vl.swift/.build/release/default.metallib
```

### 3. Download model weights

The CLI's built-in downloader silently fails — model loads but produces garbled output.
Download weights manually via Python:

```bash
pip install huggingface_hub
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'PaddlePaddle/PaddleOCR-VL',
    local_dir='\$HOME/.cache/paddleocr-vl-model',
    local_dir_use_symlinks=False,
)
"
```

### 4. Verify

```bash
paddleocr-vl ocr /path/to/image.png --model ~/.cache/paddleocr-vl-model
```

### 5. Set environment variable

```bash
export PADDLEOCR_VL_MODEL="$HOME/.cache/paddleocr-vl-model"
```

The MCP server reads this env var and passes `--model` to the CLI automatically.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PADDLEOCR_VL_BIN` | `paddleocr-vl` | Path to paddleocr-vl CLI binary |
| `PADDLEOCR_VL_TIMEOUT` | `120` | Timeout in seconds for PaddleOCR-VL |
| `PADDLEOCR_VL_MODEL` | (none) | Path to downloaded model weights (required) |

## Development

```bash
git clone https://github.com/timaliev/mcp_ocr.git
cd mcp_ocr
pip install -e .[all]
pytest
```
