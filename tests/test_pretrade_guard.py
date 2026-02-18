from risk_engine.core import AccountState, RiskEngine, RiskEngineConfig
from risk_engine.execution import ExposureState, PreTradeGuard, TradeIntent


def _engine() -> RiskEngine:
    cfg = RiskEngineConfig(
        risk_percent=0.0025,
        daily_loss_cap_percent=0.01,
        max_consecutive_losses=3,
        max_open_risk_percent=0.0075,
        max_leverage=3.0,
    )
    return RiskEngine(cfg)


def _state() -> AccountState:
    return AccountState(start_of_day_equity=1000, realized_pnl_today=0)


def _intent(**kw) -> TradeIntent:
    base = dict(symbol="BTCUSDT", side="long", entry_price=100.0, stop_price=99.0, leverage=2.0)
    base.update(kw)
    return TradeIntent(**base)


def test_blocks_leverage_cap_exceeded() -> None:
    guard = PreTradeGuard(_engine())
    dec = guard.evaluate(_state(), _intent(leverage=5.0), ExposureState())
    assert dec.allowed is False
    assert dec.reason == "leverage_cap_exceeded"


def test_blocks_duplicate_symbol_position() -> None:
    guard = PreTradeGuard(_engine())
    dec = guard.evaluate(_state(), _intent(), ExposureState(has_open_position_same_symbol=True))
    assert dec.allowed is False
    assert dec.reason == "duplicate_symbol_position"


def test_blocks_max_open_risk_reached() -> None:
    guard = PreTradeGuard(_engine())
    dec = guard.evaluate(_state(), _intent(), ExposureState(open_risk_percent=0.01))
    assert dec.allowed is False
    assert dec.reason == "max_open_risk_reached"


def test_allows_valid_trade() -> None:
    guard = PreTradeGuard(_engine())
    dec = guard.evaluate(_state(), _intent(), ExposureState())
    assert dec.allowed is True
    assert dec.reason == "ok"
    assert dec.suggested_size > 0
