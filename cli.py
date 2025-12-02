import argparse
import sys

from binance.exceptions import BinanceAPIException, BinanceRequestException
from trading_bot import create_bot_from_config


def parse_positive_float(value: str) -> float:
    """Helper for argparse: expects a float > 0."""
    try:
        val = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"could not convert '{value}' to float")
    if val <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return val


def get_arguments():
    """
    Small wrapper around argparse, just to keep main() a bit cleaner.
    """
    parser = argparse.ArgumentParser(
        description="Tiny Binance Futures Testnet trading helper (CLI)."
    )

    parser.add_argument(
        "--symbol",
        required=True,
        help="pair to trade, e.g. BTCUSDT",
    )
    parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        help="BUY or SELL",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT"],
        help="order type",
    )
    parser.add_argument(
        "--quantity",
        required=True,
        type=parse_positive_float,
        help="quantity to trade",
    )
    parser.add_argument(
        "--price",
        type=parse_positive_float,
        help="limit price (needed for LIMIT and STOP_LIMIT)",
    )
    parser.add_argument(
        "--stop_price",
        type=parse_positive_float,
        help="stop price (only for STOP_LIMIT)",
    )
    parser.add_argument(
        "--tif",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="time in force, default GTC",
    )

    return parser.parse_args()


def validate_notional(bot, symbol: str, qty: float, price: float | None) -> bool:
    """
    Quick sanity check: Binance Futures usually wants notional >= 100 USDT.
    If price is None (MARKET order), use current mark price from the API.
    Returns True if notional looks OK, False otherwise.
    """
    try:
        if price is None:
            mark_info = bot.client.futures_mark_price(symbol=symbol)
            px = float(mark_info["markPrice"])
        else:
            px = float(price)

        notional = px * qty
    except Exception as exc:
        # if we cannot check for some reason, don't completely block the order
        print("Warning: could not check notional size:", exc)
        return True

    if notional < 100:
        print()
        print("Order not sent:")
        print(f"  estimated notional = {notional:.2f} USDT (price * quantity)")
        print("  Binance Futures Testnet expects notional >= 100 USDT.")
        print("  Try increasing quantity or using a cheaper symbol.")
        return False

    return True


def show_order_summary(order: dict) -> None:
    """Print a few fields from the order response so it's easy to read."""
    print("\n--- Order Result ---")
    print(f"Symbol      : {order.get('symbol')}")
    print(f"Side        : {order.get('side')}")
    print(f"Type        : {order.get('type')}")
    print(f"Status      : {order.get('status')}")
    print(f"Order ID    : {order.get('orderId')}")
    print(f"Client ID   : {order.get('clientOrderId')}")
    print(f"Price       : {order.get('price')}")
    print(f"Orig Qty    : {order.get('origQty')}")
    print(f"Executed Qty: {order.get('executedQty')}")
    print(f"Update Time : {order.get('updateTime')}")


def main():
    args = get_arguments()
    bot = create_bot_from_config()

    # basic argument checks depending on the order type
    if args.type == "LIMIT" and args.price is None:
        print("Error: --price is required for LIMIT orders.")
        sys.exit(1)

    if args.type == "STOP_LIMIT" and (args.price is None or args.stop_price is None):
        print("Error: --price and --stop_price are required for STOP_LIMIT orders.")
        sys.exit(1)

    # notional check before even talking to Binance
    if args.type == "MARKET":
        ok = validate_notional(bot, args.symbol, args.quantity, price=None)
    else:
        ok = validate_notional(bot, args.symbol, args.quantity, price=args.price)

    if not ok:
        sys.exit(1)

    try:
        if args.type == "MARKET":
            order = bot.place_market_order(
                symbol=args.symbol,
                side=args.side,
                quantity=args.quantity,
            )
        elif args.type == "LIMIT":
            order = bot.place_limit_order(
                symbol=args.symbol,
                side=args.side,
                quantity=args.quantity,
                price=args.price,
                time_in_force=args.tif,
            )
        elif args.type == "STOP_LIMIT":
            order = bot.place_stop_limit_order(
                symbol=args.symbol,
                side=args.side,
                quantity=args.quantity,
                price=args.price,
                stop_price=args.stop_price,
                time_in_force=args.tif,
            )
        else:
            print(f"Unsupported order type: {args.type}")
            sys.exit(1)

        show_order_summary(order)

    except BinanceAPIException as exc:
        print("\nOrder rejected by Binance:")
        print(f"  code   : {exc.code}")
        print(f"  message: {exc.message}")

        if exc.code == -4164:
            print()
            print("This usually means price * quantity is below 100 USDT.")
            print("Adjust the size or pick another symbol and try again.")

    except BinanceRequestException as exc:
        print("\nNetwork error while talking to Binance:")
        print(" ", exc)

    except Exception as exc:
        print("\nUnexpected error:")
        print(" ", exc)


if __name__ == "__main__":
    main()
