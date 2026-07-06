"""SQLite / Turso persistence for saved quotes."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from db import db_connection


def init_db() -> None:
    with db_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                id TEXT PRIMARY KEY,
                inquiry_no TEXT NOT NULL DEFAULT '',
                factory_name TEXT NOT NULL DEFAULT '',
                quotation_date TEXT,
                part_count INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL,
                search_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_quotes_inquiry ON quotes(inquiry_no);
            CREATE INDEX IF NOT EXISTS idx_quotes_factory ON quotes(factory_name);
            CREATE INDEX IF NOT EXISTS idx_quotes_updated ON quotes(updated_at DESC);
            """
        )


def _build_search_text(payload: dict[str, Any]) -> str:
    parts = [
        payload.get("inquiry_no", ""),
        payload.get("factory_name", ""),
        payload.get("other_notes", ""),
        payload.get("quotation_date", ""),
    ]
    for key, val in (payload.get("custom_fields") or {}).items():
        parts.extend([key, val])
    for item in payload.get("line_items") or []:
        parts.extend([
            item.get("part_number", ""),
            item.get("cast_dwg", ""),
            item.get("mach_dwg", ""),
            item.get("description", ""),
            item.get("material", ""),
            item.get("other_finish", ""),
            item.get("pressure_testing", ""),
            str(item.get("sample_factory_cost_vnd", item.get("sample_factory_unit_price_vnd", ""))),
        ])
    return " ".join(str(p).lower() for p in parts if p)


def _row_get(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row[key]
    return row[key]


def save_quote(payload: dict[str, Any], quote_id: str | None = None) -> str:
    """Save or update a quote. Returns the quote id."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    search_text = _build_search_text(payload)
    inquiry_no = payload.get("inquiry_no") or ""
    factory_name = payload.get("factory_name") or ""
    quotation_date = payload.get("quotation_date") or ""
    part_count = len(payload.get("line_items") or [])
    payload_json = json.dumps(payload)

    with db_connection() as conn:
        if quote_id:
            existing = conn.execute("SELECT id FROM quotes WHERE id = ?", (quote_id,)).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE quotes SET
                        inquiry_no = ?, factory_name = ?, quotation_date = ?,
                        part_count = ?, payload_json = ?, search_text = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (inquiry_no, factory_name, quotation_date, part_count, payload_json, search_text, now, quote_id),
                )
                conn.commit()
                return quote_id

        new_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO quotes (id, inquiry_no, factory_name, quotation_date, part_count,
                                  payload_json, search_text, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id, inquiry_no, factory_name, quotation_date, part_count, payload_json, search_text, now, now),
        )
        conn.commit()
        return new_id


def get_quote(quote_id: str) -> dict[str, Any] | None:
    init_db()
    with db_connection() as conn:
        row = conn.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
        if not row:
            return None
        return _row_to_dict(row)


def delete_quote(quote_id: str) -> bool:
    """Delete a quote by id. Returns True if a row was removed."""
    init_db()
    with db_connection() as conn:
        cur = conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
        conn.commit()
        return cur.rowcount > 0


def search_quotes(query: str = "", limit: int = 50) -> list[dict[str, Any]]:
    init_db()
    with db_connection() as conn:
        if query.strip():
            terms = query.strip().lower().split()
            clauses = " AND ".join(["search_text LIKE ?"] * len(terms))
            params = [f"%{t}%" for t in terms]
            rows = conn.execute(
                f"""
                SELECT * FROM quotes
                WHERE {clauses}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM quotes ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_summary(r) for r in rows]


def list_recent(limit: int = 20) -> list[dict[str, Any]]:
    return search_quotes("", limit)


def _row_to_summary(row: Any) -> dict[str, Any]:
    payload = json.loads(_row_get(row, "payload_json"))
    part_numbers = [li.get("part_number", "") for li in payload.get("line_items", []) if li.get("part_number")]
    return {
        "id": _row_get(row, "id"),
        "inquiry_no": _row_get(row, "inquiry_no"),
        "factory_name": _row_get(row, "factory_name"),
        "quotation_date": _row_get(row, "quotation_date"),
        "part_count": _row_get(row, "part_count"),
        "part_numbers": part_numbers[:5],
        "created_at": _row_get(row, "created_at"),
        "updated_at": _row_get(row, "updated_at"),
    }


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": _row_get(row, "id"),
        "inquiry_no": _row_get(row, "inquiry_no"),
        "factory_name": _row_get(row, "factory_name"),
        "quotation_date": _row_get(row, "quotation_date"),
        "part_count": _row_get(row, "part_count"),
        "payload": json.loads(_row_get(row, "payload_json")),
        "created_at": _row_get(row, "created_at"),
        "updated_at": _row_get(row, "updated_at"),
    }
