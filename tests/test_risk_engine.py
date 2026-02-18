from risk_engine import (
    AccountState,
    RiskEngine,
    RiskEngineConfig,
    calculate_position_size,
)


def test_position_size_by_risk_percent():
    size = calculate_position_size(
        balance=10_000,
        risk_percent=0.01,
        entry_price=100,
        stop_price=95,
    )
    assert size == 20.0


def test_position_size_zero_when_no_stop_distance():
    size = calculate_position_size(
        balance=10_000,
        risk_percent=0.01,
        entry_price=100,
        stop_price=100,
    )
    assert size == 0.0


def test_daily_loss_cap_blocks_new_trade():
    engine = RiskEngine(RiskEngineConfig(risk_percent=0.01, daily_loss_cap_percent=0.03))
    state = AccountState(start_of_day_equity=10_000, realized_pnl_today=-350)

    decision = engine.evaluate_trade(state=state, entry_price=100, stop_price=95)

    assert not decision.allowed
    assert decision.reason == "daily_loss_cap_reached"


def test_kill_switch_blocks_new_trade():
    engine = RiskEngine(
        RiskEngineConfig(
            risk_percent=0.01,
            daily_loss_cap_percent=0.1,
            max_consecutive_losses=3,
        )
    )
    state = AccountState(
        start_of_day_equity=10_000,
        realized_pnl_today=-100,
        consecutive_losses=3,
    )

    decision = engine.evaluate_trade(state=state, entry_price=100, stop_price=95)

    assert not decision.allowed
    assert decision.reason == "kill_switch_active"


def test_manual_kill_switch_blocks_new_trade():
    engine = RiskEngine(RiskEngineConfig(risk_percent=0.01, daily_loss_cap_percent=0.1))
    state = AccountState(
        start_of_day_equity=10_000,
        realized_pnl_today=0,
        manual_kill_switch=True,
    )

    decision = engine.evaluate_trade(state=state, entry_price=100, stop_price=95)

    assert not decision.allowed
    assert decision.reason == "kill_switch_active"
