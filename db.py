"""Database connection — SQLite locally, Turso on Vercel."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DB_PATH = Path(os.environ.get("QUOTE_DB_PATH", Path(__file__).resolve().parent / "data" / "quotes.db"))


def _on_vercel() -> bool:
    return bool(os.environ.get("VERCEL"))


def _use_turso() -> bool:
    return bool(os.environ.get("TURSO_DATABASE_URL"))


def _require_turso_on_vercel() -> None:
    if _on_vercel() and not _use_turso():
        raise RuntimeError(
            "Database not configured for Vercel. Add TURSO_DATABASE_URL and "
            "TURSO_AUTH_TOKEN in Vercel → Project → Settings → Environment Variables."
        )


def _row_to_mapping(row: Any, columns: list[str] | None = None) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    if hasattr(row, "_asdict"):
        return row._asdict()
    if hasattr(row, "keys"):
        return dict(row)
    if columns:
        return {columns[i]: row[i] for i in range(len(columns))}
    return dict(row)


@contextmanager
def db_connection() -> Iterator[Any]:
    _require_turso_on_vercel()

    if _use_turso():
        import libsql_client

        client = libsql_client.create_client_sync(
            url=os.environ["TURSO_DATABASE_URL"],
            auth_token=os.environ.get("TURSO_AUTH_TOKEN", ""),
        )
        try:
            yield _LibsqlClientAdapter(client)
        finally:
            client.close()
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


class _LibsqlClientAdapter:
    """sqlite3-like wrapper for Turso via libsql-client (HTTP, serverless-safe)."""

    def __init__(self, client):
        self._client = client

    def executescript(self, script: str) -> None:
        for statement in script.split(";"):
            sql = statement.strip()
            if sql:
                self._client.execute(sql)

    def execute(self, sql: str, params: tuple = ()):
        result = self._client.execute(sql, list(params) if params else None)
        return _LibsqlCursor(result)

    def commit(self) -> None:
        return None


class _LibsqlCursor:
    def __init__(self, result):
        self._result = result
        self.rowcount = getattr(result, "rows_affected", -1)

    def fetchone(self):
        if not self._result.rows:
            return None
        row = self._result.rows[0]
        cols = list(self._result.columns) if self._result.columns else []
        if isinstance(row, dict):
            return row
        return _row_to_mapping(row, cols)

    def fetchall(self):
        cols = list(self._result.columns) if self._result.columns else []
        rows = []
        for row in self._result.rows:
            if isinstance(row, dict):
                rows.append(row)
            else:
                rows.append(_row_to_mapping(row, cols))
        return rows
