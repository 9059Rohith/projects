"""
Lightweight Flask web UI for the Binance Futures Testnet Trading Bot.

Serves a single-page dashboard and exposes JSON API endpoints that
delegate to :class:`~bot.client.BinanceFuturesClient` and
:class:`~bot.orders.OrderManager`.

Run with::

    python app.py

Then open: http://localhost:5000
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, render_template, request

from bot.client import BinanceFuturesClient
from bot.logging_config import get_logger
from bot.orders import OrderManager
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
    validate_time_in_force,
)

import click
import requests as req_lib

app = Flask(__name__)
logger = get_logger("WebUI")


# ---------------------------------------------------------------------------
# Client factory — fail fast at startup if credentials are missing
# ---------------------------------------------------------------------------

def _get_client() -> BinanceFuturesClient:
    """
    Create a new client instance per request (thread-safe).

    Returns:
        Authenticated :class:`BinanceFuturesClient`.

    Raises:
        EnvironmentError: Propagated if credentials are not configured.
    """
    return BinanceFuturesClient()


def _error(message: str, status: int = 400) -> tuple[Any, int]:
    """
    Return a standard JSON error response.

    Args:
        message: Human-readable error description.
        status:  HTTP status code (default 400).

    Returns:
        A tuple of (JSON response, status code).
    """
    logger.warning("API error %s: %s", status, message)
    return jsonify({"success": False, "error": message}), status


# ---------------------------------------------------------------------------
# Routes — UI
# ---------------------------------------------------------------------------

@app.route("/")
def index() -> str:
    """
    Serve the main single-page dashboard.

    Returns:
        Rendered ``index.html`` template.
    """
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Routes — REST API
# ---------------------------------------------------------------------------

@app.route("/api/balance", methods=["GET"])
def api_balance() -> tuple[Any, int]:
    """
    GET /api/balance

    Returns account balances for all non-zero assets.

    Returns:
        JSON with ``success`` flag and ``balances`` list.
    """
    try:
        client = _get_client()
        balances = client.get_account_balance()
        return jsonify({"success": True, "balances": balances}), 200
    except EnvironmentError as exc:
        return _error(str(exc), 503)
    except req_lib.HTTPError as exc:
        return _error(str(exc), 502)
    except Exception as exc:  # noqa: BLE001
        return _error(f"Unexpected error: {exc}", 500)


@app.route("/api/order", methods=["POST"])
def api_place_order() -> tuple[Any, int]:
    """
    POST /api/order

    Place a new order. Expects a JSON body with fields:
        symbol, side, type, quantity, price (opt), tif (opt), stop_price (opt).

    Returns:
        JSON with ``success`` flag and ``order`` dict on success.
    """
    data = request.get_json(force=True, silent=True) or {}

    raw_symbol = data.get("symbol", "")
    raw_side = data.get("side", "")
    raw_type = data.get("type", "")
    raw_qty = data.get("quantity", "")
    raw_price = data.get("price") or None
    raw_tif = data.get("tif", "GTC")
    raw_stop = data.get("stop_price") or None

    # Validate
    try:
        symbol = validate_symbol(str(raw_symbol))
        side = validate_side(str(raw_side))
        order_type = validate_order_type(str(raw_type))
        qty = validate_quantity(str(raw_qty))
        # For STOP_LIMIT treat price validation as LIMIT
        price_type = "LIMIT" if order_type == "STOP_LIMIT" else order_type
        parsed_price = validate_price(
            str(raw_price) if raw_price is not None else None, price_type
        )
        tif = validate_time_in_force(str(raw_tif))

        parsed_stop: float | None = None
        if order_type in {"STOP_MARKET", "STOP_LIMIT"}:
            if raw_stop is None:
                return _error(f"stop_price is required for {order_type} orders.")
            parsed_stop = float(raw_stop)
            if parsed_stop <= 0:
                return _error("stop_price must be a positive number.")

    except click.BadParameter as exc:
        return _error(str(exc))
    except ValueError as exc:
        return _error(str(exc))

    # Place order
    try:
        client = _get_client()
        manager = OrderManager(client)
        result = manager.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=qty,
            price=parsed_price,
            time_in_force=tif,
            stop_price=parsed_stop,
        )
        # Add human-readable time
        update_ms = result.get("updateTime", 0)
        try:
            dt = datetime.fromtimestamp(update_ms / 1000, tz=timezone.utc)
            result["updateTimeHuman"] = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:  # noqa: BLE001
            result["updateTimeHuman"] = str(update_ms)

        return jsonify({"success": True, "order": result}), 200

    except EnvironmentError as exc:
        return _error(str(exc), 503)
    except req_lib.HTTPError as exc:
        return _error(str(exc), 502)
    except Exception as exc:  # noqa: BLE001
        return _error(f"Unexpected error: {exc}", 500)


@app.route("/api/order", methods=["GET"])
def api_get_order() -> tuple[Any, int]:
    """
    GET /api/order?symbol=BTCUSDT&order_id=123456789

    Fetch the status of an existing order.

    Returns:
        JSON with ``success`` flag and ``order`` dict on success.
    """
    raw_symbol = request.args.get("symbol", "")
    raw_oid = request.args.get("order_id", "")

    try:
        symbol = validate_symbol(raw_symbol)
        order_id = int(raw_oid)
    except (click.BadParameter, ValueError) as exc:
        return _error(str(exc))

    try:
        client = _get_client()
        manager = OrderManager(client)
        result = manager.get_order(symbol=symbol, order_id=order_id)

        update_ms = result.get("updateTime", 0)
        try:
            dt = datetime.fromtimestamp(update_ms / 1000, tz=timezone.utc)
            result["updateTimeHuman"] = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:  # noqa: BLE001
            result["updateTimeHuman"] = str(update_ms)

        return jsonify({"success": True, "order": result}), 200

    except EnvironmentError as exc:
        return _error(str(exc), 503)
    except req_lib.HTTPError as exc:
        return _error(str(exc), 502)
    except Exception as exc:  # noqa: BLE001
        return _error(f"Unexpected error: {exc}", 500)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        BinanceFuturesClient()  # Validate credentials before serving
    except EnvironmentError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(1)

    port = int(os.environ.get("PORT", 5000))
    print(f"🚀  Web UI running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
