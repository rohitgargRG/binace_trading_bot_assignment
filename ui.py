# ui.py
import streamlit as st
from binance.exceptions import BinanceAPIException, BinanceRequestException

from trading_bot import create_bot_from_config


def validate_notional_size(bot, symbol: str, qty: float, price: float | None) -> bool:
    """
    Quick check so we don't send obviously too small orders.
    If price is None (for MARKET), we pull current mark price.
    """
    try:
        if price is None:
            mark = bot.client.futures_mark_price(symbol=symbol)
            px = float(mark["markPrice"])
        else:
            px = float(price)

        notional = px * qty
    except Exception as exc:
        # if this fails (network etc.), we just warn and let Binance decide
        st.warning(f"Could not check notional size: {exc}")
        return True

    if notional < 100:
        st.error(
            f"Estimated notional is only **{notional:.2f} USDT**.\n\n"
            "For opening new positions, Binance Futures Testnet expects roughly "
            "**100 USDT or more**.\n"
            "Try increasing the quantity or using a cheaper symbol."
        )
        return False

    return True


def render_account_box(bot) -> None:
    """Show a small card with USDT balance, if we can fetch it."""
    try:
        info = bot.get_account_info()
        st.subheader("Futures Account (USDT-M)")

        assets = info.get("assets", [])
        usdt_rows = [row for row in assets if row.get("asset") == "USDT"]

        if usdt_rows:
            row = usdt_rows[0]
            st.metric("USDT wallet balance", row.get("walletBalance"))
            st.metric("USDT available", row.get("availableBalance"))
        else:
            st.write("No USDT entry found in account assets.")
    except Exception as exc:
        st.error(f"Could not load account info: {exc}")


def main():
    st.set_page_config(page_title="Futures Testnet Bot", layout="centered")
    st.title("Binance Futures Testnet – Mini Trading Panel")
    st.caption("Simple assignment project: MARKET / LIMIT / STOP-LIMIT orders.")

    bot = create_bot_from_config()

    # left sidebar: just account-related stuff
    with st.sidebar:
        st.header("Account")
        if st.button("Load account info"):
            render_account_box(bot)

    st.subheader("Create Order")

    # basic form inputs
    symbol = st.text_input("Symbol", value="BTCUSDT", help="Example: BTCUSDT, ETHUSDT")
    side = st.radio("Side", options=["BUY", "SELL"], horizontal=True)

    order_type = st.selectbox(
        "Order type",
        options=["MARKET", "LIMIT", "STOP_LIMIT"],
    )

    qty = st.number_input(
        "Quantity",
        min_value=0.0,
        step=0.001,
        format="%.6f",
    )

    limit_price = None
    stop_price = None

    if order_type in ("LIMIT", "STOP_LIMIT"):
        limit_price = st.number_input(
            "Limit price",
            min_value=0.0,
            step=0.1,
            format="%.2f",
            help="Price you want your limit order to sit at.",
        )

    if order_type == "STOP_LIMIT":
        stop_price = st.number_input(
            "Stop price",
            min_value=0.0,
            step=0.1,
            format="%.2f",
            help="Trigger price for the stop part.",
        )

    tif = st.selectbox(
        "Time in force",
        options=["GTC", "IOC", "FOK"],
        index=0,
        help="GTC = Good Till Cancel, IOC = Immediate Or Cancel, FOK = Fill Or Kill",
    )

    if st.button("Place order"):
        # a couple of straightforward checks before we hit the API
        if not symbol:
            st.error("Symbol is required.")
            return

        if qty <= 0:
            st.error("Quantity must be greater than zero.")
            return

        if order_type == "LIMIT" and (not limit_price or limit_price <= 0):
            st.error("Limit price must be set and > 0 for LIMIT orders.")
            return

        if order_type == "STOP_LIMIT":
            if not limit_price or limit_price <= 0 or not stop_price or stop_price <= 0:
                st.error("Both limit price and stop price must be > 0 for STOP_LIMIT.")
                return

        # notional check before sending the request
        if order_type == "MARKET":
            if not validate_notional_size(bot, symbol, qty, price=None):
                return
        else:
            if not validate_notional_size(bot, symbol, qty, price=limit_price):
                return

        try:
            # hit the bot depending on the selected order type
            if order_type == "MARKET":
                order = bot.place_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                )
            elif order_type == "LIMIT":
                order = bot.place_limit_order(
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    price=limit_price,
                    time_in_force=tif,
                )
            elif order_type == "STOP_LIMIT":
                order = bot.place_stop_limit_order(
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    price=limit_price,
                    stop_price=stop_price,
                    time_in_force=tif,
                )
            else:
                st.error(f"Order type '{order_type}' is not supported.")
                return

            st.success("Order placed successfully.")
            # show raw JSON so it's clear what Binance returned
            st.json(order)

        except BinanceAPIException as exc:
            st.error(
                "Order rejected by Binance.\n\n"
                f"Code: {exc.code}\n"
                f"Message: {exc.message}"
            )
            if exc.code == -4164:
                st.info(
                    "This usually means price × quantity is below the ~100 USDT "
                    "minimum for opening a position."
                )

        except BinanceRequestException as exc:
            st.error(f"Network / request error while talking to Binance: {exc}")

        except Exception as exc:
            st.error(f"Unexpected error: {exc}")


if __name__ == "__main__":
    main()
