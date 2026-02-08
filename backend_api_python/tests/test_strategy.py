# Settlement Arbitrage Strategy - Strategy Module Unit Tests
# 结算价差套利策略 - 策略核心逻辑单元测试

"""
Unit tests for strategy.py covering:
- StrategyState transitions
- Signal generation (BUY_L1, BUY_L2, ALERT, SELL_CLOSE)
- Base price setting at watch_start
- Entry condition checking with thresholds
- Alert deduplication
- Day open close logic
- Multi-symbol support
- New day transition handling
- Edge cases and boundary conditions
"""

import unittest
from datetime import datetime, date, time, timedelta
from unittest.mock import MagicMock, patch

from app.strategies.settlement_arbitrage.config import StrategyConfig, RiskConfig
from app.strategies.settlement_arbitrage.data_handler import MinuteBar
from app.strategies.settlement_arbitrage.strategy import (
    SettlementArbitrageStrategy,
    StrategyState,
    SignalType,
    Signal,
    SymbolState,
)


def make_bar(symbol: str, dt: datetime, close: float, volume: float = 100) -> MinuteBar:
    """Helper to create a MinuteBar for testing."""
    return MinuteBar(
        symbol=symbol,
        dt=dt,
        open_price=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=volume,
    )


class TestSymbolState(unittest.TestCase):
    """Tests for SymbolState dataclass."""

    def test_initial_state(self):
        """SymbolState should start with IDLE and no position."""
        ss = SymbolState(symbol='IM0')
        self.assertEqual(ss.state, StrategyState.IDLE)
        self.assertIsNone(ss.base_price)
        self.assertFalse(ss.has_position)
        self.assertEqual(ss.total_quantity, 0)
        self.assertEqual(ss.avg_entry_price, 0.0)

    def test_has_position_property(self):
        """has_position should return True only for POSITION_1 and POSITION_2."""
        ss = SymbolState(symbol='IM0')

        ss.state = StrategyState.IDLE
        self.assertFalse(ss.has_position)

        ss.state = StrategyState.WATCHING
        self.assertFalse(ss.has_position)

        ss.state = StrategyState.POSITION_1
        self.assertTrue(ss.has_position)

        ss.state = StrategyState.POSITION_2
        self.assertTrue(ss.has_position)

        ss.state = StrategyState.CLOSING
        self.assertFalse(ss.has_position)

    def test_total_quantity(self):
        """total_quantity should sum all entry quantities."""
        ss = SymbolState(symbol='IM0')
        ss.entry_quantities = [1, 2, 3]
        self.assertEqual(ss.total_quantity, 6)

    def test_avg_entry_price(self):
        """avg_entry_price should be cost-weighted average."""
        ss = SymbolState(symbol='IM0')
        ss.entry_prices = [5800, 5700]
        ss.entry_quantities = [1, 2]
        # (5800*1 + 5700*2) / (1+2) = 17200/3 ≈ 5733.33
        self.assertAlmostEqual(ss.avg_entry_price, 5733.33, places=1)

    def test_avg_entry_price_empty(self):
        """avg_entry_price should return 0 when no entries."""
        ss = SymbolState(symbol='IM0')
        self.assertEqual(ss.avg_entry_price, 0.0)

    def test_reset_daily(self):
        """reset_daily should clear all daily state."""
        ss = SymbolState(symbol='IM0')
        ss.state = StrategyState.WATCHING
        ss.base_price = 5900
        ss.current_vwap = 5850
        ss.entry_prices = [5800]
        ss.entry_quantities = [1]
        ss.entry_levels = [1]
        ss.today_signals = [MagicMock()]

        ss.reset_daily()

        self.assertEqual(ss.state, StrategyState.IDLE)
        self.assertIsNone(ss.base_price)
        self.assertIsNone(ss.current_vwap)
        self.assertEqual(ss.entry_prices, [])
        self.assertEqual(ss.entry_quantities, [])
        self.assertEqual(ss.entry_levels, [])
        self.assertEqual(ss.today_signals, [])


