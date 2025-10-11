#!/usr/bin/env python3

import os
import sys
import time


def add_local_ccxt_to_path():
    root = os.path.dirname(os.path.abspath(__file__))
    python_dir = os.path.join(os.path.dirname(root), 'python')
    # if script is cloned into project root's scripts/, python/ is sibling
    if os.path.isdir(python_dir):
        sys.path.insert(0, python_dir)


def main():
    add_local_ccxt_to_path()
    import ccxt  # noqa: E402\n    print("ccxt file:", getattr(ccxt, "__file__", None))\n    print("sys.path[0]:", sys.path[0])

    ex = ccxt.aster()
    print(f"Using exchange: {ex.id}")

    # server time
    try:
        server_time = ex.fetch_time()
        print(f"fetch_time: {server_time} ({time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(server_time/1000))})")
    except Exception as e:
        print(f"fetch_time error: {e}")

    # markets
    try:
        markets = ex.load_markets()
        print(f"load_markets: {len(markets)} markets loaded")
    except Exception as e:
        print(f"load_markets error: {e}")
        return

    # symbol from argv or auto-select
    cli_symbol = sys.argv[1] if len(sys.argv) > 1 else None
    preferred = [cli_symbol] if cli_symbol else [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'BTC/USDC', 'BNB/BTC', 'BTC/USD'
    ]
    symbol = None
    for s in preferred:
        if s and s in markets:
            symbol = s
            break
    if symbol is None:
        for m in markets.values():
            if m.get('spot'):
                symbol = m['symbol']
                break
    if symbol is None:
        print("No spot symbols found to test.")
        return
    print(f"Testing symbol: {symbol}")

    # order book
    try:
        ob = ex.fetch_order_book(symbol, limit=10)
        print(f"fetch_order_book: bids={len(ob.get('bids', []))}, asks={len(ob.get('asks', []))}")
    except Exception as e:
        print(f"fetch_order_book error: {e}")

    # trades
    try:
        trades = ex.fetch_trades(symbol, limit=5)
        print(f"fetch_trades: got {len(trades)} trades; last id={trades[-1]['id'] if trades else 'n/a'}")
    except Exception as e:
        print(f"fetch_trades error: {e}")

    # ticker
    try:
        ticker = ex.fetch_ticker(symbol)
        print(f"fetch_ticker: last={ticker.get('last')}, high={ticker.get('high')}, low={ticker.get('low')}")
    except Exception as e:
        print(f"fetch_ticker error: {e}")

    # ohlcv
    try:
        ohlcv = ex.fetch_ohlcv(symbol, timeframe='1m', limit=5)
        print(f"fetch_ohlcv: got {len(ohlcv)} candles; last ts={ohlcv[-1][0] if ohlcv else 'n/a'}")
    except Exception as e:
        print(f"fetch_ohlcv error: {e}")

    # all tickers
    try:
        tickers = ex.fetch_tickers()
        print(f"fetch_tickers: got {len(tickers)} symbols")
    except Exception as e:
        print(f"fetch_tickers error: {e}")

    # raw bookTicker
    try:
        bt = ex.public_get_ticker_bookticker({'symbol': ex.market_id(symbol)})
        first = bt[0] if isinstance(bt, list) and bt else bt
        print(f"raw bookTicker: bid={first.get('bidPrice')} ask={first.get('askPrice')}")
    except Exception as e:
        print(f"raw bookTicker error: {e}")

    print("Done.")


if __name__ == '__main__':
    main()

