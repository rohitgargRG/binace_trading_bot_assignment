import logging
from logging.handlers import RotatingFileHandler
import os
import time
from typing import Dict, Any

from binance import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

from config import API_KEY, API_SECRET, USE_TESTNET


# simple logger so we don't spam print() everywhere
def _init_logger() -> logging.Logger:
    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger("futures_bot")
    logger.setLevel(logging.INFO)

    # avoid adding handlers twice (streamlit reload, etc.)
    if logger.handlers:
        return logger

    file_handler = RotatingFileHandler(
        "logs/bot.log", maxBytes=1_000_000, backupCount=3
    )
    console_handler = logging.StreamHandler()

    fmt = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    file_handler.setFormatter(fmt)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


class BasicBot:
    """
    Very small wrapper around python-binance client.
    Just enough for this assignment: account info + a few order types.
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True) -> None:
        self.logger = _init_logger()

        # 1) create client WITHOUT keys and WITHOUT testnet flag
        #    so the internal ping() in Client.__init__ hits a public endpoint.
        self.client = Client("", "", testnet=False)

        # 2) route futures calls to testnet if requested
        if testnet:
            self.client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

        # 3) inject the real credentials
        self.client.API_KEY = api_key
        self.client.API_SECRET = api_secret

        # IMPORTANT: also update the HTTP header that actually sends the key
        self.client.session.headers.update({"X-MBX-APIKEY": api_key})

        # store for possible debugging
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # 4) sync time to reduce -1021 timestamp errors
        self._sync_time_with_server()

        self.logger.info("BasicBot started (testnet=%s)", testnet)

    def _sync_time_with_server(self) -> None:
        """
        Adjust client's timestamp offset so our signed requests line up with Binance time.
        If this fails we just log a warning and continue.
        """
        try:
            server_time = self.client.get_server_time()
            local_ms = int(time.time() * 1000)
            offset = server_time["serverTime"] - local_ms
            self.client.timestamp_offset = offset
            self.logger.info("Timestamp offset set to %s ms", offset)
        except Exception as exc:
            self.logger.warning("Could not sync time with Binance: %s", exc)

    def get_account_info(self) -> Dict[str, Any]:
        """Return futures account information (balances, positions etc.)."""
        try:
            data = self.client.futures_account()
            self.logger.info("Fetched futures account info")
            return data
        except (BinanceAPIException, BinanceRequestException) as exc:
            self.logger.error("Error while fetching account info: %s", exc)
            raise

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
    ) -> Dict[str, Any]:
        """
        Send a simple MARKET order.
        side should be either 'BUY' or 'SELL'.
        """
        self.logger.info(
            "Sending MARKET order: symbol=%s side=%s qty=%s",
            symbol,
            side,
            quantity,
        )
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=quantity,
                recvWindow=5000,  # small grace window for time drift
            )
            self.logger.info("Market order accepted: %s", order)
            return order
        except (BinanceAPIException, BinanceRequestException) as exc:
            self.logger.error("Market order failed: %s", exc)
            raise

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """
        Standard LIMIT order.
        time_in_force usually: 'GTC', 'IOC', or 'FOK'.
        """
        self.logger.info(
            "Sending LIMIT order: %s %s qty=%s @ price=%s tif=%s",
            symbol,
            side,
            quantity,
            price,
            time_in_force,
        )
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="LIMIT",
                timeInForce=time_in_force,
                quantity=quantity,
                price=str(price),  # Binance expects string for price
                recvWindow=5000,
            )
            self.logger.info("Limit order accepted: %s", order)
            return order
        except (BinanceAPIException, BinanceRequestException) as exc:
            self.logger.error("Limit order failed: %s", exc)
            raise

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """
        Simple STOP-LIMIT style order.
        stop_price: trigger level
        price:      actual limit price once triggered
        """
        self.logger.info(
            "Sending STOP-LIMIT: %s %s qty=%s limit=%s stop=%s tif=%s",
            symbol,
            side,
            quantity,
            price,
            stop_price,
            time_in_force,
        )
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="STOP",
                timeInForce=time_in_force,
                quantity=quantity,
                price=str(price),
                stopPrice=str(stop_price),
                workingType="MARK_PRICE",
                recvWindow=5000,
            )
            self.logger.info("Stop-limit order accepted: %s", order)
            return order
        except (BinanceAPIException, BinanceRequestException) as exc:
            self.logger.error("Stop-limit order failed: %s", exc)
            raise


def create_bot_from_config() -> BasicBot:
    """
    Helper so other modules don't need to know where API keys come from.
    """
    return BasicBot(
        api_key=API_KEY,
        api_secret=API_SECRET,
        testnet=USE_TESTNET,
    )
