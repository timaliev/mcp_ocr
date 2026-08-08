# Image Preprocessing for OCR

Quick reference for fixing common image quality issues before OCR.

## Diagnostics

Always start with:
```
mcp_raster_raster_info(path=<image>)
```
Check DPI, dimensions, format, mode.

## Fixes

| Problem | Detection | Fix |
|---------|-----------|-----|
| Low resolution | DPI < 200, width < 1200 | `raster_resize` to 2400-3200px wide |
| Color noise (JPEG artifacts) | Format=JPEG, mode=RGB | `raster_colorspace` to "L" (grayscale) |
| Low contrast (faded text) | Dark histogram | `raster_adjust` contrast=2.0 |
| Skewed/angled photo | Perspective distortion | `raster_perspective` with 4 corner points |
| Dark photo | Brightness histogram shifted left | `raster_adjust` brightness=1.3 |
| Large image (>4000px) | Paddle warning | `raster_resize` to 3000px on longer side |
| Glare/hotspots | Uneven brightness | `raster_adjust` brightness=0.9, contrast=1.5 |
| Background noise | Busy background, watermarks | `raster_bgremove` then OCR on clean foreground |

## Quick Recipe

For most document photos, this 2-step pipeline works:
```
mcp_raster_raster_colorspace(path=<input>, target="L", output=<gray>)
mcp_raster_raster_adjust(path=<gray>, contrast=2.0, sharpness=1.5, output=<ready>)
```
Then OCR the `<ready>` output.
