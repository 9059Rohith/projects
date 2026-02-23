"""
Binance Futures REST API client.

Handles authentication, request signing, and raw HTTP communication
with the Binance Futures Testnet (https://testnet.binancefuture.com).
"""

import hashlib
import hmac
import os
import time
from typing import Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from bot.logging_config import get_logger

load_dotenv()


class BinanceFuturesClient:
    """
    Low-level wrapper around the Binance Futures Testnet REST API.

    Uses a persistent :class:`requests.Session` with HMAC-SHA256 signed
    requests where required.
    """

    BASE_URL: str = "https://testnet.binancefuture.com"

    def __init__(self) -> None:
        """
        Initialise the client by reading credentials from environment variables.

        Raises:
            EnvironmentError: If BINANCE_API_KEY or BINANCE_API_SECRET are not set.
        """
        self.api_key: str = os.getenv("BINANCE_API_KEY", "")
        self.api_secret: str = os.getenv("BINANCE_API_SECRET", "")

        if not self.api_key:
            raise EnvironmentError(
                "BINANCE_API_KEY is not set. "
                "Please copy .env.example to .env and fill in your testnet API key."
            )
        if not self.api_secret:
            raise EnvironmentError(
                "BINANCE_API_SECRET is not set. "
                "Please copy .env.example to .env and fill in your testnet API secret."
            )

        self.base_url: str = self.BASE_URL
        self.session: requests.Session = requests.Session()
        self.session.headers.update(
            {
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        self.logger = get_logger("BinanceFuturesClient")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _mask_params(self, params: dict) -> dict:
        """
        Return a copy of *params* with sensitive values redacted for logging.

        Args:
            params: Original request parameters.

        Returns:
            A copy with the ``signature`` key value replaced by ``"***"``.
        """
        masked = dict(params)
        if "signature" in masked:
            masked["signature"] = "***"
        return masked

    def _sign(self, params: dict) -> dict:
        """
        Add a timestamp and HMAC-SHA256 signature to *params*.

        Args:
            params: Request parameters to sign (mutated in place and returned).

        Returns:
            The same dict with ``timestamp`` and ``signature`` added.
        """
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _handle_response(self, response: requests.Response) -> dict:
        """
        Log and validate an HTTP response from the Binance API.

        Args:
            response: The HTTP response object.

        Returns:
            Parsed JSON body as a dict.

        Raises:
            requests.HTTPError: If the HTTP status code is not 200.
        """
        self.logger.debug("Response %s: %s", response.status_code, response.text)

        if response.status_code != 200:
            try:
                error_body = response.json()
                error_code = error_body.get("code", "N/A")
                error_msg = error_body.get("msg", response.text)
            except ValueError:
                error_code = "N/A"
                error_msg = response.text

            raise requests.HTTPError(
                f"Binance API Error {response.status_code}: {error_code} — {error_msg}",
                response=response,
            )

        return response.json()

    # ------------------------------------------------------------------
    # Public HTTP methods
    # ------------------------------------------------------------------

    def get(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        signed: bool = False,
    ) -> dict:
        """
        Send a signed or unsigned GET request.

        Args:
            endpoint: API path (e.g. ``/fapi/v1/exchangeInfo``).
            params:   Query parameters.
            signed:   Whether to add timestamp + HMAC signature.

        Returns:
            Parsed JSON response.
        """
        if params is None:
            params = {}

        if signed:
            params = self._sign(params)

        self.logger.debug("GET %s params=%s", endpoint, self._mask_params(params))

        url = self.base_url + endpoint
        response = self.session.get(url, params=params, timeout=10)
        return self._handle_response(response)

    def post(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        signed: bool = True,
    ) -> dict:
        """
        Send a signed or unsigned POST request.

        Args:
            endpoint: API path (e.g. ``/fapi/v1/order``).
            params:   Form-encoded body parameters.
            signed:   Whether to add timestamp + HMAC signature.

        Returns:
            Parsed JSON response.
        """
        if params is None:
            params = {}

        if signed:
            params = self._sign(params)

        self.logger.debug("POST %s params=%s", endpoint, self._mask_params(params))

        url = self.base_url + endpoint
        response = self.session.post(url, data=params, timeout=10)
        return self._handle_response(response)

    def delete(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        signed: bool = True,
    ) -> dict:
        """
        Send a signed or unsigned DELETE request.

        Args:
            endpoint: API path (e.g. ``/fapi/v1/order``).
            params:   Query parameters.
            signed:   Whether to add timestamp + HMAC signature.

        Returns:
            Parsed JSON response.
        """
        if params is None:
            params = {}

        if signed:
            params = self._sign(params)

        self.logger.debug("DELETE %s params=%s", endpoint, self._mask_params(params))

        url = self.base_url + endpoint
        response = self.session.delete(url, params=params, timeout=10)
        return self._handle_response(response)

    # ------------------------------------------------------------------
    # High-level API helpers
    # ------------------------------------------------------------------

    def get_exchange_info(self, symbol: str) -> dict:
        """
        Retrieve exchange information for a specific symbol.

        Args:
            symbol: Trading pair symbol (e.g. ``BTCUSDT``).

        Returns:
            The symbol's info dict from ``/fapi/v1/exchangeInfo``.

        Raises:
            ValueError: If the symbol is not found on the exchange.
        """
        data = self.get("/fapi/v1/exchangeInfo")
        for sym_info in data.get("symbols", []):
            if sym_info.get("symbol") == symbol.upper():
                return sym_info
        raise ValueError(
            f"Symbol '{symbol}' was not found on Binance Futures Testnet. "
            "Check that the symbol is correct (e.g. BTCUSDT)."
        )

    def get_account_balance(self) -> list:
        """
        Retrieve all account asset balances that have a non-zero value.

        Returns:
            A list of balance dicts for assets where ``balance`` > 0.
        """
        data = self.get("/fapi/v2/account", signed=True)
        assets: list = data.get("assets", [])
        return [
            asset for asset in assets
            if float(asset.get("walletBalance", 0)) > 0
        ]
