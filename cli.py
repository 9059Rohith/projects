"""
CLI entry point for the Binance Futures Testnet Trading Bot.

Usage::

    python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
    python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_LIMIT \\
        --quantity 0.01 --price 94000 --stop-price 95000
    python cli.py account-balance
    python cli.py order-status --symbol BTCUSDT --order-id 123456789
    python cli.py interactive
"""

import sys
from typing import Optional

import click
import requests

from bot.client import BinanceFuturesClient
from bot.orders import OrderManager
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
    validate_time_in_force,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> BinanceFuturesClient:
    """
    Construct a :class:`BinanceFuturesClient`, exiting cleanly on config errors.

    Returns:
        An initialised :class:`BinanceFuturesClient`.
    """
    try:
        return BinanceFuturesClient()
    except EnvironmentError as exc:
        click.echo(f"❌ Configuration error: {exc}", err=True)
        sys.exit(1)


def _validate_stop_price(stop_price: Optional[str], order_type: str) -> Optional[float]:
    """
    Validate the stop price parameter for order types that require it.

    Args:
        stop_price:  Raw stop-price string, or ``None``.
        order_type:  Validated order type string (uppercase).

    Returns:
        Parsed stop price as :class:`float`, or ``None`` for MARKET/LIMIT orders.

    Raises:
        click.BadParameter: If the stop price is missing or invalid.
    """
    needs_stop = order_type in {"STOP_MARKET", "STOP_LIMIT"}
    if not needs_stop:
        return None

    if stop_price is None:
        raise click.BadParameter(
            f"--stop-price is required for {order_type} orders.",
            param_hint="--stop-price",
        )
    try:
        parsed = float(stop_price)
        if parsed <= 0:
            raise ValueError
        return parsed
    except ValueError:
        raise click.BadParameter(
            f"'{stop_price}' is not a valid stop price. Must be a positive number.",
            param_hint="--stop-price",
        )


def _print_order_summary(
    symbol: str,
    side: str,
    order_type: str,
    qty: float,
    price: Optional[float],
    stop_price: Optional[float],
    tif: str,
) -> None:
    """
    Print a formatted order request summary table to stdout.

    Args:
        symbol:     Trading pair symbol.
        side:       Order side.
        order_type: Order type.
        qty:        Order quantity.
        price:      Limit price or None.
        stop_price: Stop trigger price or None.
        tif:        Time-in-force string.
    """
    border = "=" * 60
    click.echo(border)
    click.echo("           ORDER REQUEST SUMMARY")
    click.echo(border)
    click.echo(f"  Symbol     : {symbol}")
    click.echo(f"  Side       : {side}")
    click.echo(f"  Type       : {order_type}")
    click.echo(f"  Quantity   : {qty}")
    click.echo(f"  Price      : {price if price is not None else 'N/A'}")
    if stop_price is not None:
        click.echo(f"  Stop Price : {stop_price}")
    if order_type in {"LIMIT", "STOP_LIMIT"}:
        click.echo(f"  TIF        : {tif}")
    click.echo(border)
    click.echo()


def _execute_and_print_order(
    manager: OrderManager,
    symbol: str,
    side: str,
    order_type: str,
    qty: float,
    parsed_price: Optional[float],
    tif: str,
    parsed_stop_price: Optional[float],
) -> None:
    """
    Call place_order on the manager and print the result, handling errors gracefully.

    Args:
        manager:           Initialised :class:`OrderManager`.
        symbol:            Trading pair symbol.
        side:              Order side.
        order_type:        Order type.
        qty:               Order quantity.
        parsed_price:      Validated limit price or None.
        tif:               Time-in-force string.
        parsed_stop_price: Validated stop price or None.
    """
    try:
        result = manager.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=qty,
            price=parsed_price,
            time_in_force=tif,
            stop_price=parsed_stop_price,
        )
    except requests.HTTPError as exc:
        click.echo(f"\n❌ Order failed: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"\n❌ Unexpected error: {exc}", err=True)
        sys.exit(1)

    click.echo(manager.format_order_result(result))
    click.echo()
    click.echo("✅ Order placed successfully!")


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version="1.0.0", prog_name="Trading Bot")
def cli() -> None:
    """Binance Futures Testnet Trading Bot."""