class TestSignal(unittest.TestCase):
    """Tests for Signal dataclass."""

    def test_signal_to_dict(self):
        """Signal.to_dict should return all fields."""
        sig = Signal(
            signal_type=SignalType.BUY_L1,
            symbol='IM0',
            price=5840,
            base_price=5900,
            drop_pct=-0.0102,
            vwap=5870,
            level=1,
            quantity=1,
            timestamp=datetime(2026, 2, 9, 14, 35),
        )
        d = sig.to_dict()
        self.assertEqual(d['signal_type'], 'buy_level_1')
        self.assertEqual(d['symbol'], 'IM0')
        self.assertEqual(d['price'], 5840)
        self.assertEqual(d['base_price'], 5900)
        self.assertEqual(d['drop_pct'], -0.0102)
        self.assertEqual(d['vwap'], 5870)
        self.assertEqual(d['level'], 1)
        self.assertEqual(d['quantity'], 1)
        self.assertIn('2026-02-09', d['timestamp'])


class TestStrategyInitialization(unittest.TestCase):
    """Tests for SettlementArbitrageStrategy initialization."""

    def test_default_initialization(self):
        """Strategy should initialize with default config."""
        config = StrategyConfig(symbols=['IM0', 'IC0'])
        strategy = SettlementArbitrageStrategy(config=config)

        state = strategy.state
        self.assertEqual(state['IM0'], 'idle')
        self.assertEqual(state['IC0'], 'idle')

    def test_custom_vwap_calculator(self):
        """Strategy should accept custom VWAP calculator."""
        mock_vwap = MagicMock()
        config = StrategyConfig(symbols=['IM0'])
        strategy = SettlementArbitrageStrategy(config=config, vwap_calculator=mock_vwap)
        self.assertEqual(strategy.vwap_calculator, mock_vwap)

    def test_get_symbol_state_existing(self):
        """get_symbol_state should return SymbolState for tracked symbols."""
        config = StrategyConfig(symbols=['IM0'])
        strategy = SettlementArbitrageStrategy(config=config)
        ss = strategy.get_symbol_state('IM0')
        self.assertIsNotNone(ss)
        self.assertEqual(ss.symbol, 'IM0')

    def test_get_symbol_state_unknown(self):
        """get_symbol_state should return None for unknown symbols."""
        config = StrategyConfig(symbols=['IM0'])
        strategy = SettlementArbitrageStrategy(config=config)
        ss = strategy.get_symbol_state('IF0')
        self.assertIsNone(ss)


class TestBasePriceSetting(unittest.TestCase):
    """Tests for base price setting at watch_start."""

    def setUp(self):
        self.config = StrategyConfig(
            symbols=['IM0'],
            threshold_1=0.01,
            threshold_2=0.02,
        )
        self.strategy = SettlementArbitrageStrategy(config=self.config)

    def test_base_price_set_at_1430(self):
        """Base price should be set at the first bar at/after 14:30."""
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar)

        ss = self.strategy.get_symbol_state('IM0')
        self.assertEqual(ss.base_price, 5900)
        self.assertEqual(ss.state, StrategyState.WATCHING)

    def test_base_price_set_only_once(self):
        """Base price should not change after first bar in watch period."""
        bar1 = make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar1)

        bar2 = make_bar('IM0', datetime(2026, 2, 9, 14, 31), 5910)
        self.strategy.on_bar(bar2)

        ss = self.strategy.get_symbol_state('IM0')
        self.assertEqual(ss.base_price, 5900)  # Should remain 5900

    def test_no_base_price_before_watch(self):
        """Base price should NOT be set before 14:30."""
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 29), 5900)
        self.strategy.on_bar(bar)

        ss = self.strategy.get_symbol_state('IM0')
        self.assertIsNone(ss.base_price)
        self.assertEqual(ss.state, StrategyState.IDLE)


