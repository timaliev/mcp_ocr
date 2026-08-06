# pi-mcp-ocr Documentation

## Backend Status

| Backend | Text | Layout | Table | Formula | Chart | Batch |
|---------|------|--------|-------|---------|-------|-------|
| **Vision** | ✅ Stable | ✅ Stable | ⚠️ macOS 15+ | ❌ | ❌ | ✅ Stable |
| **Paddle** | ✅ Stable | ✅ Stable | ✅ Stable | ❌ | ❌ | ✅ Stable |
| **PaddleOCR-VL** | ❌ Model DL | ❌ | ❌ | ❌ | ❌ | ❌ |

## Guides

- [Backend Comparison](./backend-comparison.md) — real measurements, feature matrix, recommendations

## Troubleshooting

- [PaddleOCR-VL: Metal Shader (metallib) Fix](./troubleshooting/paddleocr-vl-metallib-fix.md) — ✅ Fixed
- [PaddleOCR-VL: Model Download Failure](./troubleshooting/paddleocr-vl-model-download.md) — ❌ Open
- [PaddleOCR-VL: Mode Parameter Bug](./troubleshooting/paddleocr-vl-mode-bug.md) — ❌ Open

## Design Documents

- [Modular Backend Architecture Plan](./superpowers/plans/2025-07-20-mcp-ocr-modular-backends.md)
- [Modular Backend Design Spec](./superpowers/specs/2025-07-20-mcp-ocr-modular-backends-design.md)

## Research

- [Deep Research: Best OCR for Apple Silicon MCP Servers](./research/2026-08-06-ocr-apple-silicon-research.md) — comparison of all OCR engines, MCP packaging guidance
