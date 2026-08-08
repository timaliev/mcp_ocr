# Text from Screenshot

Extract text from screenshots (terminal, error messages, UI dialogs).

## Steps

1. **Check resolution:**
```
mcp_raster_raster_info(path=<screenshot>)
```
If width < 1200 or DPI < 144:
```
mcp_raster_raster_resize(path=<screenshot>, width=2400, output=<upscaled>)
```

2. **Grayscale + sharpen:**
```
mcp_raster_raster_colorspace(path=<upscaled_or_orig>, target="L", output=<gray>)
mcp_raster_raster_adjust(path=<gray>, contrast=1.8, sharpness=2.5, output=<final>)
```

3. **OCR — Vision preferred** (handles terminal fonts + mixed Latin/Cyrillic):
```
mcp_ocr_ocr_text_vision(path=<final>)
```

4. **Present raw text** preserving original formatting.
