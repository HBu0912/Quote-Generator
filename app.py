"""Flask application for Toption quote generation."""

from __future__ import annotations

import io
import os
from datetime import timedelta

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for

from auth import (
    auth_redirect,
    check_password,
    is_authenticated,
    is_public_request,
    login_user,
    logout_user,
)
from calculator import calculate_quote, primary_line_items, quote_from_dict
from excel_external_generator import generate_excel_customer
from excel_generator import generate_excel
from pdf_generator import generate_pdf
from storage import delete_quote, get_quote, init_db, save_quote, search_quotes

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-in-production")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
init_db()


@app.before_request
def require_login():
    if is_public_request() or is_authenticated():
        return None
    return auth_redirect()


@app.route("/health")
def health():
    return jsonify({"ok": True})


@app.route("/login", methods=["GET", "POST"])
def login():
    if is_authenticated():
        return redirect(request.args.get("next") or url_for("home"))

    error = None
    next_url = request.args.get("next") or request.form.get("next") or url_for("home")

    if request.method == "POST":
        password = request.form.get("password", "")
        if check_password(password):
            login_user()
            if not next_url.startswith("/"):
                next_url = url_for("home")
            return redirect(next_url)
        error = "Incorrect password. Please try again."

    return render_template("login.html", error=error, next_url=next_url)


@app.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/quote")
@app.route("/quote/<quote_id>")
def quote_form(quote_id: str | None = None):
    return render_template("quote.html", quote_id=quote_id or "")


@app.route("/api/quotes/search")
def api_search():
    q = request.args.get("q", "")
    limit = min(int(request.args.get("limit", 50)), 100)
    return jsonify(search_quotes(q, limit))


@app.route("/api/quotes/<quote_id>", methods=["DELETE"])
def api_delete_quote(quote_id: str):
    if delete_quote(quote_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Quote not found"}), 404


@app.route("/api/quotes/<quote_id>")
def api_get_quote(quote_id: str):
    record = get_quote(quote_id)
    if not record:
        return jsonify({"error": "Quote not found"}), 404
    return jsonify(record)


@app.route("/api/quotes/save", methods=["POST"])
def api_save():
    body = request.get_json(force=True)
    payload = body.get("payload") or body
    quote_id = body.get("quote_id") or payload.get("quote_id")
    saved_id = save_quote(payload, quote_id)
    return jsonify({"quote_id": saved_id, "ok": True})


@app.route("/api/preview", methods=["POST"])
def preview():
    body = request.get_json(force=True)
    quote_id = body.pop("quote_id", None)
    quote = calculate_quote(quote_from_dict(body))
    saved_id = save_quote(body, quote_id)
    result = _quote_to_json(quote)
    result["quote_id"] = saved_id
    return jsonify(result)


@app.route("/api/generate/<fmt>", methods=["POST"])
def generate(fmt: str):
    try:
        body = request.get_json(force=True)
        quote_id = body.pop("quote_id", None)
        saved_id = save_quote(body, quote_id)
        quote = calculate_quote(quote_from_dict(body))
        inquiry = quote.input.inquiry_no or "quote"
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in inquiry)

        if fmt == "excel":
            data = generate_excel(quote)
            resp = send_file(
                io.BytesIO(data),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=f"{safe_name}_quotation_internal.xlsx",
            )
        elif fmt in ("excel-external", "excel-customer"):
            data = generate_excel_customer(quote)
            resp = send_file(
                io.BytesIO(data),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=f"{safe_name}_quotation.xlsx",
            )
        elif fmt == "pdf":
            data = generate_pdf(quote)
            resp = send_file(
                io.BytesIO(data),
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"{safe_name}_quotation.pdf",
            )
        else:
            return jsonify({"error": "Invalid format. Use excel, excel-customer, or pdf."}), 400
        resp.headers["X-Quote-Id"] = saved_id
        return resp
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


def _quote_to_json(quote) -> dict:
    has_multiple_qty = len(quote.line_items) > quote.num_parts
    primary = primary_line_items(quote.line_items)
    return {
        "num_parts": quote.num_parts,
        "has_multiple_qty_options": has_multiple_qty,
        "total_factory_order_usd": round(quote.total_factory_order_usd, 4),
        "total_revenue_usd": round(quote.total_revenue_usd, 4),
        "total_export_fee_allocated": round(quote.total_export_fee_allocated, 4),
        "unit_price_profit_after_export": round(quote.unit_price_profit_after_export, 4),
        "total_mold_fee_profit": round(quote.total_mold_fee_profit, 4),
        "total_sample_profit": round(quote.total_sample_profit, 2),
        "total_sample_revenue_usd": round(quote.total_sample_revenue_usd, 2),
        "sample_markup_pct": round(_pct_display(quote.input.sample_markup_pct), 2),
        "total_net_profit": round(quote.total_net_profit, 4),
        "line_items": [
            {
                "item_no": li.item_no,
                "part_number": li.part_number,
                "qty": li.qty,
                "factory_unit_price_usd": round(li.factory_unit_price_usd, 4),
                "export_fee_per_unit": round(li.export_fee_per_unit, 4),
                "unit_pricing_fob_usd": round(li.unit_pricing_fob_usd, 4),
                "tooling_fee_usd": round(li.tooling_fee_usd, 2),
                "unit_price_profit": round(li.unit_price_profit, 2),
                "mold_fee_profit": round(li.mold_fee_profit, 2),
                "line_net_profit": round(li.line_net_profit, 2),
                "line_net_after_export": round(
                    li.line_net_profit - li.export_fee_per_unit * li.qty, 2
                ),
                "sample_quoted_total_usd": round(li.sample_quoted_total_usd, 2),
                "sample_profit": round(li.sample_profit, 2),
            }
            for li in quote.line_items
        ],
        "primary_line_items": [
            {
                "item_no": li.item_no,
                "part_number": li.part_number,
                "qty": li.qty,
                "line_net_after_export": round(
                    li.line_net_profit - li.export_fee_per_unit * li.qty, 2
                ),
            }
            for li in primary
        ],
    }


def _pct_display(value: float) -> float:
    return value * 100 if value <= 1 else value


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print(f"Quote Generator running at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
