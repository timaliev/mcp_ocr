"""OTSL table markup: parse to a grid, render HTML, embed in Markdown.

Xiaomi-OCR-0 emits tables as OTSL. Each cell is introduced by a tag and the
text that follows it belongs to that cell; ``<nl>`` ends a row::

    <fcel>  cell carrying text     <ecel>  empty cell
    <lcel>  continues the cell at left
    <ucel>  continues the cell above
    <xcel>  continues both left and above
    <nl>    end of row

Only ``<fcel>`` and ``<ecel>`` start a cell. Continuation tags carry no text of
their own: in the flat grid they are blank, and in HTML they become
``colspan``/``rowspan`` on their origin cell.
"""

from __future__ import annotations

import html
import re

CELL_TAGS = ("<fcel>", "<ecel>", "<lcel>", "<ucel>", "<xcel>")
ROW_TAG = "<nl>"
ALL_TAGS = CELL_TAGS + (ROW_TAG,)

_TAG_RE = re.compile("|".join(re.escape(tag) for tag in ALL_TAGS))


def _iter_cells(otsl: str):
    """Yield ``(tag, text)`` pairs for every tag in ``otsl``."""
    position = 0
    pending = None
    for match in _TAG_RE.finditer(otsl):
        if pending is not None:
            yield pending, otsl[position : match.start()]
        pending = match.group(0)
        position = match.end()
    if pending is not None:
        yield pending, otsl[position:]


def parse_otsl(otsl: str) -> list[list[str]]:
    """Return the table as rectangular rows of cell text.

    ``<fcel>`` keeps its text; every other cell tag yields an empty string, so
    the result is a plain grid suitable for CSV or scoring.
    """
    rows: list[list[str]] = []
    row: list[str] = []
    for tag, text in _iter_cells(otsl):
        if tag == ROW_TAG:
            rows.append(row)
            row = []
        elif tag == "<fcel>":
            row.append(text.strip())
        else:
            row.append("")
    if row:
        rows.append(row)

    width = max((len(r) for r in rows), default=0)
    return [r + [""] * (width - len(r)) for r in rows]


def otsl_to_html(otsl: str) -> str:
    """Render OTSL as a ``<table>`` element with escaped cell text.

    Continuation tags extend their origin cell and become ``colspan`` /
    ``rowspan`` attributes; they are not emitted as separate cells.
    """
    grid: list[list[tuple[str, str]]] = []
    row: list[tuple[str, str]] = []
    for tag, text in _iter_cells(otsl):
        if tag == ROW_TAG:
            grid.append(row)
            row = []
        else:
            row.append((tag, text.strip()))
    if row:
        grid.append(row)

    width = max((len(r) for r in grid), default=0)
    for row in grid:
        row.extend([("<ecel>", "")] * (width - len(row)))

    continues_right = ("<lcel>", "<xcel>")
    continues_down = ("<ucel>", "<xcel>")

    parts = ["<table>"]
    for row_index, row in enumerate(grid):
        parts.append("<tr>")
        for column, (tag, text) in enumerate(row):
            if tag not in ("<fcel>", "<ecel>"):
                continue
            colspan = 1
            while (
                column + colspan < len(row)
                and row[column + colspan][0] in continues_right
            ):
                colspan += 1
            rowspan = 1
            while (
                row_index + rowspan < len(grid)
                and grid[row_index + rowspan][column][0] in continues_down
            ):
                rowspan += 1
            attrs = ""
            if colspan > 1:
                attrs += f' colspan="{colspan}"'
            if rowspan > 1:
                attrs += f' rowspan="{rowspan}"'
            parts.append(f"<td{attrs}>{html.escape(text)}</td>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def markdown_with_html_tables(markdown: str) -> str:
    """Replace every OTSL table block in ``markdown`` with an HTML table.

    The model emits a table as one or more consecutive lines containing OTSL
    tags; all other lines pass through unchanged.
    """
    result: list[str] = []
    pending: list[str] = []

    def flush() -> None:
        if pending:
            result.append(otsl_to_html("".join(pending)))
            pending.clear()

    for line in markdown.splitlines():
        if _TAG_RE.search(line):
            pending.append(line)
            continue
        flush()
        result.append(line)
    flush()
    return "\n".join(result)
