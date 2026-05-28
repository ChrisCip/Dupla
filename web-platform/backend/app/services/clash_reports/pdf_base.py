"""Shared ReportLab styles and table helpers for clash PDFs."""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

PAGE_MARGIN = 18 * mm
FOOTER_H = 12 * mm

DUPLA_PRIMARY = colors.HexColor("#C10D12")
DUPLA_PRIMARY_DARK = colors.HexColor("#9A0A0E")
DUPLA_MUTED = colors.HexColor("#666666")
LABEL_RED = DUPLA_PRIMARY
VALUE_BACKGROUND = colors.white
GRID_COLOR = colors.HexColor("#555555")

_FONT_BODY = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONT_MONO = "Courier"


def _register_unicode_fonts() -> None:
    global _FONT_BODY, _FONT_BOLD, _FONT_MONO
    candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ),
        (
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
        ),
    ]
    bundled = Path(__file__).resolve().parent / "fonts"
    if bundled.exists():
        candidates.insert(
            0,
            (
                str(bundled / "DejaVuSans.ttf"),
                str(bundled / "DejaVuSans-Bold.ttf"),
                str(bundled / "DejaVuSansMono.ttf"),
            ),
        )
    for regular, bold, mono in candidates:
        if os.path.isfile(regular) and os.path.isfile(bold):
            try:
                pdfmetrics.registerFont(TTFont("DuplaSans", regular))
                pdfmetrics.registerFont(TTFont("DuplaSans-Bold", bold))
                _FONT_BODY = "DuplaSans"
                _FONT_BOLD = "DuplaSans-Bold"
                if os.path.isfile(mono):
                    pdfmetrics.registerFont(TTFont("DuplaSansMono", mono))
                    _FONT_MONO = "DuplaSansMono"
                return
            except Exception:
                continue


_register_unicode_fonts()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ClashTitle",
            parent=base["Heading1"],
            fontName=_FONT_BOLD,
            fontSize=16,
            leading=20,
            spaceAfter=8,
            textColor=DUPLA_PRIMARY_DARK,
        ),
        "h2": ParagraphStyle(
            "ClashH2",
            parent=base["Heading2"],
            fontName=_FONT_BOLD,
            fontSize=12,
            leading=15,
            spaceBefore=10,
            spaceAfter=6,
            textColor=DUPLA_PRIMARY_DARK,
        ),
        "h3": ParagraphStyle(
            "ClashH3",
            parent=base["Heading3"],
            fontName=_FONT_BOLD,
            fontSize=10,
            leading=13,
            spaceBefore=6,
            spaceAfter=4,
            textColor=DUPLA_PRIMARY_DARK,
        ),
        "body": ParagraphStyle(
            "ClashBody",
            parent=base["BodyText"],
            fontName=_FONT_BODY,
            fontSize=9,
            leading=12,
        ),
        "small": ParagraphStyle(
            "ClashSmall",
            parent=base["BodyText"],
            fontName=_FONT_BODY,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#444444"),
        ),
        "mono": ParagraphStyle(
            "ClashMono",
            parent=base["Code"],
            fontName=_FONT_MONO,
            fontSize=8,
            leading=10,
            backColor=colors.HexColor("#f5f5f5"),
            borderPadding=4,
        ),
        "badge": ParagraphStyle(
            "ClashBadge",
            parent=base["BodyText"],
            fontName=_FONT_BOLD,
            fontSize=9,
            leading=11,
            backColor=colors.HexColor("#fff3cd"),
            borderPadding=4,
        ),
        "cell": ParagraphStyle(
            "ClashCell",
            parent=base["BodyText"],
            fontName=_FONT_BODY,
            fontSize=8,
            leading=10,
            wordWrap="CJK",
        ),
        "cell_dense": ParagraphStyle(
            "ClashCellDense",
            parent=base["BodyText"],
            fontName=_FONT_BODY,
            fontSize=7,
            leading=9,
            wordWrap="CJK",
        ),
        "cell_index": ParagraphStyle(
            "ClashCellIndex",
            parent=base["BodyText"],
            fontName=_FONT_BODY,
            fontSize=6.5,
            leading=8,
            wordWrap="CJK",
        ),
        "cell_header": ParagraphStyle(
            "ClashCellHeader",
            parent=base["BodyText"],
            fontName=_FONT_BOLD,
            fontSize=8,
            leading=10,
            textColor=colors.white,
            wordWrap="CJK",
        ),
        "cell_header_dense": ParagraphStyle(
            "ClashCellHeaderDense",
            parent=base["BodyText"],
            fontName=_FONT_BOLD,
            fontSize=7,
            leading=9,
            textColor=colors.white,
            wordWrap="CJK",
        ),
        "field_label": ParagraphStyle(
            "ClashFieldLabel",
            parent=base["BodyText"],
            fontName=_FONT_BOLD,
            fontSize=8,
            leading=10,
            textColor=colors.black,
        ),
        "field_value": ParagraphStyle(
            "ClashFieldValue",
            parent=base["BodyText"],
            fontName=_FONT_BODY,
            fontSize=8,
            leading=10,
            textColor=colors.black,
        ),
        "alias": ParagraphStyle(
            "ClashAlias",
            parent=base["BodyText"],
            fontName=_FONT_MONO,
            fontSize=7,
            leading=9,
            splitLongWords=0,
        ),
    }


