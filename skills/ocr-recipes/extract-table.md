# Extract Table

Extract structured table data from an image.

## Steps

1. **Xiaomi-OCR-0** (best structure fidelity, handles Cyrillic + English):
```
mcp_ocr_ocr_table_xiaomi(path=<image>)
```

2. **Fall back to Paddle** (cross-platform, no model download beyond PaddleOCR):
```
mcp_ocr_ocr_table_paddle(path=<image>)
```

3. **If both fail:** use `ocr_document_xiaomi` for the full page Markdown (tables are
   returned as HTML tables inside the Markdown), then extract the rows by hand.

Returns `headers` / `rows` / `csv` (plus `html` from Xiaomi). Present as markdown table
for readability.
