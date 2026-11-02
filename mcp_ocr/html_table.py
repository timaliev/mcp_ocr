"""Parse HTML ``<table>`` markup into rectangular rows of text.

PaddleOCR's structure pipeline returns tables as HTML (``pred_html``). This
module turns that into plain rows once, so callers get the same ``headers`` /
``rows`` shape as every other backend. ``rowspan``/``colspan`` cells keep their
text in the origin position; the cells they cover are empty strings.
"""

from __future__ import annotations

from html.parser import HTMLParser


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[dict]] = []
        self._row: list[dict] | None = None
        self._cell: dict | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
            self.rows.append(self._row)
        elif tag in ("td", "th"):
            attributes = dict(attrs)
            self._cell = {
                "text": "",
                "colspan": _span(attributes.get("colspan")),
                "rowspan": _span(attributes.get("rowspan")),
            }
            if self._row is None:
                self._row = []
                self.rows.append(self._row)
            self._row.append(self._cell)

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._cell = None
        elif tag == "tr":
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell["text"] += data


def _span(value) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, number)


def _occupied(grid: dict[int, dict[int, str]], row: int, column: int) -> bool:
    return column in grid.get(row, {})


def _next_free(grid: dict[int, dict[int, str]], row: int, column: int) -> int:
    while _occupied(grid, row, column):
        column += 1
    return column


def parse_html_table(markup: str) -> list[list[str]]:
    """Return the first HTML table in ``markup`` as rectangular rows."""
    parser = _TableParser()
    parser.feed(markup)
    if not parser.rows:
        return []

    grid: dict[int, dict[int, str]] = {}
    for row_index, cells in enumerate(parser.rows):
        column = 0
        for cell in cells:
            column = _next_free(grid, row_index, column)
            for row_offset in range(cell["rowspan"]):
                for column_offset in range(cell["colspan"]):
                    target_row = row_index + row_offset
                    target_column = column + column_offset
                    grid.setdefault(target_row, {})[target_column] = (
                        cell["text"].strip() if (row_offset, column_offset) == (0, 0) else ""
                    )
            column += cell["colspan"]

    if not grid:
        return []
    height = max(grid) + 1
    width = max(max(columns) for columns in grid.values()) + 1
    return [
        [grid.get(row, {}).get(column, "") for column in range(width)]
        for row in range(height)
    ]