def _escape(text: Any) -> str:
    s = str(text if text is not None else "")
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def P(text: Any, style: str = "body") -> Paragraph:
    return Paragraph(_escape(text), _styles()[style])


def P_cell(text: Any, *, dense: bool = False, index: bool = False) -> Paragraph:
    if index:
        style = "cell_index"
    elif dense:
        style = "cell_dense"
    else:
        style = "cell"
    return Paragraph(_escape(text), _styles()[style])


def P_cell_id(text: Any) -> Paragraph:
    """Wrap long incident IDs at underscores for narrow index columns."""
    raw = str(text if text is not None else "")
    if len(raw) > 14 and "_" in raw:
        split_at = raw.index("_") + 1
        html = f"{_escape(raw[:split_at])}<br/>{_escape(raw[split_at:])}"
        return Paragraph(html, _styles()["cell_index"])
    return Paragraph(_escape(raw), _styles()["cell_index"])


def P_cell_lines(text: Any, *, index: bool = False) -> Paragraph:
    """Paragraph cell allowing explicit <br/> line breaks (content is escaped per line)."""
    style = _styles()["cell_index" if index else "cell_dense"]
    parts = str(text if text is not None else "").split("<br/>")
    html = "<br/>".join(_escape(part) for part in parts)
    return Paragraph(html, style)


def _scale_col_widths(col_widths: list[float], avail: float) -> list[float]:
    if not col_widths:
        return col_widths
    total = sum(col_widths)
    if total <= 0:
        return [avail / len(col_widths)] * len(col_widths)
    return [w * avail / total for w in col_widths]


def P_alias(text: Any) -> Paragraph:
    from app.services.clash_reports.formatting import format_alias_for_pdf

    return Paragraph(format_alias_for_pdf(str(text)), _styles()["alias"])


def P_alias_pair(alias_a: str, alias_b: str) -> Paragraph:
    from app.services.clash_reports.formatting import format_alias_pair_for_pdf

    return Paragraph(format_alias_pair_for_pdf(alias_a, alias_b), _styles()["alias"])


def _field_table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (0, -1), LABEL_RED),
            ("BACKGROUND", (1, 0), (1, -1), VALUE_BACKGROUND),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.35, GRID_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def meta_block(rows: Iterable[tuple[str, str]]) -> Table:
    return field_table(rows)


def field_table(rows: Iterable[tuple[str, str]], *, label_width: float | None = None) -> Table:
    styles = _styles()
    data = [
        [Paragraph(_escape(k), styles["field_label"]), Paragraph(_escape(v), styles["field_value"])]
        for k, v in rows
    ]
    lw = label_width if label_width is not None else 4.2 * cm
    avail = A4[0] - 2 * PAGE_MARGIN
    vw = max(avail - lw, 40 * mm)
    table = Table(data, colWidths=[lw, vw], hAlign="LEFT")
    table.setStyle(_field_table_style())
    return table


