"""Xiaomi-OCR-0 backend: document parsing, tables, KIE and plain text.

The backend talks to a local vision-language model. Tests inject a ``generator``
so the OCR pipeline is exercised without loading the 0.8B model.
"""

import json

import pytest

from mcp_ocr.backends.xiaomi import XiaomiBackend


def _png(tmp_path, name="page.png"):
    path = tmp_path / name
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return str(path)


def _stub(output, calls=None):
    """Build a generator stub returning ``output`` for every prompt."""
    calls = calls if calls is not None else []

    def generator(path, prompt, max_tokens):
        calls.append({"path": path, "prompt": prompt, "max_tokens": max_tokens})
        return output

    return generator, calls


def test_extract_returns_model_text_and_lines(tmp_path):
    image = _png(tmp_path)
    generator, calls = _stub("Договор поставки № 42\nСумма: 1000 руб.")

    backend = XiaomiBackend(generator=generator)

    result = backend.extract(image)

    assert result["success"] is True
    assert result["text"] == "Договор поставки № 42\nСумма: 1000 руб."
    assert [line["text"] for line in result["lines"]] == [
        "Договор поставки № 42",
        "Сумма: 1000 руб.",
    ]
    assert calls[0]["path"] == image


def test_extract_missing_file_returns_enoent_without_calling_model(tmp_path):
    backend = XiaomiBackend(generator=_stub("unused")[0])

    result = backend.extract(str(tmp_path / "missing.png"))

    assert result["success"] is False
    assert result["error"] == "ENOENT"


def test_table_parses_otsl_into_rows(tmp_path):
    image = _png(tmp_path)
    otsl = "<fcel>Наименование<fcel>Сумма<nl><fcel>Сервер<fcel>1 690 000<nl>"
    backend = XiaomiBackend(generator=_stub(otsl)[0])

    result = backend.table(image)

    assert result["success"] is True
    table = result["tables"][0]
    assert table["headers"] == ["Наименование", "Сумма"]
    assert table["rows"] == [["Сервер", "1 690 000"]]
    assert table["csv"].splitlines() == ["Наименование,Сумма", "Сервер,1 690 000"]
    assert "<table>" in table["html"]


def test_table_without_otsl_reports_processing_error(tmp_path):
    image = _png(tmp_path)
    backend = XiaomiBackend(generator=_stub("I cannot read this image.")[0])

    result = backend.table(image)

    assert result["success"] is False
    assert result["error"] == "EPROCESSING"


def test_document_converts_embedded_otsl_table_to_html(tmp_path):
    image = _png(tmp_path)
    markdown = (
        "## Спецификация\n\n"
        "<fcel>Наименование<fcel>Сумма<nl><fcel>Сервер<fcel>100<nl>\n\n"
        "Итого: 100 рублей."
    )
    backend = XiaomiBackend(generator=_stub(markdown)[0])

    result = backend.document(image)

    assert result["success"] is True
    assert "## Спецификация" in result["markdown"]
    assert "Итого: 100 рублей." in result["markdown"]
    assert "<table>" in result["markdown"]
    assert "<fcel>" not in result["markdown"]


def test_formula_returns_latex(tmp_path):
    image = _png(tmp_path)
    backend = XiaomiBackend(generator=_stub("\\[E = mc^2\\]")[0])

    result = backend.formula(image)

    assert result["success"] is True
    assert result["latex"] == "\\[E = mc^2\\]"


def test_kie_parses_json_and_asks_for_requested_fields(tmp_path):
    image = _png(tmp_path)
    output = '```json\n{"date": "2026-03-12", "total": "1 245 000"}\n```'
    generator, calls = _stub(output)
    backend = XiaomiBackend(generator=generator)

    result = backend.kie(image, fields=["date", "total"])

    assert result["success"] is True
    assert result["data"] == {"date": "2026-03-12", "total": "1 245 000"}
    prompt = calls[0]["prompt"]
    assert '"date"' in prompt and '"total"' in prompt


def test_kie_non_json_output_reports_processing_error(tmp_path):
    image = _png(tmp_path)
    backend = XiaomiBackend(generator=_stub("not json at all")[0])

    result = backend.kie(image)

    assert result["success"] is False
    assert result["error"] == "EPROCESSING"
    assert result["raw"] == "not json at all"


def test_missing_dependencies_return_econfig(tmp_path):
    image = _png(tmp_path)

    def generator(path, prompt, max_tokens):
        raise ImportError("transformers is not installed")

    backend = XiaomiBackend(generator=generator)

    result = backend.extract(image)

    assert result["success"] is False
    assert result["error"] == "ECONFIG"
    assert "mcp-ocr[xiaomi]" in result["detail"]
