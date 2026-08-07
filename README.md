# mcp_ocr

Modular OCR MCP server with pluggable backends: Apple Vision, PaddleOCR, and PaddleOCR-VL.

> **Requires [pi-mcp-bridge](https://github.com/timaliev/pi-mcp-bridge)** to connect to [pi](https://pi.dev).

## Installation

```bash
pip install git+https://github.com/timaliev/mcp_ocr.git#egg=mcp-ocr[vision,paddleocr-vl]
```

Or via uv:

```bash
uv tool install git+https://github.com/timaliev/mcp_ocr.git
```

### Optional dependency groups

| Group | Backend | Requirements |
|-------|---------|--------------|
| `vision` | Apple Vision | macOS 10.15+ |
| `paddle` | PaddleOCR | Cross-platform, CPU |
| `paddleocr-vl` | PaddleOCR-VL | macOS 14+, Apple Silicon, `paddleocr-vl` CLI |
| `all` | Everything | All of the above |

## Configuration

### With pi-mcp-bridge

In `~/.pi/agent/settings.json`:

```json
{
  "mcpBridge": {
    "servers": [
      {
        "name": "ocr",
        "command": "mcp-ocr",
        "args": []
      }
    ]
  }
}
```

### Standalone MCP client

In `~/.mcp.json`:

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

## Development

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PADDLEOCR_VL_BIN` | `paddleocr-vl` | Path to paddleocr-vl CLI binary |
| `PADDLEOCR_VL_TIMEOUT` | `120` | Timeout in seconds for PaddleOCR-VL |

## Development

```bash
git clone https://github.com/timaliev/mcp_ocr.git
cd mcp_ocr
pip install -e .[all]
pytest
```
