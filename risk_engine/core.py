from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskEngineConfig:
    """Static controls for the MVP risk engine."""

    risk_percent: float
    daily_loss_cap_percent: float
    max_consecutive_losses: int = 3
    max_open_risk_percent: float = 0.0075
    max_leverage: float = 3.0


@dataclass(frozen=True)
class AccountState:
    """Minimal account state required for risk checks."""

    start_of_day_equity: float
    realized_pnl_today: float
    consecutive_losses: int = 0
    manual_kill_switch: bool = False


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    position_size: float
    reason: str


def calculate_position_size(
    balance: float,
    risk_percent: float,
    entry_price: float,
    stop_price: float,
    contract_multiplier: float = 1.0,
) -> float:
    """Position size based on account risk budget and stop distance.

    Formula:
    size = (balance * risk_percent) / (abs(entry - stop) * contract_multiplier)
    """

    stop_distance = abs(entry_price - stop_price)
    if stop_distance <= 0 or contract_multiplier <= 0:
        return 0.0

    risk_budget = balance * risk_percent
    if risk_budget <= 0:
        return 0.0

    size = risk_budget / (stop_distance * contract_multiplier)
    return max(0.0, round(size, 8))


class RiskEngine:
    """MVP policy engine for pre-trade risk validation."""

    def __init__(self, config: RiskEngineConfig) -> None:
        self.config = config

    def daily_loss_cap_reached(self, state: AccountState) -> bool:
        max_daily_loss = state.start_of_day_equity * self.config.daily_loss_cap_percent
        return abs(min(0.0, state.realized_pnl_today)) >= max_daily_loss

    def kill_switch_active(self, state: AccountState) -> bool:
        if state.manual_kill_switch:
            return True
        return state.consecutive_losses >= self.config.max_consecutive_losses

    def evaluate_trade(
        self,
        state: AccountState,
        entry_price: float,
        stop_price: float,
        contract_multiplier: float = 1.0,
    ) -> RiskDecision:
        if self.kill_switch_active(state):
            return RiskDecision(False, 0.0, "kill_switch_active")

        if self.daily_loss_cap_reached(state):
            return RiskDecision(False, 0.0, "daily_loss_cap_reached")

        size = calculate_position_size(
            balance=state.start_of_day_equity,
            risk_percent=self.config.risk_percent,
            entry_price=entry_price,
            stop_price=stop_price,
            contract_multiplier=contract_multiplier,
        )

        if size <= 0:
            return RiskDecision(False, 0.0, "invalid_position_size")

        return RiskDecision(True, size, "ok")
