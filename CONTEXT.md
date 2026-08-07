# CONTEXT.md — Glossary for mcp_ocr

## Domain

- **MCP (Model Context Protocol)** — JSON-RPC protocol connecting AI agents to tools over stdio/SSE
- **Backend** — OCR implementation (Vision, Paddle, PaddleOCR-VL). Pluggable via registry
- **Vision** — Apple's on-device OCR framework (macOS 10.15+, GPU/ANE)
- **PaddleOCR** — Baidu's open-source OCR engine, CPU cross-platform
- **PaddleOCR-VL** — MLX-based vision-language model (0.9B params, 109 languages), called via subprocess to Swift CLI

## Architecture

- `mcp_ocr/server.py` — MCP server entry point, registers tools dynamically per available backends
- `mcp_ocr/backends/` — backend implementations (Vision, Paddle, PaddleOCR-VL)
- Each backend implements `BaseOCRBackend` ABC with `text()`, `layout()`, `table()` methods
- Tools are registered with backend suffix: `ocr_text_vision`, `ocr_table_paddle`, etc.

## Conventions

- **Language:** Python 3.11+
- **Package manager:** uv / pip
- **Testing:** pytest
- **CI/CD:** GitHub Actions (to be added)
- **Versioning:** semantic via git-cliff
