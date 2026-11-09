# mcp_ocr

Modular OCR MCP server with pluggable backends: Apple Vision, PaddleOCR, and Xiaomi-OCR-0 (document parsing, tables, formulas, KIE).

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

Restart pi. Done — Vision, Paddle, and Xiaomi-OCR-0 are all available
(Xiaomi-OCR-0 needs the `[xiaomi]` extra: `mcp-ocr[xiaomi]`).

### Manual install (standalone MCP client)

```bash
# All backends (macOS)
uv tool install --python 3.11 "mcp-ocr[all] @ git+https://github.com/timaliev/mcp_ocr.git"

# Vision only (macOS, zero extra deps)
uv tool install --python 3.11 "mcp-ocr[vision] @ git+https://github.com/timaliev/mcp_ocr.git"

# Paddle only (cross-platform, CPU)
uv tool install --python 3.11 "mcp-ocr[paddle] @ git+https://github.com/timaliev/mcp_ocr.git"

# Xiaomi-OCR-0 only (document parsing / tables / formulas / KIE; ~1.6 GB model)
uv tool install --python 3.11 "mcp-ocr[xiaomi] @ git+https://github.com/timaliev/mcp_ocr.git"
```

Then configure your MCP client to run `mcp-ocr`.

## Backend dependencies

| Group | Backend | Python deps | External deps |
|-------|---------|-------------|---------------|
| `vision` | Apple Vision | `pyobjc-framework-vision`, `pyobjc-framework-quartz` | macOS 10.15+ |
| `paddle` | PaddleOCR | `paddleocr>=3`, `paddlepaddle` (~2.5 GB) | Nothing |
| `xiaomi` | Xiaomi-OCR-0 | `transformers`, `torch`, `torchvision`, `pillow` | Model weights (~1.6 GB, downloaded on first use) |
| `all` | Everything | vision + paddle + xiaomi | vision + paddle + Xiaomi model |

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

|  | Vision | Paddle | Xiaomi-OCR-0 |
|------|--------|--------|--------------|
| **Speed** | ⚡ <100 ms | 🐢 30–90 s | 🐢 2–18 s (after warm-up) |
| **Accuracy** | ★★★★ (Latin/CJK) | ★★★ | ★★★★ (document structure) |
| **Languages** | ~30 locales (CJK, Latin, Cyrillic, Arabic) | 100+ | empirically RU/EN/DE/JA; weak AR/KO |
| **Platform** | macOS 10.15+ | Cross-platform CPU | Apple Silicon (MPS), CUDA, CPU |
| **RAM usage** | ~50 MB | ~2.5 GB | ~2–3 GB (0.8B fp16) |
| **Install** | `mcp-ocr[vision]` | `mcp-ocr[paddle]` | `mcp-ocr[xiaomi]` |
| **First run** | Zero | Downloads models (1–2 GB) | Downloads model (~1.6 GB) |
| **Text** | ✅ | ✅ | ✅ |
| **Layout** | ✅ | ✅ | ✅ (blocks; no boxes) |
| **Table** | ❌ (no structure API) | ✅ (`PPStructureV3`) | ✅ OTSL → HTML + CSV |
| **Formula** | ❌ | ❌ | ✅ LaTeX |
| **Document → Markdown** | ❌ | ❌ | ✅ (tables + formulas inline) |
| **KIE → JSON** | ❌ | ❌ | ✅ |

**Recommendation**: **Vision** for fast everyday text (and the best Cyrillic on macOS).
**Xiaomi-OCR-0** when you need document structure — tables, formulas, full-page
Markdown, or key-field JSON. **Paddle** as a cross-platform fallback.

> **Note on Vision tables:** Apple exposes table parsing only through
> `VNRecognizeDocumentsRequest`, which the pinned pyobjc build does not provide.
> `ocr_table_vision` therefore reports `EUNSUPPORTED` and points at Xiaomi/Paddle
> instead of returning text labeled as a table.

### Vision (`ocr_text_vision`, `ocr_layout_vision`, `ocr_table_vision`)
- macOS 10.15+, zero install
- GPU/ANE accelerated
- **`mode` defaults to `accurate`** — the `fast` recognizer is Latin-only and will
  transliterate Cyrillic/CJK, so only opt into it for quick Latin scans
- Best for: CJK + major European languages, fast extraction

