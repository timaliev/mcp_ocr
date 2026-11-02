# Compare Backends

Run same image through multiple OCR backends, compare results, recommend best.

## Steps

1. **Vision:**
```
mcp_ocr_ocr_text_vision(path=<image>, lang=<lang>)
```

2. **Paddle:**
```
mcp_ocr_ocr_text_paddle(path=<image>, lang=<lang>)
```

3. **Xiaomi-OCR-0:**
```
mcp_ocr_ocr_text_xiaomi(path=<image>)
```

## Comparison Criteria

| Metric | What to check |
|--------|---------------|
| Line count | Fewer lines = better text grouping |
| Confidence | Higher average = more reliable (Xiaomi reports 1.0 — no calibration) |
| Errors | Misread chars, wrong language mapping |
| Coverage | Any backend miss text entirely? |
| Speed | For user-facing use, faster is better |

Use `ocr_document_xiaomi` instead of `ocr_text_xiaomi` when the comparison should
include table structure or formulas.

Present comparison table. Recommend best backend for this specific image.

Use when OCR quality matters (legal docs, archival material, mixed-language text).
