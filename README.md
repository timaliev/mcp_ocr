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
