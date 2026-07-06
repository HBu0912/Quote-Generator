"""Generate customer-facing PDF quotation document."""

from __future__ import annotations

import io
from datetime import date
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from calculator import QuoteCalculated, effective_gage_list
from customer_quote_layout import (
    COMPANY_ADDRESS,
    COMPANY_EMAIL,
    COMPANY_NAME,
    WEIGHT_NOTE,
    customer_quote_footer_texts,
    customer_quote_lead_rows,
    customer_quote_meta,
    customer_quote_table,
)

BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "logo.png"
SIGNATURE_PATH = BASE_DIR / "assets" / "signature.png"

BRAND = colors.HexColor("#2b5797")
BRAND_LIGHT = colors.HexColor("#d9e1f2")
ROW_ALT = colors.HexColor("#f7f9fc")
TEXT_MUTED = colors.HexColor("#555555")

PAGE_W, PAGE_H = landscape(letter)
MARGIN = 0.18 * inch
CONTENT_W = PAGE_W - 2 * MARGIN


CELL_PAD = 8  # LEFTPADDING + RIGHTPADDING from table style
MIN_COL_WIDTH = 0.28 * inch


def _flowable_width(flowable, max_wrap: float = 10000) -> float:
    w, _ = flowable.wrap(max_wrap, max_wrap)
    return w


def _autofit_col_widths(
    headers: list[str],
    row_texts: list[list[str]],
    total_width: float,
    hdr_style: ParagraphStyle,
    cell_style: ParagraphStyle,
) -> list[float]:
    """Size each column to its widest cell content, then scale to fill the page."""
    n = len(headers)
    if n == 0:
        return []

    raw = [0.0] * n
    for i, header in enumerate(headers):
        hdr_para = Paragraph(f"<b>{escape(header)}</b>", hdr_style)
        raw[i] = max(raw[i], _flowable_width(hdr_para))

    for row in row_texts:
        for i, text in enumerate(row[:n]):
            cell_para = _para(text, cell_style)
            raw[i] = max(raw[i], _flowable_width(cell_para))

    raw = [max(w + CELL_PAD, MIN_COL_WIDTH) for w in raw]
    total_raw = sum(raw)
    if total_raw <= 0:
        return [total_width / n] * n

    scale = total_width / total_raw
    return [w * scale for w in raw]


def _para(text: str, style: ParagraphStyle) -> Paragraph:
    safe = escape(text or "").replace("\n", "<br/>")
    return Paragraph(safe or "&nbsp;", style)


def _fit_image(path: Path, max_width: float, max_height: float) -> Image | None:
    if not path.exists():
        return None
    reader = ImageReader(str(path))
    iw, ih = reader.getSize()
    scale = min(max_width / iw, max_height / ih)
    return Image(str(path), width=iw * scale, height=ih * scale)


