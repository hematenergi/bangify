import json
import tempfile
from pathlib import Path

import pytest

from risk_engine.core import AccountState, RiskConfig, RiskEngine
from risk_engine.execution import (
    DraftOrder,
    ExecutionDecision,
    ExecutionWrapper,
    ExposureState,
    PreTradeGuard,
    TradeIntent,
)
from risk_engine.journal import Journal


@pytest.fixture()
def journal():
    with tempfile.TemporaryDirectory() as td:
        yield Journal(log_dir=td)


@pytest.fixture()
def risk_engine():
    cfg = RiskConfig(
        max_leverage=5,
        max_risk_per_trade_pct=1.0,
        max_open_risk_percent=5.0,
        min_stop_distance_pct=0.3,
    )
    return RiskEngine(config=cfg)


@pytest.fixture()
def guard(risk_engine: RiskEngine):
    return PreTradeGuard(risk_engine)


@pytest.fixture()
def wrapper(guard: PreTradeGuard, journal: Journal):
    return ExecutionWrapper(guard=guard, journal=journal)


def test_journal_records_allowed_decision(wrapper: ExecutionWrapper, journal: Journal, risk_engine: RiskEngine):
    state = AccountState(balance=10_000.0, equity=10_000.0)
    intent = TradeIntent(
        symbol="BTCUSDT",
        side="long",
        entry_price=100.0,
        stop_price=99.0,
        leverage=1.0,
    )
    exposure = ExposureState()

    decision, draft = wrapper.draft_order(state=state, intent=intent, exposure=exposure)

    assert decision.allowed is True
    assert draft is not None
    assert journal.pending_count() >= 2  # decision + draft

    # Verify decision entry structure
    decision_entries = [e for e in journal._buffer if e.event_type == "decision"]
    assert len(decision_entries) == 1

    de = decision_entries[0]
    assert de.data["allowed"] is True
    assert de.data["intent"]["symbol"] == "BTCUSDT"


def test_journal_records_rejected_decision(wrapper: ExecutionWrapper, journal: Journal):
    state = AccountState(balance=10_000.0, equity=10_000.0)
    intent = TradeIntent(
        symbol="BTCUSDT",
        side="invalid_side",  # invalid
        entry_price=100.0,
        stop_price=99.0,
        leverage=1.0,
    )
    exposure = ExposureState()

    decision, draft = wrapper.draft_order(state=state, intent=intent, exposure=exposure)

    assert decision.allowed is False
    assert draft is None
    assert journal.pending_count() >= 1


def test_journal_records_confirmation(wrapper: ExecutionWrapper, journal: Journal):
    state = AccountState(balance=10_000.0, equity=10_000.0)
    intent = TradeIntent(
        symbol="BTCUSDT",
        side="long",
        entry_price=100.0,
        stop_price=99.0,
        leverage=1.0,
    )
    exposure = ExposureState()

    decision, draft = wrapper.draft_order(state=state, intent=intent, exposure=exposure)
    assert draft is not None

    confirmed = wrapper.confirm_order(draft, "CONFIRM")
    assert confirmed is not None

    assert journal.pending_count() >= 3  # decision + draft + confirmation

    confirmation_entries = [e for e in journal._buffer if e.event_type == "confirmation"]
    assert len(confirmation_entries) == 1


def test_journal_flush_to_file(journal: Journal):
    # Add some entries
    journal.record("custom_event", {"foo": 1})
    journal.record("another_event", {"bar": 2})

    assert journal.pending_count() == 2

    path = journal.flush_to_file()
    assert Path(path).exists()

    # Read back and verify
    with open(path, "r") as f:
        lines = f.readlines()

    assert len(lines) == 2
    entry1 = json.loads(lines[0])
    assert entry1["event_type"] == "custom_event"
    assert entry1["data"]["foo"] == 1

    # Buffer should be cleared after flush
    assert journal.pending_count() == 0


def test_journal_records_rejection_on_invalid_confirmation(wrapper: ExecutionWrapper, journal: Journal):
    state = AccountState(balance=10_000.0, equity=10_000.0)
    intent = TradeIntent(
        symbol="BTCUSDT",
        side="long",
        entry_price=100.0,
        stop_price=99.0,
        leverage=1.0,
    )
    exposure = ExposureState()

    decision, draft = wrapper.draft_order(state=state, intent=intent, exposure=exposure)
    assert draft is not None

    with pytest.raises(ValueError):
        wrapper.confirm_order(draft, "REJECT")  # Invalid confirmation text

    # Should have recorded a rejection
    rejection_entries = [e for e in journal._buffer if e.event_type == "rejection"]
    assert len(rejection_entries) == 1
    assert rejection_entries[0].data["reason"] == "confirmation_required"