### Paddle (`ocr_text_paddle`, `ocr_layout_paddle`, `ocr_table_paddle`)
- Cross-platform CPU
- Mature PaddleOCR models, `lang=` picks the script family (e.g. `ru`, `ch`, `japan`)
- Table extraction uses the PaddleOCR 3.x `PPStructureV3` pipeline
- Best for: wide language coverage, when not on macOS

### Xiaomi-OCR-0 (`ocr_document_xiaomi`, `ocr_table_xiaomi`, `ocr_formula_xiaomi`, `ocr_kie_xiaomi`, `ocr_text_xiaomi`, `ocr_layout_xiaomi`)
- 0.8B document-parsing VLM ([xiaomi-research/Xiaomi-OCR-0](https://github.com/xiaomi-research/Xiaomi-OCR-0),
  Apache-2.0), served locally via `transformers` on MPS/CUDA/CPU (`torchvision` is required by the Qwen3-VL image processor)
- `ocr_document_xiaomi` → Markdown with HTML tables and LaTeX formulas
- `ocr_table_xiaomi` → `headers` / `rows` / `csv` / `html` (OTSL parsed by the server)
- `ocr_kie_xiaomi` → JSON; pass `fields` to narrow the schema
- `ocr_formula_xiaomi` → LaTeX
- No language parameter: it transcribes the document's own language. Measured
  character error rate 0.00 on printed Russian (including a degraded photo) and
  English/German/Japanese; Arabic and Korean are unreliable
- Model is loaded lazily, so server start stays instant; **it is loaded once per server
  process** (~3 GB resident) and every later page reuses it
- Input is downscaled to at most `XIAOMI_OCR_MAX_PIXELS` (default 4 MP) before inference:
  every 32×32 pixel block becomes one vision token, so a 300 DPI A4 page (3507×2480)
  otherwise costs ~8.6k tokens and a single call takes ~40 s
- **One request at a time**: a second concurrent call returns `EBUSY` immediately
  instead of competing for the single MPS device — retry it in a few seconds
- **Idle unload**: the ~3 GB model is released after `XIAOMI_OCR_IDLE_UNLOAD` seconds
  without requests (default 300), so an idle agent session does not hold it. The next
  call reloads it in ~3–8 s. `0` unloads after every request, `-1` keeps it resident
  for the process lifetime
- **First call returns `EWARMING` instead of blocking**: the ~1.75 GB checkpoint
  downloads in a background thread (progress is reported in the reply). Repeat the
  call in a minute; once the download is complete the model loads (~20–30 s) and the
  request runs. This keeps a cold start inside the MCP tool-call timeout
- A failed download is reported as `EPROCESSING` with the underlying error; if the
  hub is unreachable, point `XIAOMI_OCR_MODEL` at a local checkpoint directory

## Long-running calls (progress notifications)

A dense page can take longer than a client's per-request timeout (a 58-row table
takes ~60 s to decode). The server reports MCP progress every
`MCP_OCR_PROGRESS_INTERVAL` seconds while a backend call runs; clients that reset
their timeout on progress (Pi, and most progress-aware clients) keep the call alive
and show the elapsed time. Batch tools report per-page progress. Clients that do not
request progress (DSH today) are unaffected — for those, raise the client's
per-request timeout instead (e.g. `toolCallTimeoutMs` for the DSH MCP client).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `XIAOMI_OCR_MODEL` | `xiaomi-research/Xiaomi-OCR-0` | Model id or local directory |
| `XIAOMI_OCR_DEVICE` | auto (`mps` → `cuda` → `cpu`) | Torch device |
| `XIAOMI_OCR_MAX_TOKENS` | `4096` | Generation budget per request |
| `XIAOMI_OCR_EXPECTED_BYTES` | `1800000000` | Expected checkpoint size, used for EWARMING progress |
| `XIAOMI_OCR_MAX_PIXELS` | `4000000` | Downscale input images above this pixel count (0 disables scaling) |
| `XIAOMI_OCR_IDLE_UNLOAD` | `300` | Seconds without requests before the model is unloaded (0 = after every request, -1 = never) |
| `MCP_OCR_PROGRESS_INTERVAL` | `5` | Seconds between MCP progress notifications during a long call |

## Development

```bash
git clone https://github.com/timaliev/mcp_ocr.git
cd mcp_ocr
pip install -e .[all]
pytest
```

Most Xiaomi-OCR-0 tests inject a stub generator, so they run without `torch` or the
model weights; only the end-to-end test that calls the real model needs `[xiaomi]`.