def generate_pdf(quote: QuoteCalculated) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=0.22 * inch,
        bottomMargin=0.22 * inch,
    )

    styles = getSampleStyleSheet()
    company_style = ParagraphStyle(
        "company", parent=styles["Normal"], fontSize=9, leading=12, alignment=TA_RIGHT, textColor=TEXT_MUTED
    )
    title_banner = ParagraphStyle(
        "banner", parent=styles["Heading1"], fontSize=17, alignment=TA_CENTER, textColor=colors.white, spaceAfter=0
    )
    meta_label = ParagraphStyle(
        "meta_label", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, textColor=TEXT_MUTED
    )
    meta_value = ParagraphStyle(
        "meta_value", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, fontName="Helvetica-Bold"
    )
    hdr = ParagraphStyle(
        "hdr",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )
    cell = ParagraphStyle(
        "cell", parent=styles["Normal"], fontSize=8.5, leading=11, alignment=TA_CENTER, wordWrap="CJK"
    )
    note_style = ParagraphStyle(
        "note", parent=styles["Normal"], fontSize=9, leading=12, alignment=TA_CENTER, textColor=TEXT_MUTED
    )
    terms_style = ParagraphStyle(
        "terms", parent=styles["Normal"], fontSize=9, leading=12, textColor=TEXT_MUTED
    )
    footer_label = ParagraphStyle(
        "footer_label", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold"
    )

    data_in = quote.input
    quote_meta = customer_quote_meta(quote)
    qdate = data_in.quotation_date or date.today()
    story = []

    logo = _fit_image(LOGO_PATH, 1.05 * inch, 0.68 * inch) or ""
    company_block = Paragraph(
        f"<b><font color='#2b5797'>{COMPANY_NAME}</font></b><br/>{COMPANY_ADDRESS}<br/>{COMPANY_EMAIL}",
        company_style,
    )
    header = Table([[logo, "", company_block]], colWidths=[1.15 * inch, CONTENT_W - 1.15 * inch - 3.8 * inch, 3.8 * inch])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (2, 0), (2, 0), "RIGHT")]))
    story.extend([header, Spacer(1, 6)])

    banner = Table([[Paragraph("QUOTATION SHEET", title_banner)]], colWidths=[CONTENT_W])
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([banner, Spacer(1, 6)])

    meta_rows = [
        [
            Paragraph("1.) Inquiry No#:", meta_label),
            Paragraph(quote_meta["inquiry_no"], meta_value),
            "",
            Paragraph("2.) Quotation Date:", meta_label),
            Paragraph(quote_meta["quotation_date"], meta_value),
        ],
    ]
    if quote_meta["show_factory"]:
        meta_rows.append(
            [Paragraph("Factory:", meta_label), Paragraph(quote_meta["factory_name"], meta_value), "", "", ""]
        )

    meta_col = CONTENT_W / 5
    meta_table = Table(meta_rows, colWidths=[meta_col * 1.1, meta_col * 1.2, meta_col * 0.6, meta_col * 1.2, meta_col * 1.2])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, BRAND),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([meta_table, Spacer(1, 6)])

    headers, row_texts = customer_quote_table(quote)
    col_widths = _autofit_col_widths(headers, row_texts, CONTENT_W, hdr, cell)
    table_data = [[Paragraph(f"<b>{escape(h)}</b>", hdr) for h in headers]]

    for values in row_texts:
        table_data.append([_para(v, cell) for v in values])

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    style_rules = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0bac8")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    items_table.setStyle(TableStyle(style_rules))
    story.extend([items_table, Spacer(1, 8)])

    lead_rows = [
        [Paragraph(f"<b>{escape(label)}</b>", terms_style), Paragraph(escape(val), terms_style)]
        for label, val in customer_quote_lead_rows(data_in)
    ]

    left_width = CONTENT_W * 0.58
    left_table = Table(lead_rows, colWidths=[2.0 * inch, left_width - 2.0 * inch])
    left_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    gage_entries = effective_gage_list(data_in.gage_list)
    if gage_entries:
        gage_hdr = ParagraphStyle(
            "gage_hdr", parent=terms_style, fontName="Helvetica-Bold", textColor=BRAND
        )
        gage_rows = [
            [Paragraph("<b>Gage List</b>", gage_hdr), ""],
            [Paragraph("<b>P/N</b>", gage_hdr), Paragraph("<b>Gage</b>", gage_hdr)],
        ]
        for entry in gage_entries:
            pn = entry["part_number"] or "—"
            gage_rows.append([
                Paragraph(escape(pn), terms_style),
                Paragraph(escape(entry["gage"]), terms_style),
            ])
        right_width = CONTENT_W - left_width
        gage_table = Table(gage_rows, colWidths=[right_width * 0.42, right_width * 0.58])
        gage_table.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, 0), (1, 0)),
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND_LIGHT),
                    ("BACKGROUND", (0, 1), (-1, 1), BRAND_LIGHT),
                    ("GRID", (0, 1), (-1, -1), 0.4, colors.HexColor("#b0bac8")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        lead_table = Table([[left_table, gage_table]], colWidths=[left_width, right_width])
        lead_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (1, 0), (1, 0), 10),
                ]
            )
        )
    else:
        lead_table = left_table

    story.extend([lead_table, Spacer(1, 6)])

    note_box = Table(
        [[Paragraph(f"<i>{escape(WEIGHT_NOTE)}</i>", note_style)]],
        colWidths=[CONTENT_W],
    )
    note_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbea")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e8c840")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([note_box, Spacer(1, 6)])

    for text in customer_quote_footer_texts(data_in):
        story.append(Paragraph(escape(text).replace("\n", "<br/>"), terms_style))
        story.append(Spacer(1, 2))

    story.extend([Spacer(1, 8), HRFlowable(width="100%", thickness=0.5, color=BRAND_LIGHT, spaceAfter=8)])

    sig_img = _fit_image(SIGNATURE_PATH, 2.8 * inch, 0.85 * inch)
    sig_content = sig_img if sig_img else Paragraph("", cell)
    sig_table = Table(
        [
            [Paragraph("Signature:", footer_label), sig_content, Paragraph("Date:", footer_label), Paragraph(quote_meta["quotation_date"], meta_value)],
        ],
        colWidths=[0.9 * inch, 3.5 * inch, 0.55 * inch, 1.5 * inch],
    )
    sig_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(sig_table)

    doc.build(story)
    return buf.getvalue()
