"""
Input validation functions for the Binance Futures Trading Bot CLI.

All functions raise :class:`click.BadParameter` on invalid input so that
Click can display a helpful error message automatically.
"""

import re
from typing import Optional

import click


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalise a trading pair symbol.

    Strips surrounding whitespace and converts to uppercase.
    Must match the pattern ``^[A-Z]{2,20}$`` (letters only, 2-20 chars).

    Args:
        symbol: Raw symbol string provided by the user.

    Returns:
        Normalised uppercase symbol.

    Raises:
        click.BadParameter: If the symbol does not match the expected pattern.
    """
    symbol = symbol.strip().upper()
    pattern = re.compile(r"^[A-Z]{2,20}$")
    if not pattern.match(symbol):
        raise click.BadParameter(
            f"'{symbol}' is not a valid symbol. "
            "Symbol must be 2–20 uppercase letters only (e.g. BTCUSDT, ETHUSDT).",
            param_hint="--symbol",
        )
    return symbol


def validate_side(side: str) -> str:
    """
    Validate the order side.

    Args:
        side: Raw side string (``"BUY"`` or ``"SELL"``).

    Returns:
        Uppercase side string.

    Raises:
        click.BadParameter: If *side* is not ``BUY`` or ``SELL``.
    """
    side = side.strip().upper()
    valid_sides = {"BUY", "SELL"}
    if side not in valid_sides:
        raise click.BadParameter(
            f"'{side}' is not a valid side. Must be one of: {', '.join(sorted(valid_sides))}.",
            param_hint="--side",
        )
    return side


def validate_order_type(order_type: str) -> str:
    """
    Validate the order type.

    Args:
        order_type: Raw order type string.

    Returns:
        Uppercase order type string.

    Raises:
        click.BadParameter: If *order_type* is not one of the supported types.
    """
    order_type = order_type.strip().upper()
    valid_types = {"MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"}
    if order_type not in valid_types:
        raise click.BadParameter(
            f"'{order_type}' is not a supported order type. "
            f"Must be one of: {', '.join(sorted(valid_types))}.",
            param_hint="--type",
        )
    return order_type


def validate_quantity(quantity: str) -> float:
    """
    Validate and parse the order quantity.

    Must be a positive float no greater than 1,000,000.

    Args:
        quantity: Raw quantity string provided by the user.

    Returns:
        Parsed quantity as a :class:`float`.

    Raises:
        click.BadParameter: If *quantity* is not a valid positive number within range.
    """
    try:
        qty = float(quantity)
    except (ValueError, TypeError):
        raise click.BadParameter(
            f"'{quantity}' is not a valid number. Quantity must be a positive decimal (e.g. 0.01).",
            param_hint="--quantity",
        )

    if qty <= 0:
        raise click.BadParameter(
            f"Quantity must be greater than 0. Got: {qty}.",
            param_hint="--quantity",
        )

    if qty > 1_000_000:
        raise click.BadParameter(
            f"Quantity exceeds the maximum allowed value of 1,000,000. Got: {qty}.",
            param_hint="--quantity",
        )

    return qty


def validate_price(price: Optional[str], order_type: str) -> Optional[float]:
    """
    Validate the order price based on the order type.

    - ``MARKET`` orders: price must be ``None``.
    - ``STOP_MARKET`` orders: price must be ``None`` (use stop_price instead).
    - ``LIMIT`` orders: price is required and must be > 0.

    Args:
        price:      Raw price string, or ``None`` if not provided.
        order_type: Validated order type string (uppercase).

    Returns:
        Parsed price as :class:`float`, or ``None`` for MARKET/STOP_MARKET orders.

    Raises:
        click.BadParameter: If the price is missing for LIMIT orders,
            or if it is provided for MARKET/STOP_MARKET orders, or if it is not a
            valid positive number.
    """
    if order_type in ("MARKET", "STOP_MARKET"):
        if price is not None:
            raise click.BadParameter(
                f"Price must not be specified for {order_type} orders. "
                "Remove the --price flag.",
                param_hint="--price",
            )
        return None

    # LIMIT — price is required
    if price is None:
        raise click.BadParameter(
            "Price is required for LIMIT orders. "
            "Please provide --price <value>.",
            param_hint="--price",
        )

    try:
        parsed_price = float(price)
    except (ValueError, TypeError):
        raise click.BadParameter(
            f"'{price}' is not a valid price. Must be a positive decimal number.",
            param_hint="--price",
        )

    if parsed_price <= 0:
        raise click.BadParameter(
            f"Price must be greater than 0. Got: {parsed_price}.",
            param_hint="--price",
        )

    return parsed_price


def validate_time_in_force(tif: str) -> str:
    """
    Validate the time-in-force parameter.

    Defaults to ``"GTC"`` if an empty string or ``None`` is provided.

    Args:
        tif: Raw time-in-force string.

    Returns:
        Uppercase time-in-force string (``GTC``, ``IOC``, or ``FOK``).

    Raises:
        click.BadParameter: If *tif* is not one of the accepted values.
    """
    if not tif:
        return "GTC"

    tif = tif.strip().upper()
    valid_tif = {"GTC", "IOC", "FOK"}
    if tif not in valid_tif:
        raise click.BadParameter(
            f"'{tif}' is not a valid time-in-force value. "
            f"Must be one of: {', '.join(sorted(valid_tif))}.",
            param_hint="--tif",
        )
    return tif
