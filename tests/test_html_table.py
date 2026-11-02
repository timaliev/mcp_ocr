"""HTML tables (PaddleOCR structure output) to rectangular rows."""

from mcp_ocr.html_table import parse_html_table


def test_parses_simple_html_table():
    html = (
        "<table><tr><td>Item</td><td>Qty</td></tr>"
        "<tr><td>Server</td><td>2</td></tr></table>"
    )
    assert parse_html_table(html) == [["Item", "Qty"], ["Server", "2"]]


def test_merged_cells_keep_text_at_origin_and_blank_continuations():
    html = (
        "<table>"
        '<tr><td colspan="2">Merged</td></tr>'
        "<tr><td>A</td><td>B</td></tr>"
        "</table>"
    )
    assert parse_html_table(html) == [["Merged", ""], ["A", "B"]]
