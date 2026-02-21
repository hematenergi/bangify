from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

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


@dataclass(frozen=True)
class DraftOrder:
    intent: TradeIntent
    size: float
    client_order_id: str


@dataclass(frozen=True)
class ConfirmationToken:
    value: str


@dataclass(frozen=True)
class ConfirmedOrder:
    draft: DraftOrder
    confirmation: ConfirmationToken


class ExecutionWrapper:
    """D3 scaffold: build draft order, require explicit pre-trade confirmation."""

    def __init__(self, guard: PreTradeGuard) -> None:
        self.guard = guard

    def draft_order(
        self,
        state: AccountState,
        intent: TradeIntent,
        exposure: ExposureState,
    ) -> tuple[ExecutionDecision, DraftOrder | None]:
        decision = self.guard.evaluate(state=state, intent=intent, exposure=exposure)
        if not decision.allowed:
            return decision, None

        draft = DraftOrder(
            intent=intent,
            size=decision.suggested_size,
            client_order_id=f"draft-{uuid4().hex[:12]}",
        )
        return decision, draft

    def confirm_order(
        self,
        draft: DraftOrder | None,
        confirmation_text: str,
    ) -> ConfirmedOrder:
        if draft is None:
            raise ValueError("draft_required")

        normalized = confirmation_text.strip().upper()
        if normalized != "CONFIRM":
            raise ValueError("confirmation_required")

        return ConfirmedOrder(draft=draft, confirmation=ConfirmationToken(value=normalized))
