# Document OCR

OCR a document page or dense text image.

## Steps

1. **If PDF:** use `mcp_pdf2md_pdf_to_markdown` first — faster for text-based PDFs.

2. **If scanned/image:**
```
mcp_raster_raster_info(path=<document>)
```

If >4000px on any side (Paddle limit), resize:
```
mcp_raster_raster_resize(path=<document>, width=3000, output=<resized>)
```

3. **OCR:**
```
mcp_ocr_ocr_text_vision(path=<resized_or_document>)
```

4. **Multi-page:** process pages sequentially, mark with `<!-- Page N -->`.

5. **Output:** full text preserving paragraph breaks. Note low-confidence regions.
