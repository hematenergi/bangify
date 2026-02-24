"""WebSocket price feed for Bybit."""
from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

try:
    import websockets
except ImportError:
    websockets = None

from .base import Ticker


class BybitWebSocket:
    """Bybit public WebSocket for real-time ticker updates."""

    WS_PUBLIC_URL = "wss://stream.bybit.com/v5/public/linear"
    WS_TESTNET_URL = "wss://stream-testnet.bybit.com/v5/public/linear"

    def __init__(
        self,
        testnet: bool = False,
        on_ticker: Callable[[Ticker], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        if websockets is None:
            raise ImportError("websockets library is required. Install with: pip install websockets")
        self.testnet = testnet
        self.ws_url = self.WS_TESTNET_URL if testnet else self.WS_PUBLIC_URL
        self.on_ticker = on_ticker
        self.on_error = on_error
        self._ws: Any = None
        self._running = False

    async def connect(self) -> None:
        self._ws = await websockets.connect(self.ws_url)
        self._running = True

    async def subscribe_ticker(self, symbol: str) -> None:
        if not self._ws:
            raise RuntimeError("WebSocket not connected")
        msg = {
            "op": "subscribe",
            "args": [f"tickers.{symbol}"],
        }
        await self._ws.send(json.dumps(msg))

    async def listen(self) -> None:
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        try:
            async for message in self._ws:
                data = json.loads(message)
                await self._handle_message(data)
        except Exception as e:
            if self.on_error:
                self.on_error(e)
            raise

    async def _handle_message(self, data: dict[str, Any]) -> None:
        topic = data.get("topic", "")
        if not topic.startswith("tickers."):
            return

        payload = data.get("data", {})
        if not payload:
            return

        ticker = Ticker(
            symbol=payload.get("symbol", ""),
            bid=float(payload.get("bid1Price", 0)),
            ask=float(payload.get("ask1Price", 0)),
            last=float(payload.get("lastPrice", 0)),
            timestamp=str(payload.get("time", "")),
        )

        if self.on_ticker:
            self.on_ticker(ticker)

    async def close(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def run_forever(self, symbols: list[str]) -> None:
        """Connect, subscribe, and listen indefinitely."""
        await self.connect()
        for symbol in symbols:
            await self.subscribe_ticker(symbol)
        await self.listen()


async def example_usage():
    def on_ticker(t: Ticker) -> None:
        print(f"[TICKER] {t.symbol} last={t.last} bid={t.bid} ask={t.ask}")

    def on_error(e: Exception) -> None:
        print(f"[ERROR] {e}")

    ws = BybitWebSocket(testnet=True, on_ticker=on_ticker, on_error=on_error)
    try:
        await ws.run_forever(["BTCUSDT", "ETHUSDT"])
    except KeyboardInterrupt:
        pass
    finally:
        await ws.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
