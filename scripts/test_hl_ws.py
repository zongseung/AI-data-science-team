#!/usr/bin/env python3
"""Quick smoke test: connect to Hyperliquid WS, print 5 candle messages, then exit.

Usage:
    python scripts/test_hl_ws.py
    python scripts/test_hl_ws.py --coin ETH --interval 1m --count 10
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone


async def main(coin: str, interval: str, count: int) -> None:
    try:
        import websockets
    except ImportError:
        print("pip install websockets  # 먼저 설치하세요")
        sys.exit(1)

    url = "wss://api.hyperliquid.xyz/ws"
    print(f"Connecting to {url} ...")

    async with websockets.connect(url, ping_interval=None) as ws:
        print("Connected!")

        sub = {
            "method": "subscribe",
            "subscription": {"type": "candle", "coin": coin, "interval": interval},
        }
        await ws.send(json.dumps(sub))
        print(f"Subscribed: {coin} {interval}")

        received = 0
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if msg.get("channel") != "candle":
                print(f"  [{msg.get('channel', '?')}] {json.dumps(msg.get('data', ''))[:120]}")
                continue

            data = msg.get("data", {})
            received += 1

            # Pretty-print candle
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(
                f"  [{ts}] #{received} "
                f"coin={data.get('s')} i={data.get('i')} "
                f"candles={len(data.get('d', []))}"
            )
            for c in data.get("d", []):
                flag = " CLOSED" if c.get("closed") else ""
                print(
                    f"    O={c.get('o')} H={c.get('h')} "
                    f"L={c.get('l')} C={c.get('c')} "
                    f"V={c.get('v')}{flag}"
                )

            if received >= count:
                print(f"\n{count} messages received. Done.")
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hyperliquid WS smoke test")
    parser.add_argument("--coin", default="BTC")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()

    asyncio.run(main(args.coin, args.interval, args.count))
