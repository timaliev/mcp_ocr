# Batch OCR

Process multiple images in one call.

## Steps

1. **Vision batch** (preferred):
```
mcp_ocr_ocr_batch_vision(paths=[<img1>, <img2>, ...])
```

2. **Paddle batch** (cross-platform):
```
mcp_ocr_ocr_batch_paddle(paths=[<img1>, <img2>, ...], lang=<lang>)
```

## Output

- Report: N images processed, M succeeded
- List failures with reasons (unsupported format, too large, empty image)
- For each image: include text + line count + avg confidence

## Pre-flight

Before batch, check all images exist and are readable:
```
for each path in paths:
    mcp_raster_raster_info(path=<path>)
```

Skip missing/broken files, report them, continue with valid ones.
