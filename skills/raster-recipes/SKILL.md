---
name: raster-recipes
description: >
  Everyday raster image recipes using MCP raster + OCR tools. Auto-discovers
  available mcp_raster_* and mcp_ocr_* capabilities and adapts recipe offerings.
  Bundled with mcp_ocr package. Auto-loads in Pi when package is installed.
  Use when user asks to fix/enhance photos, remove red eyes, make colors
  vivid, extract product info from barcodes/QR, prepare images for web/social,
  or any everyday photo editing task.
---

# Raster Recipes via MCP Tools

Everyday image tasks using **MCP raster + mcp_ocr tools**. Auto-discovers
capabilities and adapts. No Python scripts, no external CLI — just MCP calls.

> **Bundled with [mcp_ocr](https://github.com/timaliev/mcp_ocr).**
> Install `mcp_ocr[all]` and this skill auto-loads in Pi.

---

## Phase 1: Capability Discovery

Before offering recipes, check what's available:

```
mcp_raster_raster_info(path=any_valid_image)
```

If `mcp_raster_raster_info` returns successfully → raster tools available.

Then map discovered tools to recipe tiers:

| Check | Tier unlocked |
|-------|:-------------:|
| `raster_adjust`, `raster_filter` respond | **A — Basic** |
| + `raster_crop`, `raster_resize`, `raster_text` | **B — Intermediate** |
| + `raster_qr`, `raster_diff`, `raster_bgremove` | **C — Advanced** |
| + `mcp_ocr_*` tools respond | **D — Combined** |
| + `mcp_searxng_*` or web search | **E — Web-aware** |

If discovery fails entirely: "Raster MCP tools not available. Install mcp-images."

---

## Phase 2: Recipe Selection

Match user's natural language request to the best recipe. Map common phrasing:

| User says | Recipe |
|-----------|--------|
| "make it pop", "vivid", "more colorful", "dull photo" | `vivid-colors` |
| "too dark", "brighten", "lighten up" | `fix-brightness` |
| "blurry", "sharpen", "not sharp" | `sharpen-image` |
| "red eyes", "remove red eyes" | `remove-red-eyes` |
| "watermark", "add my name", "sign" | `add-watermark` |
| "passport photo", "id photo", "document photo" | `passport-photo` |
| "before after", "compare", "what changed" | `compare-images` |
| "remove background", "cut out", "isolate" | `remove-background` |
| "what product is this", "scan barcode", "scan qr" | `scan-code` |
| "find this online", "where to buy", "price check" | `scan-and-search` |
| "collage", "put side by side", "combine images" | `simple-collage` |
| "fix old photo", "restore", "enhance photo" | `restore-photo` |

If no clear match: present available recipes and let user pick.

---

## Tier A — Basic Recipes

Available when `raster_adjust` + `raster_filter` work.

### Recipe: vivid-colors

```text
mcp_raster_raster_adjust(path=<input>, saturation=1.4, contrast=1.15, output=<vivid_output>)
```

- saturation=1.3–1.5 for subtle pop
- contrast=1.1–1.2 to deepen shadows
- Never exceed saturation=2.0 (looks unnatural)

### Recipe: fix-brightness

```text
mcp_raster_raster_adjust(path=<input>, brightness=1.3, contrast=1.1, output=<bright_output>)
```

For very dark images: brightness=1.5, contrast=1.2
For slightly dark: brightness=1.15

### Recipe: sharpen-image

```text
mcp_raster_raster_adjust(path=<input>, sharpness=2.0, output=<sharp_output>)
```

- sharpness=1.5 for mild (slightly soft photos)
- sharpness=2.5 for aggressive (motion blur, out of focus)
- sharpness=3.0 max — beyond creates halos

### Recipe: auto-enhance

```text
mcp_raster_raster_enhance(path=<input>, mode="all", output=<enhanced_output>)
```

One-call fix for balance/color/sharpness. Good starting point.

### Recipe: grayscale-convert

```text
mcp_raster_raster_filter(path=<input>, filter_name="grayscale", output=<gray_output>)
```

### Recipe: invert-colors

```text
mcp_raster_raster_filter(path=<input>, filter_name="invert", output=<inverted_output>)
```

---

## Tier B — Intermediate Recipes

Available when Tier A + `raster_crop`, `raster_resize`, `raster_text` work.

### Recipe: remove-red-eyes

Red-eye: red pupils in flash photography. Fix by isolating eyes and
desaturating the red channel.

Steps:
1. Get dimensions:
```text
mcp_raster_raster_info(path=<input>)
```

2. Crop eye region (user provides coordinates or estimate from face):
```text
mcp_raster_raster_crop(path=<input>, left=<lx>, top=<ty>, right=<rx>, bottom=<by>, output=<eye_crop>)
```

3. Desaturate red channel in crop:
```text
mcp_raster_raster_adjust(path=<eye_crop>, saturation=0.0, brightness=1.1, output=<fixed_eye>)
```

4. If single-eye fix is enough, return fixed_eye. For full face, blend manually.

**Heuristic for auto-detection**: if user doesn't provide coordinates:
- Assume face centered in top 60% of image
- Left eye: ~25-40% from left, 20-35% from top
- Right eye: ~60-75% from left, 20-35% from top
- Crop each with (width×0.15, height×0.1) sized rectangles

### Recipe: add-watermark

```text
mcp_raster_raster_text(path=<input>, text="© Name", x=<w-150>, y=<h-40>, size=18, color="white", output=<watermarked>)
```

Position defaults:
- Bottom-right: x=img_width - text_width_estimate, y=img_height - 30
- Center: x=img_width/2 - text_width_estimate/2, y=img_height/2
- Use semi-transparent: color="rgba(255,255,255,128)" or just "gray"

For repeat-tile watermark: call raster_text multiple times at grid positions.

### Recipe: passport-photo

Standard passport/ID photo: 35×45mm, white background, face centered.

```text
# 1. Remove background
mcp_raster_raster_bgremove(path=<input>, output=<no_bg>)

# 2. Resize to 35×45mm at 300 DPI = 413×531 px
mcp_raster_raster_resize(path=<no_bg>, width=413, height=531, fit="cover", output=<passport>)
```

If `raster_bgremove` not available (Tier C), use:
```text
mcp_raster_raster_resize(path=<input>, width=413, height=531, fit="cover", output=<passport>)
```

### Recipe: simple-collage

Side-by-side or grid arrangement using crop + blend.

```text
# 1. Resize both to same height
mcp_raster_raster_resize(path=<img1>, height=600, output=<r1>)
mcp_raster_raster_resize(path=<img2>, height=600, output=<r2>)

# 2. Get dimensions
mcp_raster_raster_info(path=<r1>)
mcp_raster_raster_info(path=<r2>)

# 3. Horizontal: create canvas wide enough, place images side by side
# (Manual: describe layout, use raster_perspective or blend for placement)
```

For 4-image grid: 2×2 layout, same process.

### Recipe: resize-for-social

```text
# Instagram square (1080×1080)
mcp_raster_raster_resize(path=<input>, width=1080, height=1080, fit="cover", output=<ig_output>)

# Twitter/Web (1200×675 — 16:9)
mcp_raster_raster_resize(path=<input>, width=1200, height=675, fit="cover", output=<twitter_output>)

# LinkedIn (1200×627)
mcp_raster_raster_resize(path=<input>, width=1200, height=627, fit="cover", output=<linkedin_output>)
```

---

## Tier C — Advanced Recipes

Available when Tier B + `raster_qr`, `raster_diff`, `raster_bgremove` work.

### Recipe: scan-code

Extract product identifier from barcode or QR code.

```text
mcp_raster_raster_qr(path=<input>)
```

Returns `{"codes": [{"type": "QRCODE"|"EAN13"|..., "data": "..."}]}`.

Extract the data field — it's the product identifier.

For retail barcodes (EAN-13/UPC-A): the 12-13 digit number is the GTIN.
For QR codes: typically a URL or product code.

### Recipe: scan-and-search

Full pipeline from photo to web search:

1. Decode barcode/QR:
```text
mcp_raster_raster_qr(path=<input>)
```

2. Construct search query from decoded data:
   - If URL: scrape the URL for product name, then search
   - If numeric barcode: search directly `"<barcode> product"`
   - If random string: search as-is

3. Execute search:
```text
deep_web_search(query="<constructed_search_query>", max_results=5)
```
Or if searxng available:
```text
mcp_searxng_search_web(query="<search>", max_results=5)
```

4. Present results:
   - Product name + price range (if found)
   - Top 3-5 shopping links
   - Note if barcode lookup service would give better results

**Fallback**: if no web search available, return decoded barcode data and
suggest user searches manually.

### Recipe: compare-images

```text
mcp_raster_raster_diff(path1=<before>, path2=<after>)
```

Returns SSIM score (0-1, closer to 1 = more similar) and diff image.
- 0.95+ = nearly identical
- 0.80–0.95 = noticeable differences
- < 0.80 = significantly different

Also get individual histograms for channel comparison:
```text
mcp_raster_raster_histogram(path=<before>, channel="all")
mcp_raster_raster_histogram(path=<after>, channel="all")
```

### Recipe: remove-background

```text
mcp_raster_raster_bgremove(path=<input>, output=<no_bg_output>)
```

Returns RGBA image with transparent background. Follow with:
- `raster_resize` for product listings (square, white canvas)
- `raster_convert` to JPEG for web (auto-fills transparency with white)

### Recipe: product-isolation

For e-commerce: remove background, resize to square, add padding.

```text
# 1. Remove background
mcp_raster_raster_bgremove(path=<input>, output=<no_bg>)

# 2. Get dimensions, resize to square with padding
mcp_raster_raster_resize(path=<no_bg>, width=1000, height=1000, fit="contain", output=<isolated>)
```

---

## Tier D — Combined Recipes

Available when `mcp_ocr_*` tools respond.

### Recipe: receipt-scanner

Extract structured data from receipt photos.

```text
# 1. Enhance
mcp_raster_raster_adjust(path=<receipt>, contrast=2.0, sharpness=2.5, output=<enhanced>)

# 2. OCR
mcp_ocr_ocr_text_vision(path=<enhanced>)

# 3. Parse output:
#    - Total: line matching /total|итого|sum/i near bottom
#    - Date: line matching date pattern
#    - Items: lines between header and total with price patterns
#    - Tax: line matching /tax|нал|ндс/i
```

### Recipe: business-card

```text
# 1. Perspective-correct if photo at angle
mcp_raster_raster_perspective(path=<card>, src_points=[[...]], dst_points=[[...]], output=<flat>)

# 2. Enhance
mcp_raster_raster_adjust(path=<flat>, contrast=2.0, sharpness=2.0, output=<enhanced>)

# 3. OCR
mcp_ocr_ocr_text_vision(path=<enhanced>)
# Parse: name (first/top lines), company, phone, email, address
```

### Recipe: text-from-screenshot

```text
# 1. Check if enhancement needed
mcp_raster_raster_info(path=<screenshot>)
# DPI < 144 or width < 1200 → resize first

# 2. Convert to grayscale + sharpen
mcp_raster_raster_colorspace(path=<screenshot>, target="L", output=<gray>)
mcp_raster_raster_adjust(path=<gray>, contrast=1.8, sharpness=2.5, output=<final>)

# 3. OCR
mcp_ocr_ocr_text_vision(path=<final>)
```

---

## Tier E — Web-Aware Recipes

Available when web search tools present.

### Recipe: product-finder

Full pipeline from photo to shopping:

```text
# 1. Try barcode first
mcp_raster_raster_qr(path=<product_photo>)

# 2. If no barcode found:
#    - Try OCR on any visible text
#    - OR: describe image (product category hint from filename/user context)

# 3. Search
deep_web_search(query="buy <product_identifier> price", max_results=10)

# 4. Compare prices
#    Parse results for price patterns ($XX.XX, €XX, etc.)
#    Show range + top 3 stores
```

---

## General Tips

### Output Quality

- Always save to descriptive output names: `<original>_vivid.png`, `<original>_sharp.png`
- PNG for quality, JPEG for size-sensitive outputs
- Check file size after conversion — report savings

### Batch Processing

Multiple images → apply same recipe to each:
```
for each image in list:
    mcp_raster_raster_adjust(path=image, ...)
```

Report: N images processed, M succeeded, 0 failed.

### Parameter Tuning

Default values work for 80% of cases. Tune when:
- User says "more" or "less" → adjust parameter ±20%
- Image looks unnatural → back off (saturation > 2.0, sharpness > 3.0)
- Dark/light extremes → double brightness adjustments
