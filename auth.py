"""Simple session-based password gate for the quote app."""

from __future__ import annotations

import hmac
import os
import hashlib

from flask import redirect, request, session, url_for


def _expected_password() -> str:
    return (os.environ.get("APP_PASSWORD") or "").strip() or "TopVN26"


def is_authenticated() -> bool:
    return bool(session.get("authenticated"))


def check_password(password: str) -> bool:
    """Constant-time password check that tolerates unequal lengths."""
    given = password if isinstance(password, str) else ""
    expected = _expected_password()
    return hmac.compare_digest(
        hashlib.sha256(given.encode("utf-8")).digest(),
        hashlib.sha256(expected.encode("utf-8")).digest(),
    )


def login_user() -> None:
    session["authenticated"] = True
    session.permanent = True


def logout_user() -> None:
    session.pop("authenticated", None)


def is_public_request() -> bool:
    if request.endpoint in ("login", "health"):
        return True
    if request.endpoint == "static":
        return True
    if request.path.startswith("/static/"):
        return True
    return False


def auth_redirect():
    if request.path.startswith("/api/"):
        from flask import jsonify

        return jsonify({"error": "Authentication required"}), 401
    next_url = request.full_path if request.query_string else request.path
    if next_url.endswith("?"):
        next_url = next_url[:-1]
    return redirect(url_for("login", next=next_url))
