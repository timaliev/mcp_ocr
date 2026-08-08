# Extract Table

Extract structured table data from an image.

## Steps

1. **Try Vision table extraction** (macOS 15+):
```
mcp_ocr_ocr_table_vision(path=<image>)
```

2. **Fall back to Paddle:**
```
mcp_ocr_ocr_table_paddle(path=<image>)
```

3. **If both table backends fail:** use `ocr_text_vision`, then align columns manually from text positions.

Returns CSV/JSON. Present as markdown table for readability.
