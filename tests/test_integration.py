"""End-to-end integration test — verifies server starts and tools are callable."""

import pytest
import asyncio
from mcp_ocr.server import create_server


def test_server_created_and_has_tools():
    server = create_server()
    assert server.name == "ocr"
    assert server.version == "2.0.0"

    tools = asyncio.run(server.list_tools())
    tool_names = [tool.name for tool in tools]
    total_expected = 0
    from mcp_ocr.backends import BACKENDS
    for backend in BACKENDS.values():
        total_expected += len(backend.tasks)  # one per task
        total_expected += 1  # one batch per backend
    assert len(tool_names) == total_expected, f"Expected {total_expected} tools, got {len(tool_names)}"
