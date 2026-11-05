"""Packaging: a backend extra must declare everything its backend imports.

The Xiaomi backend loads a Qwen3-VL checkpoint through transformers, whose image
processor imports torchvision. Missing it from the extra makes a fresh
``uv tool install 'mcp-ocr[xiaomi]'`` fail at the first OCR call with ECONFIG.
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _extras() -> dict[str, list[str]]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return project["optional-dependencies"]


def _joined(extra: str) -> str:
    return " ".join(_extras()[extra]).lower()


def test_xiaomi_extra_declares_runtime_dependencies():
    deps = _joined("xiaomi")
    assert "transformers" in deps
    assert "torch>=" in deps or deps.split().count("torch") == 1
    assert "torchvision" in deps
    assert "pillow" in deps


def test_all_extra_pulls_every_backend():
    all_deps = _joined("all")
    for backend in ("vision", "paddle", "xiaomi"):
        assert backend in all_deps
