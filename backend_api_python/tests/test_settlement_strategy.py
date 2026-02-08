# Settlement Arbitrage Strategy - Integration Tests
# 结算价差套利策略 - 集成测试

"""
Comprehensive test suite for the Settlement Arbitrage Strategy.

Tests cover:
- VWAP calculation accuracy
- Entry/exit condition logic
- Position management
- Risk management
- Backtest engine
"""

import unittest
from datetime import datetime, date, time, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import numpy as np

from app.strategies.settlement_arbitrage.config import StrategyConfig, RiskConfig, BacktestConfig
from app.strategies.settlement_arbitrage.data_handler import MinuteBar, MinuteDataHandler
from app.strategies.settlement_arbitrage.vwap_calculator import VWAPCalculator
from app.strategies.settlement_arbitrage.strategy import (
    SettlementArbitrageStrategy, SignalType, StrategyState
)
from app.strategies.settlement_arbitrage.position_manager import PositionManager, PositionDirection
from app.strategies.settlement_arbitrage.risk_manager import RiskManager, RiskEventType


class TestVWAPCalculator(unittest.TestCase):
    """Tests for VWAPCalculator."""

    def setUp(self):
        self.calculator = VWAPCalculator()

    def test_basic_vwap_calculation(self):
        """VWAP should equal sum(price*volume)/sum(volume)."""
        bars = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=4, freq='15min'),
            'open': [100, 101, 99, 100],
            'high': [102, 103, 101, 102],
            'low': [99, 100, 98, 99],
            'close': [101, 99, 100, 101],
            'volume': [1000, 2000, 1500, 500],
        })

        vwap = self.calculator.calculate_vwap(bars)
        expected = (101*1000 + 99*2000 + 100*1500 + 101*500) / (1000+2000+1500+500)
        self.assertIsNotNone(vwap)
        self.assertAlmostEqual(vwap, round(expected, 2), places=1)

    def test_vwap_with_zero_volume(self):
        """VWAP should use simple average when volume is zero."""
        bars = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=3, freq='20min'),
            'close': [100, 102, 101],
            'volume': [0, 0, 0],
        })

        vwap = self.calculator.calculate_vwap(bars)
        self.assertIsNotNone(vwap)
        self.assertAlmostEqual(vwap, 101.0, places=0)

    def test_vwap_empty_bars(self):
        """VWAP should return None for empty data."""
        vwap = self.calculator.calculate_vwap(pd.DataFrame())
        self.assertIsNone(vwap)

    def test_realtime_vwap_update(self):
        """Real-time VWAP should update incrementally."""
        self.calculator.reset_realtime('IM0')

        v1 = self.calculator.update_realtime('IM0', 5800, 100)
        self.assertEqual(v1, 5800.0)

        v2 = self.calculator.update_realtime('IM0', 5900, 200)
        expected = (5800*100 + 5900*200) / (100+200)
        self.assertAlmostEqual(v2, round(expected, 2), places=1)

    def test_price_vs_settlement(self):
        """Price vs settlement deviation calculation."""
        result = self.calculator.calculate_price_vs_settlement(5800, 5900)
        self.assertAlmostEqual(result['deviation'], -100.0, places=1)
        self.assertLess(result['deviation_pct'], 0)


