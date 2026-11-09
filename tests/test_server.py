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

    # Xiaomi-OCR-0: document parsing, tables, formulas, KIE + plain text
    assert "ocr_text_xiaomi" in tool_names
    assert "ocr_layout_xiaomi" in tool_names
    assert "ocr_table_xiaomi" in tool_names
    assert "ocr_formula_xiaomi" in tool_names
    assert "ocr_document_xiaomi" in tool_names
    assert "ocr_kie_xiaomi" in tool_names
    assert "ocr_batch_xiaomi" in tool_names

    # The PaddleOCR-VL backend was removed
    assert not [name for name in tool_names if name.endswith("paddleocr_vl")]


def test_kie_tool_accepts_fields():
    server = create_server()
    tools = {tool.name: tool for tool in asyncio.run(server.list_tools())}

    properties = tools["ocr_kie_xiaomi"].input_schema["properties"]

    assert "fields" in properties
    assert "path" in properties


def test_vision_tools_default_to_accurate_mode():
    """Default must not fall back to Vision's fast, Latin-only recognizer."""
    server = create_server()
    tools = {tool.name: tool for tool in asyncio.run(server.list_tools())}

    for name in ("ocr_text_vision", "ocr_layout_vision", "ocr_table_vision"):
        mode = tools[name].input_schema["properties"]["mode"]
        assert mode["default"] == "accurate", f"{name} defaults to {mode['default']}"


def test_xiaomi_tools_are_described():
    server = create_server()
    tools = {tool.name: tool for tool in asyncio.run(server.list_tools())}
    description = tools["ocr_document_xiaomi"].description
    assert "Xiaomi-OCR-0" in description
    assert "Markdown" in description


def test_create_server_tool_has_description():
    server = create_server()
    tools = asyncio.run(server.list_tools())
    for tool in tools:
        assert tool.description, f"Tool {tool.name} has no description"


def test_batch_tool_forwards_supported_arguments_only():
    """Batch helpers must not pass lang/mode to backends that do not accept them."""
    from mcp_ocr.server import _make_batch_fn

    class PathOnly:
        def extract(self, path):
            return {"success": True, "text": path}

    batch = _make_batch_fn(PathOnly().extract)
    result = asyncio.run(batch(["a.png", "b.png"], lang="russian", mode="base"))

    assert result["success"] is True
    assert [item["text"] for item in result["results"]] == ["a.png", "b.png"]