class TestEntryConditions(unittest.TestCase):
    """Tests for entry condition checking."""

    def setUp(self):
        self.config = StrategyConfig(
            symbols=['IM0'],
            threshold_1=0.01,   # 1%
            threshold_2=0.02,   # 2%
            alert_threshold=0.008,  # 0.8%
            position_size_1=1,
            position_size_2=1,
        )
        self.strategy = SettlementArbitrageStrategy(config=self.config)
        # Set base price
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar)

    def test_level1_entry_exact_threshold(self):
        """L1 entry at exactly 1% drop: 5900 * 0.99 = 5841."""
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5841)
        signals = self.strategy.on_bar(bar)
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY_L1]
        self.assertEqual(len(buy_signals), 1)

    def test_level1_entry_beyond_threshold(self):
        """L1 entry when drop > 1%."""
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5830)
        signals = self.strategy.on_bar(bar)
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY_L1]
        self.assertEqual(len(buy_signals), 1)
        self.assertEqual(buy_signals[0].level, 1)
        self.assertEqual(buy_signals[0].quantity, 1)

    def test_no_entry_below_threshold(self):
        """No entry when drop < 1%: 5900 * 0.995 = 5870.5."""
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5871)
        signals = self.strategy.on_bar(bar)
        buy_signals = [s for s in signals if s.signal_type in (SignalType.BUY_L1, SignalType.BUY_L2)]
        self.assertEqual(len(buy_signals), 0)

    def test_level2_entry_after_level1(self):
        """L2 entry when drop > 2% after L1 position exists."""
        # Trigger L1
        bar1 = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        self.strategy.on_bar(bar1)

        # Trigger L2: 5900 * 0.98 = 5782
        bar2 = make_bar('IM0', datetime(2026, 2, 9, 14, 40), 5780)
        signals = self.strategy.on_bar(bar2)
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY_L2]
        self.assertEqual(len(buy_signals), 1)
        self.assertEqual(buy_signals[0].level, 2)

    def test_no_level2_without_level1(self):
        """L2 should NOT trigger if L1 hasn't triggered first."""
        # Jump straight to 2% drop without L1 in between
        # But since drop > threshold_1, L1 should trigger first
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5780)
        signals = self.strategy.on_bar(bar)
        # Should get L1, not L2 (state was WATCHING, not POSITION_1)
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY_L1]
        self.assertEqual(len(buy_signals), 1)
        l2_signals = [s for s in signals if s.signal_type == SignalType.BUY_L2]
        self.assertEqual(len(l2_signals), 0)

    def test_no_duplicate_l1_entry(self):
        """L1 should only trigger once."""
        bar1 = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        self.strategy.on_bar(bar1)

        # Another bar still below threshold but state is POSITION_1 now
        bar2 = make_bar('IM0', datetime(2026, 2, 9, 14, 36), 5835)
        signals = self.strategy.on_bar(bar2)
        l1_signals = [s for s in signals if s.signal_type == SignalType.BUY_L1]
        self.assertEqual(len(l1_signals), 0)

    def test_no_duplicate_l2_entry(self):
        """L2 should only trigger once."""
        # L1
        bar1 = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        self.strategy.on_bar(bar1)
        # L2
        bar2 = make_bar('IM0', datetime(2026, 2, 9, 14, 40), 5780)
        self.strategy.on_bar(bar2)

        # Another deep drop - state is POSITION_2, no more entries
        bar3 = make_bar('IM0', datetime(2026, 2, 9, 14, 45), 5750)
        signals = self.strategy.on_bar(bar3)
        buy_signals = [s for s in signals if s.signal_type in (SignalType.BUY_L1, SignalType.BUY_L2)]
        self.assertEqual(len(buy_signals), 0)

    def test_state_transitions_idle_to_position2(self):
        """Full state transition: IDLE → WATCHING → POSITION_1 → POSITION_2."""
        ss = self.strategy.get_symbol_state('IM0')
        self.assertEqual(ss.state, StrategyState.WATCHING)  # Already set by setUp

        # L1
        bar1 = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        self.strategy.on_bar(bar1)
        self.assertEqual(ss.state, StrategyState.POSITION_1)

        # L2
        bar2 = make_bar('IM0', datetime(2026, 2, 9, 14, 40), 5780)
        self.strategy.on_bar(bar2)
        self.assertEqual(ss.state, StrategyState.POSITION_2)

    def test_signal_contains_correct_drop_pct(self):
        """Signal should contain accurate drop percentage."""
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        signals = self.strategy.on_bar(bar)
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY_L1]
        self.assertEqual(len(buy_signals), 1)
        expected_drop = (5840 - 5900) / 5900  # ≈ -0.01017
        self.assertAlmostEqual(buy_signals[0].drop_pct, expected_drop, places=4)

    def test_entry_records_prices_and_quantities(self):
        """Entry should record prices and quantities in symbol state."""
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        self.strategy.on_bar(bar)

        ss = self.strategy.get_symbol_state('IM0')
        self.assertEqual(ss.entry_prices, [5840])
        self.assertEqual(ss.entry_quantities, [1])
        self.assertEqual(ss.entry_levels, [1])