def data_table(
    headers: list[str],
    rows: list[list[Any]],
    *,
    col_widths: list[float] | None = None,
    page_width: float | None = None,
    dense: bool = False,
    index_mode: bool = False,
) -> Table:
    styles = _styles()
    head_style = styles["cell_header_dense" if (dense or index_mode) else "cell_header"]
    cell_style = styles["cell_index" if index_mode else ("cell_dense" if dense else "cell")]
    head = [Paragraph(_escape(h), head_style) for h in headers]
    body = []
    for row in rows:
        cells = []
        for c in row:
            if isinstance(c, Paragraph):
                cells.append(c)
            else:
                cells.append(Paragraph(_escape(c), cell_style))
        body.append(cells)
    data = [head, *body]
    avail = page_width if page_width is not None else (A4[0] - 2 * PAGE_MARGIN)
    if col_widths is None:
        col_widths = [avail / len(headers)] * len(headers)
    elif len(col_widths) == len(headers):
        col_widths = _scale_col_widths(col_widths, avail)
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DUPLA_PRIMARY_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, GRID_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fdf2f2")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def landscape_page_width() -> float:
    return landscape(A4)[0] - 2 * PAGE_MARGIN


class ClashPdfDoc(BaseDocTemplate):
    def __init__(self, buffer: BytesIO, *, title: str, meta_line: str) -> None:
        self._doc_title = title
        self._meta_line = meta_line
        super().__init__(
            buffer,
            pagesize=A4,
            leftMargin=PAGE_MARGIN,
            rightMargin=PAGE_MARGIN,
            topMargin=PAGE_MARGIN + 6 * mm,
            bottomMargin=PAGE_MARGIN + FOOTER_H,
            title=title,
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="portrait",
        )
        ls_frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            landscape(A4)[0] - 2 * PAGE_MARGIN,
            landscape(A4)[1] - 2 * PAGE_MARGIN - FOOTER_H,
            id="landscape",
        )
        self.addPageTemplates(
            [
                PageTemplate(id="portrait", frames=[frame], pagesize=A4, onPage=self._draw_page),
                PageTemplate(
                    id="landscape",
                    frames=[ls_frame],
                    pagesize=landscape(A4),
                    onPage=self._draw_page,
                ),
            ]
        )

    def _draw_page(self, canvas, doc) -> None:
        canvas.saveState()
        pw, ph = doc.pagesize
        canvas.setStrokeColor(DUPLA_PRIMARY)
        canvas.setLineWidth(1)
        canvas.line(PAGE_MARGIN, ph - PAGE_MARGIN - 2, pw - PAGE_MARGIN, ph - PAGE_MARGIN - 2)
        canvas.setFont(_FONT_BOLD, 8)
        canvas.setFillColor(DUPLA_PRIMARY_DARK)
        canvas.drawString(PAGE_MARGIN, ph - PAGE_MARGIN, self._doc_title)
        canvas.setFont(_FONT_BODY, 8)
        canvas.setFillColor(DUPLA_MUTED)
        canvas.drawRightString(pw - PAGE_MARGIN, 10 * mm, f"Pagina {doc.page}")
        canvas.drawString(PAGE_MARGIN, 10 * mm, self._meta_line)
        canvas.restoreState()


def build_pdf(story: list[Any], *, title: str, meta_line: str) -> bytes:
    buf = BytesIO()
    doc = ClashPdfDoc(buf, title=title, meta_line=meta_line)
    doc.build(story)
    return buf.getvalue()


def section(title: str) -> list[Any]:
    return [P(title, "h2"), Spacer(1, 4)]


def page_break_landscape() -> list[Any]:
    return [NextPageTemplate("landscape"), PageBreak()]


def page_break_portrait() -> list[Any]:
    return [NextPageTemplate("portrait"), PageBreak()]
