"""Quote calculation engine — mirrors the Excel quotation formulas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class LineItemInput:
    part_number: str = ""
    cast_dwg: str = ""
    mach_dwg: str = ""
    description: str = ""
    material: str = ""
    qty: int = 0
    qty_options: list[int] = field(default_factory=list)
    factory_unit_price_vnd: float = 0
    factory_unit_price_vnd_options: list[float] = field(default_factory=list)
    factory_weight_kg: float = 0
    other_finish: str = ""
    pressure_testing: str = ""
    factory_mold_fee_vnd: float = 0
    unit_price_markup_pct: float | None = None
    mold_fee_markup_pct: float | None = None
    sample_factory_cost_vnd: float = 0


@dataclass
class QuoteInput:
    inquiry_no: str = ""
    quotation_date: date | None = None
    factory_name: str = ""
    exchange_rate_vnd: float = 26130
    export_inspection_fee_usd: float = 500
    unit_price_markup_pct: float = 0.25
    mold_fee_markup_pct: float = 0.08
    sample_markup_pct: float = 25
    sample_lead_time_days: int | None = None
    production_lead_time_days: int = 65
    validity_days: int = 10
    other_notes: str = ""
    artmark: bool = False
    payment_terms: str = (
        "Price is FOB included.\nPayment: 30 days from the invoice date for Air Shipments, "
        "60 days from the invoice date for Sea Shipments."
    )
    custom_fields: dict[str, str] = field(default_factory=dict)
    gage_list: list[dict[str, str]] = field(default_factory=list)
    line_items: list[LineItemInput] = field(default_factory=list)
    line_item_column_labels: dict[str, str] = field(default_factory=dict)
    show_factory_name_on_pdf: bool = False


ARTMARK_PAYMENT_TEXT = (
    "Payment: 30 days from the invoice date for Air Shipments, "
    "60 days from the invoice date for Sea Shipments."
)


def effective_payment_terms(data: QuoteInput) -> str:
    """Return payment terms for PDF — Artmark quotes omit the standard payment-days line."""
    text = (data.payment_terms or "").strip()
    if not data.artmark:
        return text
    cleaned = text.replace(ARTMARK_PAYMENT_TEXT, "").replace("\n\n", "\n").strip()
    return cleaned


def effective_gage_list(gage_list: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """Return gage entries that have a gage value."""
    entries = []
    for row in gage_list or []:
        gage = str(row.get("gage", "")).strip()
        if not gage:
            continue
        entries.append({
            "part_number": str(row.get("part_number", "")).strip(),
            "gage": gage,
        })
    return entries


DEFAULT_LINE_ITEM_COLUMN_LABELS: dict[str, str] = {
    "item_no": "Item",
    "part_number": "P/N",
    "cast_dwg": "Cast DWG#",
    "mach_dwg": "Mach DWG#",
    "description": "Description",
    "material": "Material",
    "qty": "Quantity",
    "factory_unit_price_vnd": "Unit Price FOB",
    "factory_weight_kg": "Weight (kg)",
    "factory_mold_fee_vnd": "Mold Fee",
    "other_finish": "Other/Finish",
    "pressure_testing": "Pressure Testing",
    "sample_factory_cost_vnd": "Sample Fee",
    "unit_price_markup_pct": "Unit Markup %",
    "mold_fee_markup_pct": "Mold Markup %",
    "factory_unit_price_usd": "Factory Unit (USD)",
    "factory_mold_fee_usd": "Factory Mold (USD)",
    "export_fee_per_unit": "Export Fee / Unit",
    "unit_pricing_fob_usd": "Unit Price FOB",
    "tooling_fee_usd": "Mold Fee",
    "unit_price_profit": "Unit Price Profit",
    "mold_fee_profit": "Mold Fee Profit",
    "line_net_profit": "Line Net Profit",
    "sample_quoted_total_usd": "Sample Fee",
}


def sample_field_visible(line_items) -> bool:
    """True if any line item has a sample factory cost entered."""
    return any(getattr(li, "sample_factory_cost_vnd", 0) > 0 for li in line_items)


def column_label(labels: dict[str, str], field: str) -> str:
    """Return custom column label or the default for a line-item field."""
    custom = (labels or {}).get(field, "").strip()
    if custom:
        return custom
    return DEFAULT_LINE_ITEM_COLUMN_LABELS.get(field, field.replace("_", " ").title())


# PDF customer columns may use a dedicated label key or fall back to the related line-item header name.
PDF_COLUMN_LABEL_SOURCES: dict[str, tuple[str, ...]] = {
    "item_no": ("item_no",),
    "part_number": ("part_number",),
    "cast_dwg": ("cast_dwg",),
    "mach_dwg": ("mach_dwg",),
    "description": ("description",),
    "material": ("material",),
    "qty": ("qty",),
    "unit_pricing_fob_usd": ("unit_pricing_fob_usd", "factory_unit_price_vnd"),
    "factory_weight_kg": ("factory_weight_kg",),
    "other_finish": ("other_finish",),
    "pressure_testing": ("pressure_testing",),
    "sample_quoted_total_usd": ("sample_quoted_total_usd", "sample_factory_cost_vnd"),
    "tooling_fee_usd": ("tooling_fee_usd", "factory_mold_fee_vnd"),
}


def pdf_column_label(labels: dict[str, str], field: str) -> str:
    """Resolve a customer PDF column title from saved line-item header names."""
    for key in PDF_COLUMN_LABEL_SOURCES.get(field, (field,)):
        custom = (labels or {}).get(key, "").strip()
        if custom:
            return custom
    return DEFAULT_LINE_ITEM_COLUMN_LABELS.get(field, field.replace("_", " ").title())


@dataclass
class LineItemCalculated:
    item_no: int
    part_number: str
    cast_dwg: str
    mach_dwg: str
    description: str
    material: str
    qty: int
    factory_weight_kg: float
    other_finish: str
    pressure_testing: str
    factory_unit_price_vnd: float
    factory_unit_price_usd: float
    factory_mold_fee_vnd: float
    factory_mold_fee_usd: float
    export_fee_per_unit: float
    unit_price_markup_pct: float
    mold_fee_markup_pct: float
    unit_pricing_fob_usd: float
    tooling_fee_usd: float
    unit_price_profit: float
    mold_fee_profit: float
    line_net_profit: float
    sample_factory_cost_vnd: float = 0
    sample_factory_cost_usd: float = 0
    sample_quoted_total_usd: float = 0
    sample_profit: float = 0


@dataclass
class QuoteCalculated:
    input: QuoteInput
    line_items: list[LineItemCalculated]
    num_parts: int
    total_factory_order_usd: float
    total_factory_order_vnd: float
    total_export_fee_allocated: float
    total_unit_price_profit: float
    unit_price_profit_after_export: float
    total_mold_fee_profit: float
    total_sample_profit: float
    total_sample_revenue_usd: float
    total_net_profit: float
    total_revenue_usd: float


def _pct(value: float) -> float:
    """Accept markup as 25 or 0.25."""
    return value / 100 if value > 1 else value


def effective_qty_options(item: LineItemInput) -> list[int]:
    """Return quantity options in entry order."""
    if item.qty_options:
        return [q for q in item.qty_options if q > 0]
    if item.qty > 0:
        return [item.qty]
    return []


def effective_factory_prices(item: LineItemInput) -> list[float]:
    """Return factory unit prices in entry order."""
    if item.factory_unit_price_vnd_options:
        return [p for p in item.factory_unit_price_vnd_options if p >= 0]
    if item.factory_unit_price_vnd > 0:
        return [item.factory_unit_price_vnd]
    return []


def iter_qty_price_scenarios(item: LineItemInput) -> list[tuple[int, float]]:
    """Pair each quantity option with its factory price (by position)."""
    qtys = effective_qty_options(item)
    prices = effective_factory_prices(item)
    if not qtys:
        return []
    if not prices:
        return [(q, 0.0) for q in qtys]
    if len(prices) == 1:
        return [(q, prices[0]) for q in qtys]
    paired: list[tuple[int, float]] = []
    for i, qty in enumerate(qtys):
        price = prices[i] if i < len(prices) else prices[-1]
        paired.append((qty, price))
    return paired


def primary_line_items(line_items: list[LineItemCalculated]) -> list[LineItemCalculated]:
    """One row per part (first quantity option) for aggregate totals."""
    seen: dict[int, LineItemCalculated] = {}
    for li in line_items:
        if li.item_no not in seen:
            seen[li.item_no] = li
    return [seen[k] for k in sorted(seen)]


def _sample_calc(item: LineItemInput, sample_markup: float, rate: float) -> dict[str, float]:
    if item.sample_factory_cost_vnd <= 0:
        return {
            "sample_factory_cost_vnd": 0,
            "sample_factory_cost_usd": 0,
            "sample_quoted_total_usd": 0,
            "sample_profit": 0,
        }
    factory_usd = item.sample_factory_cost_vnd / rate
    quoted_total = factory_usd * (1 + sample_markup)
    return {
        "sample_factory_cost_vnd": item.sample_factory_cost_vnd,
        "sample_factory_cost_usd": factory_usd,
        "sample_quoted_total_usd": quoted_total,
        "sample_profit": quoted_total - factory_usd,
    }


def calculate_quote(data: QuoteInput) -> QuoteCalculated:
    items = [li for li in data.line_items if effective_qty_options(li)]
    num_parts = len(items)
    rate = data.exchange_rate_vnd
    export_fee = data.export_inspection_fee_usd
    default_unit_markup = _pct(data.unit_price_markup_pct)
    default_mold_markup = _pct(data.mold_fee_markup_pct)
    sample_markup = _pct(data.sample_markup_pct)

    calculated: list[LineItemCalculated] = []

    for idx, item in enumerate(items, start=1):
        unit_markup = _pct(item.unit_price_markup_pct) if item.unit_price_markup_pct is not None else default_unit_markup
        mold_markup = _pct(item.mold_fee_markup_pct) if item.mold_fee_markup_pct is not None else default_mold_markup
        sample_fields = _sample_calc(item, sample_markup, rate)

        mold_usd = item.factory_mold_fee_vnd / rate
        export_alloc_per_part = export_fee / num_parts if num_parts else 0
        tooling = mold_usd * (1 + mold_markup)
        mold_profit = tooling - mold_usd

        for qty, price_vnd in iter_qty_price_scenarios(item):
            factory_usd = price_vnd / rate
            export_per_unit = export_alloc_per_part / qty
            unit_fob = factory_usd * (1 + unit_markup) + export_per_unit
            unit_profit = (unit_fob - factory_usd) * qty
            net_profit = unit_profit + mold_profit

            calculated.append(
                LineItemCalculated(
                    item_no=idx,
                    part_number=item.part_number,
                    cast_dwg=item.cast_dwg,
                    mach_dwg=item.mach_dwg,
                    description=item.description,
                    material=item.material,
                    qty=qty,
                    factory_weight_kg=item.factory_weight_kg,
                    other_finish=item.other_finish,
                    pressure_testing=item.pressure_testing,
                    factory_unit_price_vnd=price_vnd,
                    factory_unit_price_usd=factory_usd,
                    factory_mold_fee_vnd=item.factory_mold_fee_vnd,
                    factory_mold_fee_usd=mold_usd,
                    export_fee_per_unit=export_per_unit,
                    unit_price_markup_pct=unit_markup,
                    mold_fee_markup_pct=mold_markup,
                    unit_pricing_fob_usd=unit_fob,
                    tooling_fee_usd=tooling,
                    unit_price_profit=unit_profit,
                    mold_fee_profit=mold_profit,
                    line_net_profit=net_profit,
                    **sample_fields,
                )
            )

    primary = primary_line_items(calculated)
    total_factory_usd = sum(li.factory_unit_price_usd * li.qty for li in primary)
    total_factory_vnd = total_factory_usd * rate
    total_export_allocated = export_fee if num_parts else 0
    total_unit_profit = sum(li.unit_price_profit for li in primary)
    unit_profit_after_export = total_unit_profit - total_export_allocated
    total_mold_profit = sum(li.mold_fee_profit for li in primary)
    production_net = sum(li.line_net_profit for li in primary) - total_export_allocated
    total_sample_profit = sum(li.sample_profit for li in primary)
    total_sample_revenue = sum(li.sample_quoted_total_usd for li in primary)
    total_net = production_net
    total_revenue = sum(li.unit_pricing_fob_usd * li.qty for li in primary)

    return QuoteCalculated(
        input=data,
        line_items=calculated,
        num_parts=num_parts,
        total_factory_order_usd=total_factory_usd,
        total_factory_order_vnd=total_factory_vnd,
        total_export_fee_allocated=total_export_allocated,
        total_unit_price_profit=total_unit_profit,
        unit_price_profit_after_export=unit_profit_after_export,
        total_mold_fee_profit=total_mold_profit,
        total_sample_profit=total_sample_profit,
        total_sample_revenue_usd=total_sample_revenue,
        total_net_profit=total_net,
        total_revenue_usd=total_revenue,
    )


def field_has_display_value(value: Any) -> bool:
    """True if a line-item field should appear on generated outputs."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip()
    return bool(text) and text not in ("", "/", "—", "-")


