# CONTEXT.md — Glossary for mcp_ocr

## Domain

- **MCP (Model Context Protocol)** — JSON-RPC protocol connecting AI agents to tools over stdio/SSE
- **Backend** — OCR implementation (Vision, Paddle, Xiaomi-OCR-0). Pluggable via registry
- **Vision** — Apple's on-device OCR framework (macOS 10.15+, GPU/ANE)
- **PaddleOCR** — Baidu's open-source OCR engine, CPU cross-platform
- **Xiaomi-OCR-0** — local 0.8B document-parsing VLM (transformers; MPS/CUDA/CPU). Emits Markdown with OTSL tables (converted to HTML) and LaTeX formulas; also KIE/VQA

## Architecture

- `mcp_ocr/server.py` — MCP server entry point, registers tools dynamically per available backends
- `mcp_ocr/backends/` — backend implementations (Vision, Paddle, Xiaomi-OCR-0)
- Each backend implements `BaseOCRBackend` ABC with `extract()`, `layout()`, `table()`; optional `formula()`, `document()`, `kie()`
- Tools are registered with backend suffix: `ocr_text_vision`, `ocr_table_paddle`, `ocr_document_xiaomi`, `ocr_kie_xiaomi`, etc.
- `mcp_ocr/otsl.py` — OTSL table markup → grid / HTML / Markdown embedding
- `mcp_ocr/html_table.py` — HTML tables (PaddleOCR `pred_html`) → rows

## Conventions

- **Language:** Python 3.11+
- **Package manager:** uv / pip
- **Testing:** pytest
- **CI/CD:** GitHub Actions (to be added)
- **Versioning:** semantic via git-cliff
