# Extract Layout

Get text positions and types (header, paragraph, caption, table region).

## Steps

```
mcp_ocr_ocr_layout_vision(path=<image>)
```

Returns blocks with type, text, confidence, and bounding boxes.

Use for:
- Understanding document structure before extraction
- Extracting specific regions (header, footer, sidebar)
- Pre-processing before table extraction
- Identifying multi-column layouts
