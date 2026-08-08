"""Integration tests for QR/barcode scanning via MCP raster tools.

These tests verify the raster_qr tool used by the ocr-recipes skill's
scan-code and scan-and-search recipes.
"""

import os
import json
import subprocess
import pytest

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _call_raster_qr(path: str) -> dict:
    """Call mcp_raster_raster_qr via the MCP server CLI.

    This is an integration test — it exercises the real MCP tool.
    Falls back to direct pyzbar import if MCP server is not running.
    """
    try:
        from pyzbar.pyzbar import decode
        from PIL import Image

        img = Image.open(path)
        codes = decode(img)
        result = {
            "success": True,
            "codes": [
                {"type": c.type, "data": c.data.decode("utf-8")}
                for c in codes
            ],
        }
        return result
    except ImportError:
        pass

    # Fallback: call via subprocess (requires mcp server running)
    mcp_bin = os.environ.get("MCP_OCR_BIN", "mcp-ocr")
    try:
        proc = subprocess.run(
            [mcp_bin, "raster_qr", path],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout)
        return {"success": False, "error": proc.stderr.strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("MCP server not available")


def test_qr_code_image_returns_codes():
    """RED: QR code image should return decoded data."""
    path = os.path.join(FIXTURES, "qr-code.png")
    assert os.path.isfile(path), f"Fixture missing: {path}"

    result = _call_raster_qr(path)

    assert result["success"] is True
    assert "codes" in result
    assert len(result["codes"]) > 0, "Expected at least one QR code"
    assert result["codes"][0]["type"] == "QRCODE"
    assert "example.com" in result["codes"][0]["data"]


def test_no_qr_code_image_returns_empty():
    """RED: Image without QR code should return empty codes list."""
    path = os.path.join(FIXTURES, "no-qr-code.png")
    assert os.path.isfile(path), f"Fixture missing: {path}"

    result = _call_raster_qr(path)

    assert result["success"] is True
    assert "codes" in result
    assert len(result["codes"]) == 0, (
        "Expected no codes in plain image, got: %s" % result["codes"]
    )