def line_field_visible(line_items, field: str) -> bool:
    return any(field_has_display_value(getattr(li, field, None)) for li in line_items)


def has_cast_dwg_data(line_items) -> bool:
    """True if any line item has a meaningful cast drawing number."""
    return line_field_visible(line_items, "cast_dwg")


def _float(value: Any, default: float = 0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _parse_qty_options(row: dict[str, Any]) -> list[int]:
    raw = row.get("qty_options")
    if raw is not None and raw != "":
        if isinstance(raw, str):
            parts = raw.replace(";", ",").split(",")
            return [q for q in (_int(p.strip()) for p in parts) if q > 0]
        if isinstance(raw, list):
            return [q for q in (_int(x) for x in raw) if q > 0]
    qty = _int(row.get("qty"))
    return [qty] if qty > 0 else []


def _parse_float_list(value: Any) -> list[float]:
    if value is None or value == "":
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, str):
        parts = value.replace(";", ",").split(",")
        return [_float(p.strip()) for p in parts if p.strip()]
    if isinstance(value, list):
        return [_float(x) for x in value if x is not None and str(x).strip() != ""]
    return []


def _parse_factory_unit_prices(row: dict[str, Any]) -> list[float]:
    raw_opts = row.get("factory_unit_price_vnd_options")
    if raw_opts is not None and raw_opts != "":
        prices = _parse_float_list(raw_opts)
        if prices:
            return prices
    return _parse_float_list(row.get("factory_unit_price_vnd"))


