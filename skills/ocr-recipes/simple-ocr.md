# Simple OCR

Quick text extraction — when user just says "read this" or "what does it say."

## Steps

```
mcp_ocr_ocr_text_vision(path=<image>)
```

No preprocessing unless image is clearly problematic (low-res, dark, skewed).
If Vision unavailable, fall back to Paddle with appropriate `lang`.

Present raw text directly. Include line count and average confidence in summary.
