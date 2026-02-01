#!/usr/bin/env python3

import os
import sys
import time


def add_local_ccxt_to_path():
    root = os.path.dirname(os.path.abspath(__file__))
    python_dir = os.path.join(os.path.dirname(root), 'python')
    if os.path.isdir(python_dir):
        sys.path.insert(0, python_dir)


def pick_symbol(markets, preferred, market_type):
    for s in preferred:
        if s and s in markets:
            return s
    for m in markets.values():
        if market_type == 'swap' and m.get('swap'):
            return m['symbol']
        if market_type == 'spot' and m.get('spot'):
            return m['symbol']
    return None


def run_test(market_type, cli_symbol=None):
    import ccxt  # noqa: E402

    ex = ccxt.orangex({'options': {'defaultType': market_type}})
    print(f"=== {market_type.upper()} ===")
    print(f"Using exchange: {ex.id}")

    try:
        server_time = ex.fetch_time()
        if server_time is not None:
            print(f"fetch_time: {server_time} ({time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(server_time/1000))})")
        else:
            print("fetch_time: None")
    except Exception as e:
        print(f"fetch_time error: {e}")

    try:
        markets = ex.load_markets()
        print(f"load_markets: {len(markets)} markets loaded")
    except Exception as e:
        print(f"load_markets error: {e}")
        return

    if market_type == 'swap':
        preferred = [cli_symbol] if cli_symbol else [
            'BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT'
        ]
    else:
        preferred = [cli_symbol] if cli_symbol else [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'BTC/USDC', 'BTC/USD'
        ]
    symbol = pick_symbol(markets, preferred, market_type)
    if symbol is None:
        print(f"No {market_type} symbols found to test.")
        return
    print(f"Testing symbol: {symbol}")

    try:
        ob = ex.fetch_order_book(symbol, limit=10)
        print(f"fetch_order_book: bids={len(ob.get('bids', []))}, asks={len(ob.get('asks', []))}")
    except Exception as e:
        print(f"fetch_order_book error: {e}")

    try:
        ticker = ex.fetch_ticker(symbol)
        print(f"fetch_ticker: last={ticker.get('last')}, high={ticker.get('high')}, low={ticker.get('low')}")
    except Exception as e:
        print(f"fetch_ticker error: {e}")


def main():
    add_local_ccxt_to_path()

    cli_symbol = sys.argv[1] if len(sys.argv) > 1 else None
    if cli_symbol:
        market_type = 'swap' if (':' in cli_symbol or 'PERPETUAL' in cli_symbol) else 'spot'
        run_test(market_type, cli_symbol)
    else:
        run_test('spot')
        run_test('swap')

    print("Done.")


if __name__ == '__main__':
    main()