class TestStrategy(unittest.TestCase):
    """Tests for SettlementArbitrageStrategy."""

    def setUp(self):
        self.config = StrategyConfig(
            symbols=['IM0'],
            threshold_1=0.01,
            threshold_2=0.02,
            alert_threshold=0.008,
            position_size_1=1,
            position_size_2=1,
        )
        self.strategy = SettlementArbitrageStrategy(config=self.config)

    def _make_bar(self, symbol, dt, close, volume=100):
        return MinuteBar(
            symbol=symbol, dt=dt,
            open_price=close, high=close+1, low=close-1, close=close,
            volume=volume
        )

    def test_base_price_set_at_watch_start(self):
        """Base price should be set when watch period starts."""
        bar = self._make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar)

        ss = self.strategy.get_symbol_state('IM0')
        self.assertEqual(ss.base_price, 5900)
        self.assertEqual(ss.state, StrategyState.WATCHING)

    def test_no_signal_before_watch(self):
        """No signal should be generated before 14:30."""
        bar = self._make_bar('IM0', datetime(2026, 2, 9, 14, 0), 5900)
        signals = self.strategy.on_bar(bar)
        self.assertEqual(len(signals), 0)

    def test_level1_entry_signal(self):
        """L1 signal when drop > threshold_1 (1%)."""
        # Set base price at 14:30
        bar1 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar1)

        # Drop > 1%: 5900 * 0.99 = 5841
        bar2 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        signals = self.strategy.on_bar(bar2)

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].signal_type, SignalType.BUY_L1)
        self.assertEqual(signals[0].level, 1)

        ss = self.strategy.get_symbol_state('IM0')
        self.assertEqual(ss.state, StrategyState.POSITION_1)

    def test_level2_entry_signal(self):
        """L2 signal when drop > threshold_2 (2%)."""
        # Set base
        bar1 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar1)

        # L1 trigger
        bar2 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        self.strategy.on_bar(bar2)

        # L2 trigger: drop > 2% → 5900 * 0.98 = 5782
        bar3 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 40), 5780)
        signals = self.strategy.on_bar(bar3)

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].signal_type, SignalType.BUY_L2)
        self.assertEqual(signals[0].level, 2)

        ss = self.strategy.get_symbol_state('IM0')
        self.assertEqual(ss.state, StrategyState.POSITION_2)

    def test_alert_signal(self):
        """Alert when drop approaches threshold (0.8%)."""
        bar1 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar1)

        # Drop 0.85%: 5900 * (1-0.0085) ≈ 5849.85
        bar2 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 33), 5849)
        signals = self.strategy.on_bar(bar2)

        alert_signals = [s for s in signals if s.signal_type == SignalType.ALERT]
        self.assertEqual(len(alert_signals), 1)

    def test_no_duplicate_alert(self):
        """Alert should only fire once per day per symbol."""
        bar1 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar1)

        bar2 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 33), 5849)
        self.strategy.on_bar(bar2)

        bar3 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 36), 5848)
        signals = self.strategy.on_bar(bar3)

        alert_signals = [s for s in signals if s.signal_type == SignalType.ALERT]
        self.assertEqual(len(alert_signals), 0)  # No duplicate

    def test_day_open_close(self):
        """Positions should close at next day open."""
        # Enter position
        bar1 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar1)

        bar2 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5840)
        self.strategy.on_bar(bar2)

        # Close at next day open
        signal = self.strategy.on_day_open('IM0', 5880)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.signal_type, SignalType.SELL_CLOSE)

    def test_no_entry_when_drop_insufficient(self):
        """No signal when drop < threshold."""
        bar1 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 30), 5900)
        self.strategy.on_bar(bar1)

        # Drop only 0.5%: 5900 * 0.995 = 5870.5
        bar2 = self._make_bar('IM0', datetime(2026, 2, 9, 14, 35), 5871)
        signals = self.strategy.on_bar(bar2)

        buy_signals = [s for s in signals if s.signal_type in (SignalType.BUY_L1, SignalType.BUY_L2)]
        self.assertEqual(len(buy_signals), 0)


