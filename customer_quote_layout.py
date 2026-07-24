"""Shared customer-facing quote layout (PDF and external Excel)."""

from __future__ import annotations

from datetime import date

from calculator import (
    QuoteCalculated,
    QuoteInput,
    effective_payment_terms,
    line_field_visible,
    pdf_column_label,
    sample_field_visible,
)

COMPANY_NAME = "Toption (Asia) Company Limited"
COMPANY_ADDRESS = (
    "Room 606, No. 02 Nguyen Khac Vien Street, Tan My Ward, "
    "District 7, Ho Chi Minh City, Vietnam"
)
COMPANY_EMAIL = "business@toptionasia.com"

WEIGHT_NOTE = (
    "NOTE: The quote is based on the estimated weight by the factory and the final cost will be "
    "adjusted accordingly if the difference between the actual weight and the estimated weight exceeds 3%."
)


def _money(val: float, places: int = 2) -> str:
    return f"{val:,.{places}f}"


def _pdf_col_defs():
    return [
        ("item_no", True, lambda li: str(li.item_no)),
        ("part_number", False, lambda li: li.part_number),
        ("cast_dwg", False, lambda li: li.cast_dwg),
        ("mach_dwg", False, lambda li: li.mach_dwg),
        ("description", False, lambda li: li.description),
        ("material", False, lambda li: li.material),
        ("qty", True, lambda li: str(li.qty)),
        ("unit_pricing_fob_usd", True, lambda li: f"${_money(li.unit_pricing_fob_usd)}"),
        ("factory_weight_kg", False, lambda li: _money(li.factory_weight_kg)),
        ("other_finish", False, lambda li: li.other_finish),
        ("pressure_testing", False, lambda li: li.pressure_testing),
        (
            "sample_quoted_total_usd",
            False,
            lambda li: f"${_money(li.sample_quoted_total_usd)}" if li.sample_factory_cost_vnd > 0 else "",
        ),
        ("tooling_fee_usd", False, lambda li: f"${_money(li.tooling_fee_usd)}"),
    ]


def _excel_col_defs():
    return [
        ("item_no", True, lambda li: li.item_no, "0"),
        ("part_number", False, lambda li: li.part_number or None, None),
        ("cast_dwg", False, lambda li: li.cast_dwg or None, None),
        ("mach_dwg", False, lambda li: li.mach_dwg or None, None),
        ("description", False, lambda li: li.description or None, None),
        ("material", False, lambda li: li.material or None, None),
        ("qty", True, lambda li: li.qty, "#,##0"),
        ("unit_pricing_fob_usd", True, lambda li: li.unit_pricing_fob_usd, "$#,##0.00"),
        ("factory_weight_kg", False, lambda li: li.factory_weight_kg or None, "#,##0.00"),
        ("other_finish", False, lambda li: li.other_finish or None, None),
        ("pressure_testing", False, lambda li: li.pressure_testing or None, None),
        (
            "sample_quoted_total_usd",
            False,
            lambda li: li.sample_quoted_total_usd if li.sample_factory_cost_vnd > 0 else None,
            "$#,##0.00",
        ),
        ("tooling_fee_usd", False, lambda li: li.tooling_fee_usd or None, "$#,##0.00"),
    ]


def _visible_col_defs(quote: QuoteCalculated, defs):
    visible = []
    for field, always, fn, *rest in defs:
        if always:
            visible.append((field, fn, *rest))
        elif field.startswith("sample_"):
            if sample_field_visible(quote.line_items):
                visible.append((field, fn, *rest))
        elif line_field_visible(quote.line_items, field):
            visible.append((field, fn, *rest))
    return visible


def pdf_visible_fields(quote: QuoteCalculated):
    return [(field, fn) for field, fn, *_ in _visible_col_defs(quote, _pdf_col_defs())]


def customer_quote_table(quote: QuoteCalculated) -> tuple[list[str], list[list[str]]]:
    """Return PDF line-item headers and formatted row values."""
    labels = quote.input.line_item_column_labels
    specs = [(pdf_column_label(labels, field), fn) for field, fn in pdf_visible_fields(quote)]
    headers = [h for h, _ in specs]
    rows = [[fn(li) for _, fn in specs] for li in quote.line_items]
    return headers, rows


def customer_quote_table_excel(
    quote: QuoteCalculated,
) -> tuple[list[str], list[list], list[str | None]]:
    """Return Excel line-item headers, numeric row values, and per-column number formats."""
    labels = quote.input.line_item_column_labels
    specs = _visible_col_defs(quote, _excel_col_defs())
    headers = [pdf_column_label(labels, field) for field, *_ in specs]
    formats = [fmt for *_, fmt in specs]
    rows = [[fn(li) for _, fn, *_ in specs] for li in quote.line_items]
    return headers, rows, formats


def customer_quote_meta(quote: QuoteCalculated) -> dict:
    data = quote.input
    qdate = data.quotation_date or date.today()
    return {
        "inquiry_no": data.inquiry_no,
        "quotation_date": qdate.strftime("%B %d, %Y"),
        "quotation_date_iso": qdate.isoformat(),
        "factory_name": data.factory_name if data.show_factory_name_on_pdf else "",
        "show_factory": bool(data.show_factory_name_on_pdf and data.factory_name),
    }


def customer_quote_lead_rows(data: QuoteInput) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    n = 3
    if data.sample_lead_time_days is not None:
        rows.append((f"{n}.) Sample Lead-Time:", f"{data.sample_lead_time_days} Days"))
        n += 1
    rows.append((f"{n}.) Production Lead-Time:", f"{data.production_lead_time_days} Days"))
    n += 1
    rows.append((f"{n}.) Validity:", f"{data.validity_days} Days"))
    n += 1
    rows.append((f"{n}.) Exchange Rate:", f"1 USD = {data.exchange_rate_vnd:,.0f} VND"))
    if data.other_notes:
        rows.append(("Other:", data.other_notes))
    for label, val in data.custom_fields.items():
        rows.append((f"{label}:", val))
    return rows


def customer_quote_footer_texts(data: QuoteInput) -> list[str]:
    return [
        "The production order is needed for the factory to proceed with sampling preparation.",
        (
            "Our quotation does not include import tariffs for imported thread gauges. If the final tariffs "
            "are paid by Toption (Asia), we will issue the corresponding invoice for payment."
        ),
        effective_payment_terms(data),
        "Sample charge will apply.",
    ]


def autofit_column_units(headers: list[str], rows: list[list[str]], total_units: float = 80.0) -> list[float]:
    """Proportional column widths for Excel (character-based, scaled to total_units)."""
    n = len(headers)
    if n == 0:
        return []
    raw = []
    for i in range(n):
        max_len = len(headers[i])
        for row in rows:
            if i < len(row):
                max_len = max(max_len, len(str(row[i])))
        raw.append(max(10.0, min(max_len * 1.2 + 3, 38.0)))
    total_raw = sum(raw)
    if total_raw <= 0:
        return [total_units / n] * n
    scale = total_units / total_raw
    return [w * scale for w in raw]