def has_sample_data(line_items) -> bool:
    return sample_field_visible(line_items)


def _parse_sample_factory_cost(row: dict[str, Any]) -> float:
    """Parse lump-sum sample factory cost; migrate legacy qty × unit price fields."""
    cost = _float(row.get("sample_factory_cost_vnd"))
    if cost > 0:
        return cost
    unit = _float(row.get("sample_factory_unit_price_vnd"))
    if unit <= 0:
        return 0
    qty = _int(row.get("sample_qty"))
    return unit * qty if qty > 0 else unit


def _merge_legacy_samples(line_items: list[LineItemInput], legacy_samples: list[dict[str, Any]]) -> None:
    """Attach old standalone sample_line_items to matching production rows by P/N."""
    by_pn = {
        row.get("part_number", ""): row
        for row in legacy_samples
        if row.get("part_number")
    }
    for li in line_items:
        if li.sample_factory_cost_vnd > 0:
            continue
        legacy = by_pn.get(li.part_number)
        if not legacy:
            continue
        cost = _parse_sample_factory_cost(legacy)
        if cost > 0:
            li.sample_factory_cost_vnd = cost


def quote_from_dict(payload: dict[str, Any]) -> QuoteInput:
    """Parse JSON/form payload into QuoteInput."""
    qdate = payload.get("quotation_date")
    parsed_date = date.fromisoformat(qdate) if qdate else None

    line_items = []
    for row in payload.get("line_items", []):
        qty_options = _parse_qty_options(row)
        price_options = _parse_factory_unit_prices(row)
        line_items.append(
            LineItemInput(
                part_number=row.get("part_number", ""),
                cast_dwg=row.get("cast_dwg", ""),
                mach_dwg=row.get("mach_dwg", ""),
                description=row.get("description", ""),
                material=row.get("material", ""),
                qty=qty_options[0] if qty_options else _int(row.get("qty")),
                qty_options=qty_options,
                factory_unit_price_vnd=price_options[0] if price_options else _float(row.get("factory_unit_price_vnd")),
                factory_unit_price_vnd_options=price_options,
                factory_weight_kg=_float(row.get("factory_weight_kg")),
                other_finish=row.get("other_finish", ""),
                pressure_testing=row.get("pressure_testing", ""),
                factory_mold_fee_vnd=_float(row.get("factory_mold_fee_vnd")),
                unit_price_markup_pct=_optional_float(row.get("unit_price_markup_pct")),
                mold_fee_markup_pct=_optional_float(row.get("mold_fee_markup_pct")),
                sample_factory_cost_vnd=_parse_sample_factory_cost(row),
            )
        )

    _merge_legacy_samples(line_items, payload.get("sample_line_items") or [])

    custom = {k: v for k, v in payload.get("custom_fields", {}).items() if k and v}
    col_labels = {
        k: str(v).strip()
        for k, v in payload.get("line_item_column_labels", {}).items()
        if k and str(v).strip()
    }

    return QuoteInput(
        inquiry_no=payload.get("inquiry_no", ""),
        quotation_date=parsed_date,
        factory_name=payload.get("factory_name", ""),
        exchange_rate_vnd=_float(payload.get("exchange_rate_vnd"), 26130),
        export_inspection_fee_usd=_float(payload.get("export_inspection_fee_usd"), 500),
        unit_price_markup_pct=_float(payload.get("unit_price_markup_pct"), 25),
        mold_fee_markup_pct=_float(payload.get("mold_fee_markup_pct"), 8),
        sample_markup_pct=_float(payload.get("sample_markup_pct"), 25),
        sample_lead_time_days=_optional_int(payload.get("sample_lead_time_days")),
        production_lead_time_days=_int(payload.get("production_lead_time_days"), 65),
        validity_days=_int(payload.get("validity_days"), 10),
        other_notes=payload.get("other_notes", ""),
        artmark=bool(payload.get("artmark")),
        payment_terms=payload.get("payment_terms", QuoteInput.payment_terms),
        custom_fields=custom,
        gage_list=[
            {
                "part_number": str(row.get("part_number", "")).strip(),
                "gage": str(row.get("gage", "")).strip(),
            }
            for row in (payload.get("gage_list") or [])
            if str(row.get("gage", "")).strip() or str(row.get("part_number", "")).strip()
        ],
        line_items=line_items,
        line_item_column_labels=col_labels,
        show_factory_name_on_pdf=bool(payload.get("show_factory_name_on_pdf")),
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
