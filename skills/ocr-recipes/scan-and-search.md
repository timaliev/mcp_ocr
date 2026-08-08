# Scan and Search

Full pipeline: photo → barcode/QR → web search for product.

## Steps

1. **Decode barcode:**
```
mcp_raster_raster_qr(path=<product_photo>)
```

2. **Construct search:**
- URL → scrape title, search product name
- Numeric barcode → search `"<barcode> product buy price"`
- Random string → search as-is

3. **Search web:**
```
mcp_searxng_search_web(query="<constructed_query>", max_results=5)
```
Or:
```
deep_web_search(query="<query>", max_results=5)
```

4. **Present:**
- Product name + price range (if found)
- Top 3-5 shopping links
- Note if barcode lookup service would give better results

If no web search available: return decoded barcode data, suggest manual lookup.
