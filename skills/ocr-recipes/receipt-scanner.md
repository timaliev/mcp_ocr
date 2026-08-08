# Receipt Scanner

Extract structured data from receipt or check photos.

## Steps

1. **Enhance** (receipts often low-contrast, curled paper):
```
mcp_raster_raster_adjust(path=<receipt>, contrast=2.0, sharpness=2.5, output=<enhanced>)
```

2. **OCR** — Vision preferred (best accuracy on mixed fonts/numbers):
```
mcp_ocr_ocr_text_vision(path=<enhanced>)
```
If Vision unavailable: `mcp_ocr_ocr_text_paddle(path=<enhanced>, lang="ru")` for Cyrillic receipts.

3. **Parse output:**
- **Total:** line matching `/total|итого|sum|всего/i` near bottom
- **Date:** line matching `\d{2}[./]\d{2}[./]\d{2,4}`
- **Items:** lines between header and total with price patterns (`\d+[.,]\d{2}`)
- **Tax:** line matching `/tax|нал|ндс|vat/i`
- **Store:** first 1-3 lines, often ALL CAPS

4. **Present:**
```
Store: <name>
Date: <date>
Items:
  - <item1>: <price1>
  - <item2>: <price2>
Total: <total>
Tax: <tax>
```