class TestAlertConditions(unittest.TestCase):
    """Tests for alert signal generation."""

    def setUp(self):
        self.config = StrategyConfig(
            symbols=['IM0'],
            threshold_1=0.01,
            alert_threshold=0.008,
        )
        self.strategy = SettlementArbitrageStrategy(config=self.config)
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar)

    def test_alert_at_threshold(self):
        """Alert should fire when drop reaches alert_threshold (0.8%)."""
        # 5900 * (1 - 0.008) = 5852.8 → bar at 5852 should trigger
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 33), 5852)
        signals = self.strategy.on_bar(bar)
        alert_signals = [s for s in signals if s.signal_type == SignalType.ALERT]
        self.assertEqual(len(alert_signals), 1)

    def test_no_alert_above_threshold(self):
        """No alert when drop < alert_threshold."""
        # 5900 * (1 - 0.005) = 5870.5 → still above 0.8%
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 33), 5871)
        signals = self.strategy.on_bar(bar)
        alert_signals = [s for s in signals if s.signal_type == SignalType.ALERT]
        self.assertEqual(len(alert_signals), 0)

    def test_alert_deduplication(self):
        """Alert should only fire once per day per symbol."""
        bar1 = make_bar('IM0', datetime(2026, 2, 9, 14, 33), 5852)
        self.strategy.on_bar(bar1)

        bar2 = make_bar('IM0', datetime(2026, 2, 9, 14, 34), 5850)
        signals = self.strategy.on_bar(bar2)
        alert_signals = [s for s in signals if s.signal_type == SignalType.ALERT]
        self.assertEqual(len(alert_signals), 0)  # Duplicate suppressed

    def test_no_alert_when_in_position(self):
        """No alert should fire when already in a position."""
        # Trigger L1 first
        bar1 = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        self.strategy.on_bar(bar1)

        # Now drop further - already in POSITION_1, no alert
        bar2 = make_bar('IM0', datetime(2026, 2, 9, 14, 36), 5830)
        signals = self.strategy.on_bar(bar2)
        alert_signals = [s for s in signals if s.signal_type == SignalType.ALERT]
        self.assertEqual(len(alert_signals), 0)


class TestDayOpenClose(unittest.TestCase):
    """Tests for next-day open close logic."""

    def setUp(self):
        self.config = StrategyConfig(
            symbols=['IM0'],
            threshold_1=0.01,
            threshold_2=0.02,
        )
        self.strategy = SettlementArbitrageStrategy(config=self.config)

    def test_close_at_day_open(self):
        """Position should close at next day's open price."""
        # Enter position
        bar1 = make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar1)
        bar2 = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        self.strategy.on_bar(bar2)

        ss = self.strategy.get_symbol_state('IM0')
        self.assertTrue(ss.has_position)

        # Close at next day open
        signal = self.strategy.on_day_open('IM0', 5880)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.signal_type, SignalType.SELL_CLOSE)
        self.assertEqual(signal.price, 5880)
        self.assertEqual(signal.quantity, 1)  # Total quantity
        self.assertEqual(ss.state, StrategyState.CLOSING)

    def test_close_with_level2_position(self):
        """Close should include total quantity from L1 + L2."""
        bar1 = make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar1)
        bar2 = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        self.strategy.on_bar(bar2)
        bar3 = make_bar('IM0', datetime(2026, 2, 9, 14, 40), 5780)
        self.strategy.on_bar(bar3)

        signal = self.strategy.on_day_open('IM0', 5860)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.quantity, 2)  # 1 (L1) + 1 (L2)

    def test_no_close_without_position(self):
        """on_day_open should return None if no position."""
        signal = self.strategy.on_day_open('IM0', 5900)
        self.assertIsNone(signal)

    def test_no_close_for_unknown_symbol(self):
        """on_day_open should return None for unknown symbol."""
        signal = self.strategy.on_day_open('IF0', 5900)
        self.assertIsNone(signal)

    def test_close_signal_timestamp(self):
        """Close signal should use provided timestamp."""
        bar1 = make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar1)
        bar2 = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        self.strategy.on_bar(bar2)

        ts = datetime(2026, 2, 10, 9, 30)
        signal = self.strategy.on_day_open('IM0', 5880, timestamp=ts)
        self.assertEqual(signal.timestamp, ts)


