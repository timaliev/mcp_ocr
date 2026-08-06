import pytest
import asyncio
from mcp.server import MCPServer

from mcp_ocr.server import create_server, handle_errors


def test_handle_errors_returns_success_on_ok():
    @handle_errors
    def good_func(x):
        return {"success": True, "value": x}

    result = good_func(42)
    assert result == {"success": True, "value": 42}


def test_handle_errors_catches_file_not_found():
    @handle_errors
    def raising_func(path):
        raise FileNotFoundError("nope")

    result = raising_func("test.png")
    assert result["success"] is False
    assert result["error"] == "ENOENT"


def test_handle_errors_catches_import_error():
    @handle_errors
    def bad_import():
        raise ImportError("no module")

    result = bad_import()
    assert result["success"] is False
    assert result["error"] == "EUNSUPPORTED"


def test_handle_errors_catches_generic():
    @handle_errors
    def oops():
        raise ValueError("boom")

    result = oops()
    assert result["success"] is False
    assert result["error"] == "EPROCESSING"
    assert "boom" in result["detail"]


def test_create_server_has_all_tools():
    server = create_server()
    tools = asyncio.run(server.list_tools())

    tool_names = [tool.name for tool in tools]
    # Vision: 3 tools (text, layout, table) + batch
    assert "ocr_text_vision" in tool_names
    assert "ocr_layout_vision" in tool_names
    assert "ocr_table_vision" in tool_names
    assert "ocr_batch_vision" in tool_names

    # Paddle: 3 tools (text, layout, table) + batch
    assert "ocr_text_paddle" in tool_names
    assert "ocr_layout_paddle" in tool_names
    assert "ocr_table_paddle" in tool_names
    assert "ocr_batch_paddle" in tool_names

    # PaddleOCR-VL: 5 tools (text, layout, table, formula, chart) + batch
    assert "ocr_text_paddleocr_vl" in tool_names
    assert "ocr_layout_paddleocr_vl" in tool_names
    assert "ocr_table_paddleocr_vl" in tool_names
    assert "ocr_formula_paddleocr_vl" in tool_names
    assert "ocr_chart_paddleocr_vl" in tool_names
    assert "ocr_batch_paddleocr_vl" in tool_names


def test_create_server_tool_has_description():
    server = create_server()
    tools = asyncio.run(server.list_tools())
    for tool in tools:
        assert tool.description, f"Tool {tool.name} has no description"
