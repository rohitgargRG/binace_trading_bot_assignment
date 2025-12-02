import argparse
import sys

from binance.exceptions import BinanceAPIException, BinanceRequestException
from trading_bot import create_bot_from_config 


def positive_float(value: str) -> float:
    """Argparse type: positive float."""
    try:
        f = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid float value: {value}")
    if f <= 0:
        raise argparse.ArgumentTypeError("Value must be positive")
    return f


def parse_args():
    parser = argparse.ArgumentParser(
        description="Simple Binance Futures Testnet Trading Bot"
    )

    parser.add_argument(
        "--symbol",
        required=True,
        help="Trading pair symbol, e.g. BTCUSDT",
    )
    parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        help="Order side",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT"],
        help="Order type",
    )
    parser.add_argument(
        "--quantity",
        required=True,
        type=positive_float,
        help="Order quantity",
    )
    parser.add_argument(
        "--price",
        type=positive_float,
        help="Limit/Stop-Limit order price (required for LIMIT/STOP_LIMIT)",
    )
    parser.add_argument(
        "--stop_price",
        type=positive_float,
        help="Stop price (required for STOP_LIMIT)",
    )
    parser.add_argument(
        "--tif",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time in force (for LIMIT/STOP_LIMIT)",
    )

    return parser.parse_args()


def check_min_notional(bot, symbol: str, quantity: float, price: float | None):
    """
    Pre-check: ensure notional >= 100 USDT.
    If price is None (MARKET), use mark price from futures_mark_price.
    """
    try:
        if price is None:
            # For MARKET orders, approximate with current mark price
            mark_data = bot.client.futures_mark_price(symbol=symbol)
            used_price = float(mark_data["markPrice"])
        else:
            used_price = float(price)

        notional = used_price * quantity
    except Exception as e:
        # If this fails (network, symbol error, etc.), just warn and skip precheck
        print("⚠️ Warning: Could not fetch mark price for pre-check:", e)
        return

    if notional < 100:
        print("\n❌ Order NOT sent:")
        print(f"Your order notional = {notional:.2f} USDT (price × quantity).")
        print("Binance Futures Testnet requires notional >= 100 USDT for new positions.")
        print("👉 Try increasing quantity or using a cheaper symbol.")
        sys.exit(1)


def print_order_result(order: dict):
    """Pretty-print key order fields."""
    print("\n=== ORDER RESULT ===")
    print(f"Symbol:     {order.get('symbol')}")
    print(f"Side:       {order.get('side')}")
    print(f"Type:       {order.get('type')}")
    print(f"Status:     {order.get('status')}")
    print(f"Order ID:   {order.get('orderId')}")
    print(f"Client ID:  {order.get('clientOrderId')}")
    print(f"Price:      {order.get('price')}")
    print(f"OrigQty:    {order.get('origQty')}")
    print(f"Executed:   {order.get('executedQty')}")
    print(f"Time:       {order.get('updateTime')}")


def main():
    args = parse_args()
    bot = create_bot_from_config()

    # Validate required params for each type
    if args.type == "LIMIT" and args.price is None:
        print("❌ Error: --price is required for LIMIT orders.")
        sys.exit(1)

    if args.type == "STOP_LIMIT" and (args.price is None or args.stop_price is None):
        print("❌ Error: --price and --stop_price are required for STOP_LIMIT orders.")
        sys.exit(1)

    # Pre-check notional to avoid Binance error -4164
    if args.type == "MARKET":
        check_min_notional(bot, args.symbol, args.quantity, price=None)
    elif args.type in ("LIMIT", "STOP_LIMIT"):
        check_min_notional(bot, args.symbol, args.quantity, price=args.price)

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
            print(f"❌ Unsupported order type: {args.type}")
            sys.exit(1)

        print_order_result(order)

    except BinanceAPIException as e:
        print("\n❌ Order rejected by Binance:")
        print(f"Code:    {e.code}")
        print(f"Message: {e.message}")

        # Special explanation for the error you got
        if e.code == -4164:
            print("\nThis means your order's notional (price × quantity) is < 100 USDT.")
            print("Binance Futures requires notional ≥ 100 USDT for opening a position.")
            print("👉 Increase quantity, or use a cheaper symbol (like ETHUSDT, XRPUSDT, etc.).")

    except BinanceRequestException as e:
        print("\n❌ Network / request error when talking to Binance:")
        print(e)

    except Exception as e:
        print("\n❌ Unexpected error:")
        print(e)


if __name__ == "__main__":
    main()
