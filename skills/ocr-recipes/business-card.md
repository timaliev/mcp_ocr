# Business Card Extraction

Extract contact information from business card photos.

## Steps

1. **If angled photo**, perspective-correct:
```
mcp_raster_raster_perspective(path=<card>, src_points=[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], dst_points=[[0,0],[w,0],[w,h],[0,h]], output=<flat>)
```

2. **Enhance:**
```
mcp_raster_raster_adjust(path=<flat_or_card>, contrast=2.0, sharpness=2.0, output=<enhanced>)
```

3. **OCR:**
```
mcp_ocr_ocr_text_vision(path=<enhanced>)
```

4. **Parse:**
- **Name:** first non-logo line, largest font
- **Company:** line with legal form (LLC, Inc, ООО, АО)
- **Phone:** matches `\+?[\d\s\(\)-]{7,}`
- **Email:** matches `[\w.+-]+@[\w-]+\.[\w.-]+`
- **Address:** multi-word, middle of card
- **Website:** starts with `www.` or contains `http`

5. **Present:**
```
Name: <name>
Company: <company>
Phone: <phone>
Email: <email>
Web: <website>
Address: <address>
```
