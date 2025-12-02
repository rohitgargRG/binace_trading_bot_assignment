from binance import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET
from typing import Optional, Dict, Any
import logging
from logging.handlers import RotatingFileHandler
import os




def setup_logger() -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    file_handler = RotatingFileHandler("logs/bot.log", maxBytes=1_000_000, backupCount=3)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


class BasicBot:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.logger = setup_logger()

        self.client = Client(api_key, api_secret, testnet=testnet)

        # IMPORTANT: set Futures testnet URL
        if testnet:
            self.client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

        self.logger.info(f"Initialized BasicBot (testnet={testnet})")

    def get_account_info(self) -> Dict[str, Any]:
        """Fetch futures account balance/info."""
        try:
            info = self.client.futures_account()
            self.logger.info(f"Account info fetched successfully")
            return info
        except (BinanceAPIException, BinanceRequestException) as e:
            self.logger.error(f"Error fetching account info: {e}")
            raise

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
    ) -> Dict[str, Any]:
        """
        Place a futures market order.
        side: 'BUY' or 'SELL'
        """
        self.logger.info(
            f"Placing MARKET order: symbol={symbol}, side={side}, qty={quantity}"
        )
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=quantity,
            )
            self.logger.info(f"Market order placed successfully: {order}")
            return order
        except (BinanceAPIException, BinanceRequestException) as e:
            self.logger.error(f"Error placing market order: {e}")
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
        Place a futures limit order.
        time_in_force: 'GTC', 'IOC', 'FOK'
        """
        self.logger.info(
            f"Placing LIMIT order: symbol={symbol}, side={side}, "
            f"qty={quantity}, price={price}, tif={time_in_force}"
        )
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="LIMIT",
                timeInForce=time_in_force,
                quantity=quantity,
                price=str(price),
            )
            self.logger.info(f"Limit order placed successfully: {order}")
            return order
        except (BinanceAPIException, BinanceRequestException) as e:
            self.logger.error(f"Error placing limit order: {e}")
            raise

    # Optional: Stop-Limit example
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
        Place a STOP-LIMIT order (Futures).
        """
        self.logger.info(
            f"Placing STOP-LIMIT order: symbol={symbol}, side={side}, qty={quantity}, "
            f"price={price}, stop_price={stop_price}, tif={time_in_force}"
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
            )
            self.logger.info(f"Stop-Limit order placed successfully: {order}")
            return order
        except (BinanceAPIException, BinanceRequestException) as e:
            self.logger.error(f"Error placing stop-limit order: {e}")
            raise


# Helper to create a bot instance using config
def create_bot_from_config() -> BasicBot:
    return BasicBot(
        api_key=BINANCE_API_KEY,
        api_secret=BINANCE_API_SECRET,
        testnet=BINANCE_TESTNET,
    )
