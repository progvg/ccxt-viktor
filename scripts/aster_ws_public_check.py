#!/usr/bin/env python3

import os
import sys
import asyncio


def add_local_ccxt_to_path():
    root = os.path.dirname(os.path.abspath(__file__))
    python_dir = os.path.join(os.path.dirname(root), 'python')
    if os.path.isdir(python_dir):
        sys.path.insert(0, python_dir)


async def main():
    add_local_ccxt_to_path()
    from ccxt import pro as ccxtpro  # noqa: E402

    # args: symbol [max_events]
    cli_symbol = sys.argv[1] if len(sys.argv) > 1 else None
    max_events = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    ex = ccxtpro.aster()
    print('Using exchange (pro):', ex.id)

    # load markets & choose symbol
    await ex.load_markets()
    preferred = [cli_symbol] if cli_symbol else [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'BTC/USDC', 'BNB/BTC', 'BTC/USD'
    ]
    symbol = None
    for s in preferred:
        if s and s in ex.markets:
            symbol = s
            break
    if symbol is None:
        for m in ex.markets.values():
            if m.get('spot'):
                symbol = m['symbol']
                break
    if symbol is None:
        print('No spot symbols found to test.')
        await ex.close()
        return
    print('Testing symbol:', symbol)

    # concurrently watch trades, ticker, and order book
    async def watch_trades_task():
        count = 0
        while count < max_events:
            trades = await ex.watch_trades(symbol)
            if trades:
                t = trades[-1]
                print(f"trades[{count+1}/{max_events}]: id={t.get('id')} price={t.get('price')} amount={t.get('amount')} ts={t.get('timestamp')}")
                count += 1

    async def watch_ticker_task():
        count = 0
        while count < max_events:
            ticker = await ex.watch_ticker(symbol)
            print(f"ticker[{count+1}/{max_events}]: last={ticker.get('last')} bid={ticker.get('bid')} ask={ticker.get('ask')}")
            count += 1

    async def watch_order_book_task():
        count = 0
        while count < max_events:
            ob = await ex.watch_order_book(symbol)
            best_bid = ob['bids'][0][0] if ob.get('bids') else None
            best_ask = ob['asks'][0][0] if ob.get('asks') else None
            print(f"orderbook[{count+1}/{max_events}]: bestBid={best_bid} bestAsk={best_ask} bids={len(ob.get('bids', []))} asks={len(ob.get('asks', []))}")
            count += 1

    # run with timeout to avoid hanging forever
    timeout_sec = int(os.environ.get('ASTER_WS_TIMEOUT', '60'))
    try:
        await asyncio.wait_for(
            asyncio.gather(
                watch_trades_task(),
                watch_ticker_task(),
                watch_order_book_task(),
            ),
            timeout=timeout_sec,
        )
    except asyncio.TimeoutError:
        print(f"Timed out after {timeout_sec}s (partial results above if any)")
    finally:
        await ex.close()
        print('Done.')


if __name__ == '__main__':
    # Ensure SelectorEventLoop on Windows (required by aiodns/aiohttp)
    try:
        import platform
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass
    asyncio.run(main())
