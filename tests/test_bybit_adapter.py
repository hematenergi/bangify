import pytest

from exchange.base import Balance, OrderSide, OrderType, Position, Ticker
from exchange.bybit import BybitAdapter


@pytest.fixture()
def adapter():
    # Using dummy keys for structure testing; real tests need testnet keys
    return BybitAdapter(
        api_key="dummy_key",
        api_secret="dummy_secret",
        testnet=True,
    )


def test_adapter_initialization(adapter: BybitAdapter):
    assert adapter.api_key == "dummy_key"
    assert adapter.api_secret == "dummy_secret"
    assert adapter.testnet is True
    assert adapter.base_url == BybitAdapter.TESTNET_URL


def test_stringify_params(adapter: BybitAdapter):
    params = {"symbol": "BTCUSDT", "category": "linear"}
    result = adapter._stringify_params(params)
    # Should be sorted by key, concatenated key+value
    assert result == "categorylinearsymbolBTCUSDT"


def test_stringify_empty_params(adapter: BybitAdapter):
    assert adapter._stringify_params(None) == ""
    assert adapter._stringify_params({}) == ""


def test_balance_dataclass():
    b = Balance(coin="USDT", wallet_balance=1000.0, available_balance=800.0)
    assert b.coin == "USDT"
    assert b.wallet_balance == 1000.0
    assert b.available_balance == 800.0


def test_position_dataclass():
    p = Position(
        symbol="BTCUSDT",
        side="long",
        size=0.5,
        entry_price=50000.0,
        unrealised_pnl=100.0,
        leverage=5.0,
    )
    assert p.symbol == "BTCUSDT"
    assert p.side == "long"
    assert p.size == 0.5
    assert p.entry_price == 50000.0
    assert p.unrealised_pnl == 100.0
    assert p.leverage == 5.0


def test_ticker_dataclass():
    t = Ticker(
        symbol="BTCUSDT",
        bid=49990.0,
        ask=50010.0,
        last=50000.0,
        timestamp="2024-01-01T00:00:00Z",
    )
    assert t.symbol == "BTCUSDT"
    assert t.bid == 49990.0
    assert t.ask == 50010.0
    assert t.last == 50000.0


def test_order_sides():
    assert OrderSide.BUY.value == "Buy"
    assert OrderSide.SELL.value == "Sell"


def test_order_types():
    assert OrderType.MARKET.value == "Market"
    assert OrderType.LIMIT.value == "Limit"


@pytest.mark.skip(reason="Requires real testnet API keys")
def test_get_account_info_live():
    adapter = BybitAdapter(
        api_key="YOUR_TESTNET_KEY",
        api_secret="YOUR_TESTNET_SECRET",
        testnet=True,
    )
    info = adapter.get_account_info()
    assert info.total_equity >= 0
    assert isinstance(info.positions, list)
    assert isinstance(info.balances, list)


@pytest.mark.skip(reason="Requires real testnet API keys")
def test_get_positions_live():
    adapter = BybitAdapter(
        api_key="YOUR_TESTNET_KEY",
        api_secret="YOUR_TESTNET_SECRET",
        testnet=True,
    )
    positions = adapter.get_positions()
    assert isinstance(positions, list)


@pytest.mark.skip(reason="Requires real testnet API keys")
def test_get_ticker_live():
    adapter = BybitAdapter(
        api_key="YOUR_TESTNET_KEY",
        api_secret="YOUR_TESTNET_SECRET",
        testnet=True,
    )
    ticker = adapter.get_ticker("BTCUSDT")
    assert ticker.symbol == "BTCUSDT"
    assert ticker.last > 0
