"""Render architect revision markdown (REVISION_CLASHES_ARQUITECTO) to PDF."""

from __future__ import annotations

import re
from io import BytesIO

from fpdf import FPDF
from fpdf.enums import XPos

_EMOJI_REPLACEMENTS = {
    "✅": "OK",
    "❌": "NO",
    "⚠️": "(!)",
    "⚠": "(!)",
    "☐": "[ ]",
    "ℹ️": "i",
    "ℹ": "i",
    "→": "->",
    "·": "-",
}


def _pdf_text(value: str) -> str:
    text = str(value or "")
    for src, dst in _EMOJI_REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


def _strip_inline_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    return text.strip()


def _parse_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    cells = [_strip_inline_md(c.strip()) for c in stripped.strip("|").split("|")]
    if all(re.fullmatch(r"-+", c.replace(" ", "")) or c == "" for c in cells):
        return None
    return cells


class _RevisionPdf(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 8, _pdf_text(f"Página {self.page_no()}"), align="R")


class MarkdownPdfRenderer:
    def __init__(self) -> None:
        self._pdf = _RevisionPdf()
        self._pdf.set_auto_page_break(auto=True, margin=15)
        self._pdf.add_page()
        self._table_buffer: list[list[str]] = []
        self._in_code = False
        self._code_lines: list[str] = []

    def _flush_table(self) -> None:
        if not self._table_buffer:
            return
        pdf = self._pdf
        rows = self._table_buffer
        self._table_buffer = []
        ncols = max(len(r) for r in rows)
        if ncols == 0:
            return
        page_w = pdf.w - pdf.l_margin - pdf.r_margin
        col_w = page_w / ncols
        pdf.ln(2)
        for row_idx, row in enumerate(rows):
            while len(row) < ncols:
                row.append("")
            pdf.set_font("Helvetica", "B" if row_idx == 0 else "", 8)
            for cell in row:
                display = _pdf_text(cell)
                if len(display) > 72:
                    display = display[:69] + "..."
                pdf.cell(col_w, 6, display, border=1)
            pdf.ln()
        pdf.ln(2)

    def _flush_code(self) -> None:
        if not self._code_lines:
            return
        pdf = self._pdf
        pdf.ln(1)
        pdf.set_fill_color(245, 245, 245)
        pdf.set_font("Courier", size=9)
        for line in self._code_lines:
            pdf.multi_cell(0, 5, _pdf_text(line), fill=True, new_x=XPos.LMARGIN)
        pdf.ln(2)
        self._code_lines = []

    def _write_heading(self, text: str, level: int) -> None:
        self._flush_table()
        sizes = {1: 16, 2: 13, 3: 11}
        self._pdf.set_font("Helvetica", "B", sizes.get(level, 11))
        self._pdf.ln(2)
        self._pdf.multi_cell(0, 7, _pdf_text(text), new_x=XPos.LMARGIN)
        self._pdf.ln(1)

    def _write_paragraph(self, text: str, *, style: str = "", size: int = 10, indent: float = 0) -> None:
        self._flush_table()
        self._pdf.set_font("Helvetica", style, size)
        if indent:
            self._pdf.set_x(self._pdf.l_margin + indent)
        self._pdf.multi_cell(0, 5, _pdf_text(text), new_x=XPos.LMARGIN)
        self._pdf.ln(0.5)

    def feed_line(self, raw_line: str) -> None:
        line = raw_line.rstrip("\n")

        if line.strip().startswith("```"):
            if self._in_code:
                self._in_code = False
                self._flush_code()
            else:
                self._flush_table()
                self._in_code = True
            return

        if self._in_code:
            self._code_lines.append(line)
            return

        table_row = _parse_table_row(line)
        if table_row is not None:
            self._table_buffer.append(table_row)
            return
        self._flush_table()

        stripped = line.strip()
        if not stripped:
            self._pdf.ln(2)
            return

        if stripped == "---":
            self._pdf.ln(2)
            y = self._pdf.get_y()
            self._pdf.set_draw_color(180, 180, 180)
            self._pdf.line(self._pdf.l_margin, y, self._pdf.w - self._pdf.r_margin, y)
            self._pdf.ln(4)
            return

        if stripped.startswith("# "):
            self._write_heading(_strip_inline_md(stripped[2:]), 1)
            return
        if stripped.startswith("## "):
            self._write_heading(_strip_inline_md(stripped[3:]), 2)
            return
        if stripped.startswith("### "):
            self._write_heading(_strip_inline_md(stripped[4:]), 3)
            return

        if stripped.startswith("> "):
            self._write_paragraph(_strip_inline_md(stripped[2:]), style="I", size=9, indent=4)
            return

        numbered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if numbered:
            self._write_paragraph(f"{numbered.group(1)}. {_strip_inline_md(numbered.group(2))}", indent=2)
            return

        if stripped.startswith("- ") or stripped.startswith("* "):
            self._write_paragraph(f"- {_strip_inline_md(stripped[2:])}", indent=2)
            return

        self._write_paragraph(_strip_inline_md(stripped))

    def finish(self) -> bytes:
        self._flush_table()
        if self._in_code:
            self._in_code = False
            self._flush_code()
        buf = BytesIO()
        self._pdf.output(buf)
        return buf.getvalue()


def render_markdown_pdf(markdown_text: str) -> bytes:
    renderer = MarkdownPdfRenderer()
    for line in markdown_text.replace("\r\n", "\n").split("\n"):
        renderer.feed_line(line)
    return renderer.finish()
