# Compare Backends

Run same image through multiple OCR backends, compare results, recommend best.

## Steps

1. **Vision:**
```
mcp_ocr_ocr_text_vision(path=<image>)
```

2. **Paddle:**
```
mcp_ocr_ocr_text_paddle(path=<image>, lang=<lang>)
```

3. **PaddleOCR-VL** (if available):
```
mcp_ocr_ocr_text_paddleocr_vl(path=<image>)
```

## Comparison Criteria

| Metric | What to check |
|--------|---------------|
| Line count | Fewer lines = better text grouping |
| Confidence | Higher average = more reliable |
| Errors | Misread chars, wrong language mapping |
| Coverage | Any backend miss text entirely? |
| Speed | For user-facing use, faster is better |

Present comparison table. Recommend best backend for this specific image.

Use when OCR quality matters (legal docs, archival material, mixed-language text).
