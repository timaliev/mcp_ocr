"""OTSL table markup: parsing to a grid, HTML rendering, markdown embedding."""

from mcp_ocr.otsl import parse_otsl


def test_parses_simple_two_by_two_table():
    rows = parse_otsl("<fcel>A<fcel>B<nl><fcel>1<fcel>2<nl>")
    assert rows == [["A", "B"], ["1", "2"]]


def test_empty_and_ragged_rows_are_padded():
    rows = parse_otsl("<fcel>A<ecel><nl><fcel>1<fcel>2<fcel>3<nl>")
    assert rows == [["A", "", ""], ["1", "2", "3"]]


def test_renders_simple_table_as_html():
    from mcp_ocr.otsl import otsl_to_html

    assert otsl_to_html("<fcel>A<fcel>B<nl><fcel>1<fcel>2<nl>") == (
        "<table>"
        "<tr><td>A</td><td>B</td></tr>"
        "<tr><td>1</td><td>2</td></tr>"
        "</table>"
    )


def test_renders_merged_cells_with_spans():
    from mcp_ocr.otsl import otsl_to_html

    otsl = "<fcel>A<lcel><nl><ucel><fcel>B<nl>"
    assert otsl_to_html(otsl) == (
        "<table>"
        '<tr><td colspan="2" rowspan="2">A</td></tr>'
        "<tr><td>B</td></tr>"
        "</table>"
    )


def test_replaces_embedded_otsl_with_html_table():
    from mcp_ocr.otsl import markdown_with_html_tables

    markdown = "Title\n\n<fcel>A<fcel>B<nl><fcel>1<fcel>2<nl>\n\nFooter"
    result = markdown_with_html_tables(markdown)
    assert "Title" in result
    assert "Footer" in result
    assert "<fcel>" not in result
    assert (
        "<table><tr><td>A</td><td>B</td></tr><tr><td>1</td><td>2</td></tr></table>"
        in result
    )