# ---------------------------------------------------------------------------
# place-order
# ---------------------------------------------------------------------------

@cli.command("place-order")
@click.option("--symbol", required=True, type=str,
              help="Trading pair symbol, e.g. BTCUSDT.")
@click.option("--side", required=True, type=str,
              help="Order side: BUY or SELL.")
@click.option("--type", "order_type", required=True, type=str,
              help="Order type: MARKET, LIMIT, STOP_MARKET, or STOP_LIMIT.")
@click.option("--quantity", required=True, type=str,
              help="Quantity of the base asset to trade (e.g. 0.01).")
@click.option("--price", default=None, type=str,
              help="Limit price. Required for LIMIT and STOP_LIMIT orders.")
@click.option("--tif", default="GTC", type=str, show_default=True,
              help="Time-in-force for LIMIT/STOP_LIMIT orders: GTC, IOC, or FOK.")
@click.option("--stop-price", "stop_price", default=None, type=str,
              help="Stop trigger price. Required for STOP_MARKET and STOP_LIMIT orders.")
def place_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str],
    tif: str,
    stop_price: Optional[str],
) -> None:
    """
    Place a new order on Binance Futures Testnet.

    Supported order types:

    \b
      MARKET     — executes immediately at market price
      LIMIT      — executes at --price or better (requires --price)
      STOP_MARKET — triggers a market order when --stop-price is reached
      STOP_LIMIT  — triggers a limit order at --price when --stop-price is hit

    Examples:

    \b
      python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
      python cli.py place-order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 95000
      python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 90000
      python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.01 --price 89500 --stop-price 90000
    """
    try:
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        order_type = validate_order_type(order_type)
        qty = validate_quantity(quantity)
        parsed_price = validate_price(
            price, order_type if order_type != "STOP_LIMIT" else "LIMIT"
        )
        tif = validate_time_in_force(tif)
        parsed_stop_price = _validate_stop_price(stop_price, order_type)
    except click.BadParameter as exc:
        click.echo(f"❌ Validation error: {exc}", err=True)
        sys.exit(1)

    _print_order_summary(symbol, side, order_type, qty, parsed_price, parsed_stop_price, tif)

    client = _make_client()
    manager = OrderManager(client)
    _execute_and_print_order(manager, symbol, side, order_type, qty,
                             parsed_price, tif, parsed_stop_price)


# ---------------------------------------------------------------------------
# account-balance
# ---------------------------------------------------------------------------