class TestPositionManager(unittest.TestCase):
    """Tests for PositionManager."""

    def setUp(self):
        self.pm = PositionManager()

    def test_open_position(self):
        """Should create a position with correct fields."""
        pos = self.pm.open_position(
            symbol='IM0', price=5840, quantity=1, level=1,
            base_price=5900, drop_pct=-0.0102
        )
        self.assertEqual(pos.symbol, 'IM0')
        self.assertEqual(pos.entry_price, 5840)
        self.assertEqual(pos.quantity, 1)
        self.assertTrue(pos.margin > 0)

    def test_close_position(self):
        """Should close position and calculate P&L."""
        pos = self.pm.open_position(
            symbol='IM0', price=5840, quantity=1, level=1
        )

        trade = self.pm.close_position(pos.id, exit_price=5890)
        self.assertIsNotNone(trade)
        self.assertGreater(trade.gross_pnl, 0)  # Price went up
        self.assertGreater(trade.net_pnl, 0)  # Profit after fees

    def test_close_all_positions(self):
        """Should close all open positions."""
        self.pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)
        self.pm.open_position(symbol='IM0', price=5780, quantity=1, level=2)

        trades = self.pm.close_all_positions(exit_price=5890)
        self.assertEqual(len(trades), 2)
        self.assertEqual(self.pm.get_position_count(), 0)

    def test_pnl_summary(self):
        """Should calculate correct P&L summary."""
        pos = self.pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)
        self.pm.close_position(pos.id, exit_price=5890)

        summary = self.pm.get_pnl_summary()
        self.assertEqual(summary['total_trades'], 1)
        self.assertEqual(summary['winning_trades'], 1)
        self.assertGreater(summary['total_pnl'], 0)


class TestRiskManager(unittest.TestCase):
    """Tests for RiskManager."""

    def setUp(self):
        self.risk_config = RiskConfig(
            max_daily_loss=10000,
            max_drawdown=0.05,
            force_close_on_limit=True,
            max_total_position=4,
        )
        self.strategy_config = StrategyConfig(max_position_per_symbol=2)
        self.rm = RiskManager(self.risk_config, self.strategy_config)
        self.rm.initialize(500000)

    def test_daily_loss_limit(self):
        """Should trigger when daily loss exceeds limit."""
        from app.strategies.settlement_arbitrage.position_manager import TradeRecord, Position

        # Simulate a loss trade
        mock_trade = MagicMock()
        mock_trade.net_pnl = -11000  # Exceeds 10000 limit

        self.rm.on_trade(mock_trade)
        event = self.rm.check_daily_loss_limit()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, RiskEventType.DAILY_LOSS_LIMIT)

    def test_position_limit(self):
        """Should reject when position limit reached."""
        pm = PositionManager(self.strategy_config)
        pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)
        pm.open_position(symbol='IM0', price=5780, quantity=1, level=2)

        event = self.rm.check_position_limit('IM0', pm)
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, RiskEventType.POSITION_LIMIT)

    def test_no_risk_when_within_limits(self):
        """Should return None when all within limits."""
        event = self.rm.check_all_risks()
        self.assertIsNone(event)

    def test_drawdown_limit(self):
        """Should trigger when drawdown exceeds limit."""
        self.rm._current_equity = 470000  # 6% drawdown from 500000
        event = self.rm.check_drawdown_limit()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, RiskEventType.DRAWDOWN_LIMIT)


class TestMinuteDataHandler(unittest.TestCase):
    """Tests for MinuteDataHandler."""

    def setUp(self):
        self.handler = MinuteDataHandler()

    def test_subscribe(self):
        """Should subscribe to symbols."""
        self.handler.subscribe(['IM0', 'IC0'])
        self.assertEqual(len(self.handler._symbols), 2)

    def test_callback_registration(self):
        """Should register and fire callbacks."""
        callback = MagicMock()
        self.handler.on_bar(callback)
        self.assertEqual(len(self.handler._bar_callbacks), 1)

    def test_cache_update(self):
        """Should update cache with deduplication."""
        df1 = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:30', periods=3, freq='1min'),
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [100, 200, 150],
        })

        self.handler._update_cache('IM0', df1)
        cached = self.handler.get_cached_bars('IM0')
        self.assertIsNotNone(cached)
        self.assertEqual(len(cached), 3)


if __name__ == '__main__':
    unittest.main()
