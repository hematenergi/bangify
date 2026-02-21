from risk_engine.core import AccountState, RiskEngine, RiskEngineConfig
from risk_engine.execution import ExecutionWrapper, ExposureState, PreTradeGuard, TradeIntent


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


def test_draft_order_requires_risk_guard_pass() -> None:
    wrapper = ExecutionWrapper(PreTradeGuard(_engine()))

    decision, draft = wrapper.draft_order(
        state=_state(),
        intent=_intent(leverage=10.0),
        exposure=ExposureState(),
    )

    assert decision.allowed is False
    assert decision.reason == "leverage_cap_exceeded"
    assert draft is None


def test_confirm_order_requires_explicit_confirm_text() -> None:
    wrapper = ExecutionWrapper(PreTradeGuard(_engine()))
    decision, draft = wrapper.draft_order(_state(), _intent(), ExposureState())

    assert decision.allowed is True
    assert draft is not None

    try:
        wrapper.confirm_order(draft, "yes")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert str(exc) == "confirmation_required"


def test_confirm_order_success() -> None:
    wrapper = ExecutionWrapper(PreTradeGuard(_engine()))
    decision, draft = wrapper.draft_order(_state(), _intent(), ExposureState())

    assert decision.allowed is True
    assert draft is not None

    confirmed = wrapper.confirm_order(draft, " confirm ")
    assert confirmed.draft.client_order_id.startswith("draft-")
    assert confirmed.confirmation.value == "CONFIRM"
