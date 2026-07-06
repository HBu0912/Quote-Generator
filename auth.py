"""Simple session-based password gate for the quote app."""

from __future__ import annotations

import os
import secrets

from flask import redirect, request, session, url_for

APP_PASSWORD = os.environ.get("APP_PASSWORD", "TopVN26")


def is_authenticated() -> bool:
    return bool(session.get("authenticated"))


def check_password(password: str) -> bool:
    return secrets.compare_digest(password, APP_PASSWORD)


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