@cli.command("account-balance")
def account_balance() -> None:
    """
    Display current Binance Futures Testnet account balances.

    Prints a formatted table of all assets with a non-zero wallet balance,
    showing wallet balance and available (cross wallet) balance.
    """
    client = _make_client()

    try:
        balances = client.get_account_balance()
    except requests.HTTPError as exc:
        click.echo(f"❌ Failed to fetch account balance: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"❌ Unexpected error: {exc}", err=True)
        sys.exit(1)

    if not balances:
        click.echo("ℹ️  No assets with a non-zero balance found.")
        return

    border = "=" * 60
    click.echo(border)
    click.echo("           ACCOUNT BALANCES")
    click.echo(border)
    click.echo(f"  {'Asset':<10} {'Wallet Balance':>20} {'Available Balance':>20}")
    click.echo("-" * 60)

    for asset in balances:
        name = asset.get("asset", "N/A")
        wallet = float(asset.get("walletBalance", 0))
        available = float(asset.get("availableBalance", 0))
        click.echo(f"  {name:<10} {wallet:>20.8f} {available:>20.8f}")

    click.echo(border)


# ---------------------------------------------------------------------------
# order-status
# ---------------------------------------------------------------------------

@cli.command("order-status")
@click.option("--symbol", required=True, type=str,
              help="Trading pair symbol, e.g. BTCUSDT.")
@click.option("--order-id", "order_id", required=True, type=int,
              help="The Binance integer order ID to look up.")
def order_status(symbol: str, order_id: int) -> None:
    """
    Fetch and display the status of an existing order.

    Example:

    \b
      python cli.py order-status --symbol BTCUSDT --order-id 123456789
    """
    try:
        symbol = validate_symbol(symbol)
    except click.BadParameter as exc:
        click.echo(f"❌ Validation error: {exc}", err=True)
        sys.exit(1)

    client = _make_client()
    manager = OrderManager(client)

    try:
        result = manager.get_order(symbol=symbol, order_id=order_id)
    except requests.HTTPError as exc:
        click.echo(f"❌ Failed to fetch order status: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"❌ Unexpected error: {exc}", err=True)
        sys.exit(1)

    click.echo(manager.format_order_result(result))


# ---------------------------------------------------------------------------
# interactive  (Bonus: enhanced guided UX)
# ---------------------------------------------------------------------------

@cli.command("interactive")
def interactive_mode() -> None:
    """
    Launch an interactive guided menu — no flags needed.

    Walk through order placement, balance checks, and order status
    lookups with step-by-step prompts, inline validation feedback,
    and a live confirmation screen before anything is sent.

    \b
      python cli.py interactive
    """
    border = "=" * 60

    click.echo()
    click.echo(border)
    click.echo("   🤖  BINANCE FUTURES TESTNET — INTERACTIVE MODE")
    click.echo(border)
    click.echo()

    # --- Main menu loop ---------------------------------------------------
    while True:
        click.echo("  What would you like to do?")
        click.echo()
        click.echo("    [1] Place an order")
        click.echo("    [2] Check account balance")
        click.echo("    [3] Check order status")
        click.echo("    [4] Exit")
        click.echo()

        choice = click.prompt("  Enter choice", type=click.Choice(["1", "2", "3", "4"]),
                              show_choices=False)
        click.echo()

        # ------------------------------------------------------------------
        # [1] Place order
        # ------------------------------------------------------------------
        if choice == "1":
            # Symbol
            while True:
                raw_symbol = click.prompt("  Symbol (e.g. BTCUSDT)").strip()
                try:
                    symbol = validate_symbol(raw_symbol)
                    break
                except click.BadParameter as e:
                    click.echo(f"  ⚠️  {e}\n")

            # Side
            while True:
                raw_side = click.prompt("  Side [BUY/SELL]").strip()
                try:
                    side = validate_side(raw_side)
                    break
                except click.BadParameter as e:
                    click.echo(f"  ⚠️  {e}\n")

            # Order type
            click.echo()
            click.echo("  Order types:")
            click.echo("    MARKET     — instant fill at market price")
            click.echo("    LIMIT      — fill at your price or better")
            click.echo("    STOP_MARKET — triggers market order at stop price")
            click.echo("    STOP_LIMIT  — triggers limit order at stop price")
            click.echo()
            while True:
                raw_type = click.prompt("  Order type").strip()
                try:
                    order_type = validate_order_type(raw_type)
                    break
                except click.BadParameter as e:
                    click.echo(f"  ⚠️  {e}\n")

            # Quantity
            while True:
                raw_qty = click.prompt("  Quantity").strip()
                try:
                    qty = validate_quantity(raw_qty)
                    break
                except click.BadParameter as e:
                    click.echo(f"  ⚠️  {e}\n")

            # Price (LIMIT / STOP_LIMIT)
            parsed_price: Optional[float] = None
            if order_type in {"LIMIT", "STOP_LIMIT"}:
                while True:
                    raw_price = click.prompt("  Limit price").strip()
                    try:
                        parsed_price = validate_price(raw_price, "LIMIT")
                        break
                    except click.BadParameter as e:
                        click.echo(f"  ⚠️  {e}\n")

            # Stop price (STOP_MARKET / STOP_LIMIT)
            parsed_stop_price: Optional[float] = None
            if order_type in {"STOP_MARKET", "STOP_LIMIT"}:
                while True:
                    raw_stop = click.prompt("  Stop trigger price").strip()
                    try:
                        parsed_stop_price = _validate_stop_price(raw_stop, order_type)
                        break
                    except click.BadParameter as e:
                        click.echo(f"  ⚠️  {e}\n")

            # Time-in-force (LIMIT / STOP_LIMIT)
            tif = "GTC"
            if order_type in {"LIMIT", "STOP_LIMIT"}:
                while True:
                    raw_tif = click.prompt(
                        "  Time-in-force [GTC/IOC/FOK]", default="GTC"
                    ).strip()
                    try:
                        tif = validate_time_in_force(raw_tif)
                        break
                    except click.BadParameter as e:
                        click.echo(f"  ⚠️  {e}\n")

            # Confirmation screen
            click.echo()
            _print_order_summary(symbol, side, order_type, qty,
                                 parsed_price, parsed_stop_price, tif)

            if not click.confirm("  Confirm and place this order?", default=False):
                click.echo("  ↩  Order cancelled.\n")
                continue

            client = _make_client()
            manager = OrderManager(client)
            click.echo()
            _execute_and_print_order(manager, symbol, side, order_type, qty,
                                     parsed_price, tif, parsed_stop_price)

        # ------------------------------------------------------------------
        # [2] Account balance
        # ------------------------------------------------------------------
        elif choice == "2":
            client = _make_client()
            try:
                balances = client.get_account_balance()
            except requests.HTTPError as exc:
                click.echo(f"  ❌ {exc}\n", err=True)
                continue
            except Exception as exc:  # noqa: BLE001
                click.echo(f"  ❌ Unexpected error: {exc}\n", err=True)
                continue

            if not balances:
                click.echo("  ℹ️  No assets with a non-zero balance.\n")
                continue

            click.echo(border)
            click.echo("           ACCOUNT BALANCES")
            click.echo(border)
            click.echo(f"  {'Asset':<10} {'Wallet Balance':>20} {'Available Balance':>20}")
            click.echo("-" * 60)
            for asset in balances:
                name = asset.get("asset", "N/A")
                wallet = float(asset.get("walletBalance", 0))
                available = float(asset.get("availableBalance", 0))
                click.echo(f"  {name:<10} {wallet:>20.8f} {available:>20.8f}")
            click.echo(border)
            click.echo()

        # ------------------------------------------------------------------
        # [3] Order status
        # ------------------------------------------------------------------
        elif choice == "3":
            while True:
                raw_sym = click.prompt("  Symbol (e.g. BTCUSDT)").strip()
                try:
                    sym = validate_symbol(raw_sym)
                    break
                except click.BadParameter as e:
                    click.echo(f"  ⚠️  {e}\n")

            oid = click.prompt("  Order ID", type=int)

            client = _make_client()
            manager = OrderManager(client)
            try:
                result = manager.get_order(symbol=sym, order_id=oid)
            except requests.HTTPError as exc:
                click.echo(f"  ❌ {exc}\n", err=True)
                continue
            except Exception as exc:  # noqa: BLE001
                click.echo(f"  ❌ Unexpected error: {exc}\n", err=True)
                continue

            click.echo()
            click.echo(manager.format_order_result(result))
            click.echo()

        # ------------------------------------------------------------------
        # [4] Exit
        # ------------------------------------------------------------------
        elif choice == "4":
            click.echo("  👋  Goodbye!")
            break

        click.echo()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