class TestMultiSymbol(unittest.TestCase):
    """Tests for multi-symbol support."""

    def setUp(self):
        self.config = StrategyConfig(
            symbols=['IM0', 'IC0'],
            threshold_1=0.01,
            threshold_2=0.02,
        )
        self.strategy = SettlementArbitrageStrategy(config=self.config)

    def test_independent_base_prices(self):
        """Each symbol should have its own base price."""
        bar_im = make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        bar_ic = make_bar('IC0', datetime(2026, 2, 9, 14, 30), 6200)
        self.strategy.on_bar(bar_im)
        self.strategy.on_bar(bar_ic)

        ss_im = self.strategy.get_symbol_state('IM0')
        ss_ic = self.strategy.get_symbol_state('IC0')
        self.assertEqual(ss_im.base_price, 5900)
        self.assertEqual(ss_ic.base_price, 6200)

    def test_independent_signals(self):
        """Signals for one symbol should not affect another."""
        # Set base prices
        self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))
        self.strategy.on_bar(make_bar('IC0', datetime(2026, 2, 9, 14, 30), 6200))

        # Only IM0 drops
        signals = self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840))
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY_L1]
        self.assertEqual(len(buy_signals), 1)
        self.assertEqual(buy_signals[0].symbol, 'IM0')

        # IC0 stays flat
        ss_ic = self.strategy.get_symbol_state('IC0')
        self.assertEqual(ss_ic.state, StrategyState.WATCHING)

    def test_both_symbols_trigger(self):
        """Both symbols can trigger signals independently."""
        self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))
        self.strategy.on_bar(make_bar('IC0', datetime(2026, 2, 9, 14, 30), 6200))

        self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840))
        self.strategy.on_bar(make_bar('IC0', datetime(2026, 2, 9, 14, 35), 6130))

        ss_im = self.strategy.get_symbol_state('IM0')
        ss_ic = self.strategy.get_symbol_state('IC0')
        self.assertEqual(ss_im.state, StrategyState.POSITION_1)
        self.assertEqual(ss_ic.state, StrategyState.POSITION_1)


class TestNewDayTransition(unittest.TestCase):
    """Tests for day transition logic."""

    def setUp(self):
        self.config = StrategyConfig(symbols=['IM0'], threshold_1=0.01)
        self.strategy = SettlementArbitrageStrategy(config=self.config)

    def test_new_day_resets_watching_state(self):
        """New day should reset symbol state if no position."""
        bar1 = make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar1)

        ss = self.strategy.get_symbol_state('IM0')
        self.assertEqual(ss.state, StrategyState.WATCHING)

        # New day bar (no position held)
        bar2 = make_bar('IM0', datetime(2026, 2, 10, 9, 30), 5910)
        self.strategy.on_bar(bar2)

        # State should be reset to IDLE (new day, before watch)
        ss = self.strategy.get_symbol_state('IM0')
        self.assertEqual(ss.state, StrategyState.IDLE)
        self.assertIsNone(ss.base_price)

    def test_new_day_keeps_position_state(self):
        """New day should keep position state but reset base price."""
        # Enter position on day 1
        self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))
        self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840))

        ss = self.strategy.get_symbol_state('IM0')
        self.assertTrue(ss.has_position)

        # New day - position should carry over
        bar = make_bar('IM0', datetime(2026, 2, 10, 9, 30), 5850)
        self.strategy.on_bar(bar)

        ss = self.strategy.get_symbol_state('IM0')
        self.assertTrue(ss.has_position)
        self.assertIsNone(ss.base_price)  # Base price reset for new day

    def test_daily_signals_reset(self):
        """Daily signal list should reset on new day."""
        self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))
        self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840))

        today_signals = self.strategy.get_today_signals()
        self.assertGreater(len(today_signals), 0)

        # New day
        self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 10, 9, 30), 5850))
        today_signals = self.strategy.get_today_signals()
        self.assertEqual(len(today_signals), 0)

    def test_alert_reset_on_new_day(self):
        """Alert dedup tracking should reset on new day."""
        self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))
        # Trigger alert
        self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 33), 5852))

        # New day
        self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 10, 14, 30), 5900))
        signals = self.strategy.on_bar(make_bar('IM0', datetime(2026, 2, 10, 14, 33), 5852))
        alert_signals = [s for s in signals if s.signal_type == SignalType.ALERT]
        # Alert should fire again on new day
        self.assertEqual(len(alert_signals), 1)


class TestStrategyReset(unittest.TestCase):
    """Tests for strategy full reset."""

    def test_reset_clears_everything(self):
        """Full reset should clear all state."""
        config = StrategyConfig(symbols=['IM0', 'IC0'])
        strategy = SettlementArbitrageStrategy(config=config)

        # Build up state
        strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))
        strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840))

        strategy.reset()

        for symbol in ['IM0', 'IC0']:
            ss = strategy.get_symbol_state(symbol)
            self.assertEqual(ss.state, StrategyState.IDLE)
            self.assertIsNone(ss.base_price)
            self.assertFalse(ss.has_position)

        self.assertEqual(strategy.get_today_signals(), [])


