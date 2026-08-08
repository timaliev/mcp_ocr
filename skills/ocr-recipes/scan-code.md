# Scan Code

Decode barcode or QR code from an image.

## Steps

```
mcp_raster_raster_qr(path=<image>)
```

Returns: `{"codes": [{"type": "QRCODE"|"EAN13"|..., "data": "..."}]}`

- **EAN-13/UPC-A:** 12-13 digit GTIN — search as product barcode
- **QR code:** typically URL or product code
- **Data Matrix:** industrial/shipping code

If no code found: check image quality (blurry, small, partially cropped).
Suggest user take a clearer photo.
