---
name: ocr-recipes
description: >
  OCR and image-to-text recipes using mcp_ocr + mcp_raster MCP tools.
  Pluggable subskills for receipt scanning, business card extraction,
  screenshot text, document OCR, QR/barcode search, and more.
  Bundled with mcp_ocr package. Auto-loads in Pi when package is installed.
  Use when user asks to extract text from images, scan receipts/documents,
  find products by barcode, or any OCR-related task.
---

# OCR Recipes

Pluggable OCR workflows. Each recipe is a standalone subskill file in this
directory. The agent reads the relevant file at runtime — no monolithic config.

> **Bundled with [mcp_ocr](https://github.com/timaliev/mcp_ocr).**
> Install `mcp_ocr[all]` and this skill auto-loads in Pi.

---

## Phase 1: Backend Discovery

Check which OCR backends are available before running any recipe:

```
mcp_ocr_ocr_text_vision(path=<any_valid_image>)
mcp_ocr_ocr_text_paddle(path=<any_valid_image>)
```

| Backend | Best for |
|---------|----------|
| Vision | European/CJK, fast, zero-config |
| Paddle | Cross-platform, wide languages, needs `lang` param |
| PaddleOCR-VL | 109 languages, tables/formulas, slow |

Prefer Vision when available. Fall back to Paddle with explicit `lang`.

---

## Phase 2: Dispatch

Match user request to subskill file:

| User says | Read subskill |
|-----------|---------------|
| "scan receipt", "receipt", "check photo" | [receipt-scanner.md](receipt-scanner.md) |
| "business card", "contact from image" | [business-card.md](business-card.md) |
| "text from screenshot", "read screen" | [text-from-screenshot.md](text-from-screenshot.md) |
| "scan document", "digitize", "OCR document" | [document-ocr.md](document-ocr.md) |
| "read this", "what does it say", "OCR" | [simple-ocr.md](simple-ocr.md) |
| "extract table", "table from image" | [extract-table.md](extract-table.md) |
| "text layout", "where is text" | [extract-layout.md](extract-layout.md) |
| "scan barcode", "scan QR", "product code" | [scan-code.md](scan-code.md) |
| "find online", "where to buy", "price" | [scan-and-search.md](scan-and-search.md) |
| "compare OCR", "which backend" | [compare-backends.md](compare-backends.md) |
| "batch OCR", "OCR multiple files" | [batch-ocr.md](batch-ocr.md) |

If no match: present the list and ask user to pick.

## Image Preprocessing

Quick reference — read full guide in [preprocessing.md](preprocessing.md):

| Problem | Fix |
|---------|-----|
| Low resolution | `raster_resize` to 2400-3200px |
| JPEG noise | `raster_colorspace` to "L" |
| Low contrast | `raster_adjust` contrast=2.0 |
| Skewed photo | `raster_perspective` |
| >4000px (Paddle limit) | `raster_resize` to 3000px |