class TestMonitorData(unittest.TestCase):
    """Tests for get_monitor_data."""

    def test_monitor_data_structure(self):
        """Monitor data should contain required fields."""
        config = StrategyConfig(symbols=['IM0'])
        strategy = SettlementArbitrageStrategy(config=config)

        strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))

        data = strategy.get_monitor_data()
        self.assertIn('current_date', data)
        self.assertIn('symbols', data)
        self.assertIn('total_signals_today', data)
        self.assertIn('IM0', data['symbols'])

        im_data = data['symbols']['IM0']
        self.assertIn('state', im_data)
        self.assertIn('base_price', im_data)
        self.assertIn('has_position', im_data)
        self.assertIn('total_quantity', im_data)
        self.assertIn('avg_entry_price', im_data)

    def test_monitor_data_after_entry(self):
        """Monitor data should reflect position state after entry."""
        config = StrategyConfig(symbols=['IM0'], threshold_1=0.01)
        strategy = SettlementArbitrageStrategy(config=config)

        strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))
        strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840))

        data = strategy.get_monitor_data()
        im_data = data['symbols']['IM0']
        self.assertEqual(im_data['state'], 'position_1')
        self.assertTrue(im_data['has_position'])
        self.assertEqual(im_data['total_quantity'], 1)
        self.assertEqual(im_data['base_price'], 5900)
        self.assertGreater(im_data['signals_today'], 0)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and boundary conditions."""

    def test_unknown_symbol_bar(self):
        """Bars for untracked symbols should be ignored."""
        config = StrategyConfig(symbols=['IM0'])
        strategy = SettlementArbitrageStrategy(config=config)

        bar = make_bar('IF0', datetime(2026, 2, 9, 14, 35), 3500)
        signals = strategy.on_bar(bar)
        self.assertEqual(len(signals), 0)

    def test_bar_after_watch_end(self):
        """Bars after 15:00 should not generate entry signals."""
        config = StrategyConfig(symbols=['IM0'], threshold_1=0.01)
        strategy = SettlementArbitrageStrategy(config=config)

        strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))

        bar = make_bar('IM0', datetime(2026, 2, 9, 15, 1), 5840)
        signals = strategy.on_bar(bar)
        buy_signals = [s for s in signals if s.signal_type in (SignalType.BUY_L1, SignalType.BUY_L2)]
        self.assertEqual(len(buy_signals), 0)

    def test_zero_close_price(self):
        """Strategy should handle zero close price gracefully."""
        config = StrategyConfig(symbols=['IM0'], threshold_1=0.01)
        strategy = SettlementArbitrageStrategy(config=config)

        strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))

        # Zero price bar
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 0)
        signals = strategy.on_bar(bar)
        # Should handle gracefully - large drop triggers L1
        # The important thing is it doesn't crash

    def test_price_rise_no_signal(self):
        """Price rise should not generate any buy signals."""
        config = StrategyConfig(symbols=['IM0'], threshold_1=0.01)
        strategy = SettlementArbitrageStrategy(config=config)

        strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))
        bar = make_bar('IM0', datetime(2026, 2, 9, 14, 35), 6000)
        signals = strategy.on_bar(bar)
        buy_signals = [s for s in signals if s.signal_type in (SignalType.BUY_L1, SignalType.BUY_L2)]
        self.assertEqual(len(buy_signals), 0)

    def test_rapid_successive_bars(self):
        """Multiple bars in quick succession should be handled correctly."""
        config = StrategyConfig(symbols=['IM0'], threshold_1=0.01)
        strategy = SettlementArbitrageStrategy(config=config)

        strategy.on_bar(make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900))

        total_signals = []
        for i in range(1, 30):
            bar = make_bar('IM0', datetime(2026, 2, 9, 14, 30 + i), 5900 - i * 5)
            signals = strategy.on_bar(bar)
            total_signals.extend(signals)

        # Should have exactly 1 L1 and at most 1 L2
        l1_count = sum(1 for s in total_signals if s.signal_type == SignalType.BUY_L1)
        l2_count = sum(1 for s in total_signals if s.signal_type == SignalType.BUY_L2)
        self.assertEqual(l1_count, 1)
        self.assertLessEqual(l2_count, 1)


if __name__ == '__main__':
    unittest.main()
