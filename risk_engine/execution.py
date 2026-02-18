from __future__ import annotations

from dataclasses import dataclass

from .core import AccountState, RiskEngine


@dataclass(frozen=True)
class TradeIntent:
    symbol: str
    side: str  # long | short
    entry_price: float
    stop_price: float
    leverage: float
    contract_multiplier: float = 1.0


@dataclass(frozen=True)
class ExposureState:
    open_risk_percent: float = 0.0
    has_open_position_same_symbol: bool = False


@dataclass(frozen=True)
class ExecutionDecision:
    allowed: bool
    reason: str
    suggested_size: float = 0.0


class PreTradeGuard:
    """Execution-side safety checks layered on top of RiskEngine."""

    def __init__(self, risk_engine: RiskEngine) -> None:
        self.risk_engine = risk_engine

    def evaluate(
        self,
        state: AccountState,
        intent: TradeIntent,
        exposure: ExposureState,
    ) -> ExecutionDecision:
        if intent.side not in {"long", "short"}:
            return ExecutionDecision(False, "invalid_side")

        if intent.leverage <= 0:
            return ExecutionDecision(False, "invalid_leverage")

        if intent.leverage > self.risk_engine.config.max_leverage:
            return ExecutionDecision(False, "leverage_cap_exceeded")

        if exposure.has_open_position_same_symbol:
            return ExecutionDecision(False, "duplicate_symbol_position")

        if exposure.open_risk_percent >= self.risk_engine.config.max_open_risk_percent:
            return ExecutionDecision(False, "max_open_risk_reached")

        rd = self.risk_engine.evaluate_trade(
            state=state,
            entry_price=intent.entry_price,
            stop_price=intent.stop_price,
            contract_multiplier=intent.contract_multiplier,
        )

        if not rd.allowed:
            return ExecutionDecision(False, rd.reason)

        return ExecutionDecision(True, "ok", suggested_size=rd.position_size)
