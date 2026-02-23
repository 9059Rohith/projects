"""
Order management for the Binance Futures Trading Bot.

Provides :class:`OrderManager` which wraps the low-level
:class:`~bot.client.BinanceFuturesClient` to place, query, cancel,
and format orders on Binance Futures Testnet.
"""

from datetime import datetime, timezone
from typing import Optional

from bot.client import BinanceFuturesClient
from bot.logging_config import get_logger


class OrderManager:
    """
    High-level order operations built on top of :class:`BinanceFuturesClient`.

    Handles parameter construction, logging, and result formatting for
    all order lifecycle operations.
    """

    def __init__(self, client: BinanceFuturesClient) -> None:
        """
        Initialise the OrderManager.

        Args:
            client: An authenticated :class:`BinanceFuturesClient` instance.
        """
        self.client = client
        self.logger = get_logger("OrderManager")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        time_in_force: str = "GTC",
        stop_price: Optional[float] = None,
    ) -> dict:
        """
        Place a new order on Binance Futures Testnet.

        Constructs and sends a ``POST /fapi/v1/order`` request with the
        appropriate parameters for the given order type.

        Args:
            symbol:         Trading pair symbol (e.g. ``BTCUSDT``).
            side:           Order side — ``BUY`` or ``SELL``.
            order_type:     Order type — ``MARKET``, ``LIMIT``, ``STOP_MARKET``,
                            or ``STOP_LIMIT``.
            quantity:       Quantity of the base asset to trade.
            price:          Limit price (required for LIMIT / STOP_LIMIT orders).
            time_in_force:  Time-in-force policy for LIMIT/STOP_LIMIT orders (default ``GTC``).
            stop_price:     Trigger price for STOP_MARKET / STOP_LIMIT orders.

        Returns:
            Parsed JSON response dict from the Binance API.
        """
        params: dict = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
        }

        if order_type.upper() == "LIMIT":
            if price is None:
                raise ValueError("Price is required for LIMIT orders.")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        elif order_type.upper() == "STOP_MARKET":
            if stop_price is None:
                raise ValueError("stop_price is required for STOP_MARKET orders.")
            params["stopPrice"] = str(stop_price)

        elif order_type.upper() == "STOP_LIMIT":
            if price is None:
                raise ValueError("Price (limit price) is required for STOP_LIMIT orders.")
            if stop_price is None:
                raise ValueError("stop_price (trigger price) is required for STOP_LIMIT orders.")
            params["price"] = str(price)
            params["stopPrice"] = str(stop_price)
            params["timeInForce"] = time_in_force

        # MARKET orders — no price fields

        self.logger.info(
            "Placing %s %s order | symbol=%s quantity=%s price=%s stopPrice=%s tif=%s",
            side.upper(),
            order_type.upper(),
            symbol.upper(),
            quantity,
            price if price is not None else "N/A",
            stop_price if stop_price is not None else "N/A",
            time_in_force,
        )

        response = self.client.post("/fapi/v1/order", params=params)
        self.logger.info("Order placed successfully: %s", response)
        return response

    def get_order(self, symbol: str, order_id: int) -> dict:
        """
        Retrieve the details of an existing order.

        Args:
            symbol:   Trading pair symbol (e.g. ``BTCUSDT``).
            order_id: Binance order ID integer.

        Returns:
            Parsed JSON response dict with order details.
        """
        params = {"symbol": symbol.upper(), "orderId": order_id}
        self.logger.info("Fetching order %s for symbol %s", order_id, symbol)
        response = self.client.get("/fapi/v1/order", params=params, signed=True)
        self.logger.debug("Order status response: %s", response)
        return response

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """
        Cancel an existing open order.

        Args:
            symbol:   Trading pair symbol (e.g. ``BTCUSDT``).
            order_id: Binance order ID integer.

        Returns:
            Parsed JSON response dict confirming cancellation.
        """
        params = {"symbol": symbol.upper(), "orderId": order_id}
        self.logger.info("Cancelling order %s for symbol %s", order_id, symbol)
        response = self.client.delete("/fapi/v1/order", params=params, signed=True)
        self.logger.info("Order cancelled: %s", response)
        return response

    def format_order_result(self, order: dict) -> str:
        """
        Format an order response dict into a human-readable summary string.

        Converts the ``updateTime`` millisecond timestamp in *order* to a
        UTC datetime string.

        Args:
            order: Binance order response dict.

        Returns:
            A formatted multi-line string ready to print to the console.
        """
        update_time_ms = order.get("updateTime", 0)
        try:
            update_dt = datetime.fromtimestamp(update_time_ms / 1000, tz=timezone.utc)
            time_str = update_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (OSError, OverflowError, ValueError):
            time_str = str(update_time_ms)

        border = "=" * 60
        lines = [
            border,
            "           ORDER RESULT",
            border,
            f"  Order ID     : {order.get('orderId', 'N/A')}",
            f"  Symbol       : {order.get('symbol', 'N/A')}",
            f"  Side         : {order.get('side', 'N/A')}",
            f"  Type         : {order.get('type', 'N/A')}",
            f"  Status       : {order.get('status', 'N/A')}",
            f"  Quantity     : {order.get('origQty', 'N/A')}",
            f"  Executed Qty : {order.get('executedQty', 'N/A')}",
            f"  Avg Price    : {order.get('avgPrice', 'N/A')}",
            f"  Price        : {order.get('price', 'N/A')}",
            f"  Time         : {time_str}",
            border,
        ]
        return "\n".join(lines)
