"""Base types for exchange adapters."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class OrderSide(str, Enum):
    BUY = "Buy"
    SELL = "Sell"


class OrderType(str, Enum):
    MARKET = "Market"
    LIMIT = "Limit"


class OrderStatus(str, Enum):
    NEW = "New"
    PARTIALLY_FILLED = "PartiallyFilled"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"


@dataclass(frozen=True)
class Position:
    symbol: str
    side: str  # long | short
    size: float
    entry_price: float
    unrealised_pnl: float
    leverage: float


@dataclass(frozen=True)
class Balance:
    coin: str
    wallet_balance: float
    available_balance: float


@dataclass(frozen=True)
class Order:
    order_id: str
    symbol: str
    side: str
    order_type: str
    price: float | None
    qty: float
    filled_qty: float
    status: str
    created_at: str


@dataclass(frozen=True)
class Ticker:
    symbol: str
    bid: float
    ask: float
    last: float
    timestamp: str


@dataclass(frozen=True)
class AccountInfo:
    total_equity: float
    total_available_balance: float
    positions: list[Position]
    balances: list[Balance]


class ExchangeAdapter:
    """Abstract base for exchange adapters."""

    def get_account_info(self) -> AccountInfo:
        raise NotImplementedError

    def get_positions(self, symbol: str | None = None) -> list[Position]:
        raise NotImplementedError

    def get_balance(self, coin: str) -> Balance | None:
        raise NotImplementedError

    def get_ticker(self, symbol: str) -> Ticker:
        raise NotImplementedError

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
        raise NotImplementedError

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        raise NotImplementedError

    def get_order(self, symbol: str, order_id: str) -> Order:
        raise NotImplementedError

    def set_leverage(self, symbol: str, leverage: float) -> bool:
        raise NotImplementedError
