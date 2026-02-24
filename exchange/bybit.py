"""Bybit V5 REST API adapter."""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

import requests

from .base import (
    AccountInfo,
    Balance,
    ExchangeAdapter,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Ticker,
)


class BybitAdapter(ExchangeAdapter):
    """Bybit V5 REST API adapter for USDT perpetual futures."""

    BASE_URL = "https://api.bybit.com"
    TESTNET_URL = "https://api-testnet.bybit.com"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        account_type: str = "UNIFIED",
        recv_window: int = 5000,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = self.TESTNET_URL if testnet else self.BASE_URL
        self.account_type = account_type
        self.recv_window = recv_window
        self.session = requests.Session()

    def _sign(self, params: dict[str, Any], timestamp: int) -> str:
        """Generate signature for Bybit V5 API."""
        param_str = str(timestamp) + self.api_key + str(self.recv_window) + self._stringify_params(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            param_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _stringify_params(self, params: dict[str, Any] | None) -> str:
        if not params:
            return ""
        sorted_items = sorted(params.items(), key=lambda x: x[0])
        return "".join(f"{k}{v}" for k, v in sorted_items if v is not None and v != "")

    def _headers(self, params: dict[str, Any] | None = None) -> dict[str, str]:
        ts = int(time.time() * 1000)
        sign = self._sign(params or {}, ts)
        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": str(ts),
            "X-BAPI-SIGN": sign,
            "X-BAPI-RECV-WINDOW": str(self.recv_window),
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        headers = self._headers(params)
        if method.upper() == "GET":
            resp = self.session.get(url, headers=headers, params=params, timeout=10)
        else:
            resp = self.session.post(url, headers=headers, json=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("retCode", 0) != 0:
            raise RuntimeError(f"Bybit API error: {data}")
        return data.get("result", {})

    def get_account_info(self) -> AccountInfo:
        result = self._request("GET", "/v5/account/wallet-balance", {"accountType": self.account_type})
        positions = self.get_positions()
        balances: list[Balance] = []

        total_equity = 0.0
        total_available = 0.0

        for coin_data in result.get("list", []):
            for coin in coin_data.get("coin", []):
                b = Balance(
                    coin=coin["coin"],
                    wallet_balance=float(coin.get("walletBalance", 0)),
                    available_balance=float(coin.get("availableToWithdraw", 0)),
                )
                balances.append(b)
                total_equity += b.wallet_balance
                total_available += b.available_balance

        return AccountInfo(
            total_equity=total_equity,
            total_available_balance=total_available,
            positions=positions,
            balances=balances,
        )

    def get_positions(self, symbol: str | None = None) -> list[Position]:
        params: dict[str, Any] = {"category": "linear", "settleCoin": "USDT"}
        if symbol:
            params["symbol"] = symbol
        result = self._request("GET", "/v5/position/list", params)
        positions: list[Position] = []

        for item in result.get("list", []):
            pos = Position(
                symbol=item["symbol"],
                side=item["side"],
                size=float(item.get("size", 0)),
                entry_price=float(item.get("avgPrice", 0)),
                unrealised_pnl=float(item.get("unrealisedPnl", 0)),
                leverage=float(item.get("leverage", 1)),
            )
            positions.append(pos)

        return positions

    def get_balance(self, coin: str) -> Balance | None:
        info = self.get_account_info()
        for b in info.balances:
            if b.coin == coin:
                return b
        return None

    def get_ticker(self, symbol: str) -> Ticker:
        result = self._request("GET", "/v5/market/tickers", {"category": "linear", "symbol": symbol})
        if not result.get("list"):
            raise ValueError(f"No ticker data for {symbol}")

        item = result["list"][0]
        return Ticker(
            symbol=item["symbol"],
            bid=float(item.get("bid1Price", 0)),
            ask=float(item.get("ask1Price", 0)),
            last=float(item.get("lastPrice", 0)),
            timestamp=item.get("time", ""),
        )

    def set_leverage(self, symbol: str, leverage: float) -> bool:
        params = {
            "category": "linear",
            "symbol": symbol,
            "buyLeverage": str(leverage),
            "sellLeverage": str(leverage),
        }
        result = self._request("POST", "/v5/position/set-leverage", params)
        return result.get("retMsg", "") == "OK" or "leverage not modified" in result.get("retMsg", "").lower()

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: float,
        price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        leverage: float | None = None,
        **kwargs: Any,
    ) -> Order:
        if leverage:
            self.set_leverage(symbol, leverage)

        params: dict[str, Any] = {
            "category": "linear",
            "symbol": symbol,
            "side": side.value,
            "orderType": order_type.value,
            "qty": str(qty),
        }
        if price:
            params["price"] = str(price)
        if stop_loss:
            params["stopLoss"] = str(stop_loss)
        if take_profit:
            params["takeProfit"] = str(take_profit)
        params.update(kwargs)

        result = self._request("POST", "/v5/order/create", params)
        order_id = result.get("orderId", "")
        return self.get_order(symbol, order_id)

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        params = {"category": "linear", "symbol": symbol, "orderId": order_id}
        result = self._request("POST", "/v5/order/cancel", params)
        return result.get("retMsg", "") == "OK"

    def get_order(self, symbol: str, order_id: str) -> Order:
        params = {"category": "linear", "symbol": symbol, "orderId": order_id}
        result = self._request("GET", "/v5/order/realtime", params)
        if not result.get("list"):
            raise ValueError(f"Order {order_id} not found")

        item = result["list"][0]
        return Order(
            order_id=item["orderId"],
            symbol=item["symbol"],
            side=item["side"],
            order_type=item["orderType"],
            price=float(item.get("price", 0)) if item.get("price") else None,
            qty=float(item.get("qty", 0)),
            filled_qty=float(item.get("cumExecQty", 0)),
            status=item.get("orderStatus", OrderStatus.NEW.value),
            created_at=item.get("createdTime", ""),
        )
