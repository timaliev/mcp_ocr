# Scan Code

Decode barcode or QR code from an image.

## Pre-flight

Check if raster MCP server is available:
```
mcp_raster_raster_info(path=<any_valid_image>)
```
If `mcp_raster_raster_info` fails: "Raster MCP server (mcp-images) not available. Install with: uv tool install mcp-images".

## Steps

```
mcp_raster_raster_qr(path=<image>)
```

Returns: `{"codes": [{"type": "QRCODE"|"EAN13"|..., "data": "..."}]}`

- **EAN-13/UPC-A:** 12-13 digit GTIN — search as product barcode
- **QR code:** typically URL or product code
- **Data Matrix:** industrial/shipping code

If no code found: check image quality (blurry, small, partially cropped).
Suggest user take a clearer photo or crop to just the barcode area.
