# Settlement Arbitrage Strategy - Risk Manager Unit Tests
# 结算价差套利策略 - 风控管理 单元测试

"""
Unit tests for RiskManager module.

Covers:
- Initialization and reset
- Daily loss limit checks
- Drawdown limit checks
- Position limit checks (per-symbol and total)
- Trade event handling (on_trade)
- Force close mechanism
- Risk status reporting
- Event logging and filtering
- Edge cases and boundary conditions
"""

import unittest
from datetime import datetime, date
from unittest.mock import MagicMock, patch

from app.strategies.settlement_arbitrage.config import RiskConfig, StrategyConfig
from app.strategies.settlement_arbitrage.position_manager import (
    PositionManager, Position, PositionStatus, PositionDirection, TradeRecord
)
from app.strategies.settlement_arbitrage.risk_manager import (
    RiskManager, RiskEvent, RiskEventType
)


class TestRiskManagerInitialization(unittest.TestCase):
    """Tests for RiskManager initialization and reset."""

    def test_default_initialization(self):
        """Should initialize with default config."""
        rm = RiskManager()
        self.assertIsNotNone(rm.config)
        self.assertIsNotNone(rm.strategy_config)
        self.assertFalse(rm.is_risk_triggered)

    def test_custom_config_initialization(self):
        """Should initialize with custom configs."""
        risk_cfg = RiskConfig(max_daily_loss=20000, max_drawdown=0.10)
        strat_cfg = StrategyConfig(max_position_per_symbol=3)
        rm = RiskManager(risk_config=risk_cfg, strategy_config=strat_cfg)

        self.assertEqual(rm.config.max_daily_loss, 20000)
        self.assertEqual(rm.config.max_drawdown, 0.10)
        self.assertEqual(rm.strategy_config.max_position_per_symbol, 3)

    def test_initialize_equity(self):
        """Should set initial equity values correctly."""
        rm = RiskManager()
        rm.initialize(initial_equity=500000)

        self.assertEqual(rm._initial_equity, 500000)
        self.assertEqual(rm._current_equity, 500000)
        self.assertEqual(rm._peak_equity, 500000)
        self.assertFalse(rm.is_risk_triggered)

    def test_reset_daily(self):
        """Should reset daily counters."""
        rm = RiskManager()
        rm.initialize(500000)
        rm._daily_pnl = -5000
        rm._daily_trades = 3
        rm._is_risk_triggered = True

        rm.reset_daily()

        self.assertEqual(rm._daily_pnl, 0.0)
        self.assertEqual(rm._daily_trades, 0)
        self.assertFalse(rm.is_risk_triggered)

    def test_full_reset(self):
        """Should fully reset all state."""
        rm = RiskManager()
        rm.initialize(500000)
        rm._daily_pnl = -5000
        rm._daily_trades = 3
        rm._events.append(RiskEvent(
            event_type=RiskEventType.DAILY_LOSS_LIMIT,
            message="test", value=-5000, limit=-10000
        ))
        rm._is_risk_triggered = True

        rm.reset()

        self.assertEqual(rm._daily_pnl, 0.0)
        self.assertEqual(rm._daily_trades, 0)
        self.assertEqual(rm._peak_equity, 0.0)
        self.assertEqual(rm._current_equity, 0.0)
        self.assertEqual(rm._initial_equity, 0.0)
        self.assertEqual(len(rm._events), 0)
        self.assertFalse(rm.is_risk_triggered)


class TestDailyLossLimit(unittest.TestCase):
    """Tests for daily loss limit checking."""

    def setUp(self):
        self.risk_cfg = RiskConfig(max_daily_loss=10000)
        self.rm = RiskManager(risk_config=self.risk_cfg)
        self.rm.initialize(500000)

    def test_no_trigger_within_limit(self):
        """Should return None when daily loss is within limit."""
        self.rm._daily_pnl = -5000  # Within 10000 limit
        event = self.rm.check_daily_loss_limit()
        self.assertIsNone(event)

    def test_no_trigger_positive_pnl(self):
        """Should return None when daily P&L is positive."""
        self.rm._daily_pnl = 3000
        event = self.rm.check_daily_loss_limit()
        self.assertIsNone(event)

    def test_no_trigger_zero_pnl(self):
        """Should return None when daily P&L is zero."""
        self.rm._daily_pnl = 0.0
        event = self.rm.check_daily_loss_limit()
        self.assertIsNone(event)

    def test_no_trigger_at_exact_limit(self):
        """Should return None when daily loss equals exactly the limit."""
        self.rm._daily_pnl = -10000  # Exactly at limit, not exceeded
        event = self.rm.check_daily_loss_limit()
        self.assertIsNone(event)

    def test_trigger_exceeds_limit(self):
        """Should trigger when daily loss exceeds limit."""
        self.rm._daily_pnl = -10001  # Exceeds 10000 limit
        event = self.rm.check_daily_loss_limit()

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, RiskEventType.DAILY_LOSS_LIMIT)
        self.assertTrue(self.rm.is_risk_triggered)

    def test_trigger_large_loss(self):
        """Should trigger on large loss."""
        self.rm._daily_pnl = -50000
        event = self.rm.check_daily_loss_limit()

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, RiskEventType.DAILY_LOSS_LIMIT)
        self.assertEqual(event.value, -50000)

    def test_event_logged_on_trigger(self):
        """Should log event when triggered."""
        self.rm._daily_pnl = -15000
        self.rm.check_daily_loss_limit()

        self.assertEqual(len(self.rm._events), 1)
        self.assertEqual(self.rm._events[0].event_type, RiskEventType.DAILY_LOSS_LIMIT)


class TestDrawdownLimit(unittest.TestCase):
    """Tests for maximum drawdown limit checking."""

    def setUp(self):
        self.risk_cfg = RiskConfig(max_drawdown=0.05)
        self.rm = RiskManager(risk_config=self.risk_cfg)
        self.rm.initialize(500000)

    def test_no_trigger_no_drawdown(self):
        """Should return None when there's no drawdown."""
        event = self.rm.check_drawdown_limit()
        self.assertIsNone(event)

    def test_no_trigger_within_limit(self):
        """Should return None when drawdown is within limit."""
        self.rm._current_equity = 490000  # 2% drawdown
        event = self.rm.check_drawdown_limit()
        self.assertIsNone(event)

    def test_no_trigger_at_exact_limit(self):
        """Should return None when drawdown equals exactly the limit."""
        self.rm._current_equity = 475000  # Exactly 5% drawdown
        event = self.rm.check_drawdown_limit()
        self.assertIsNone(event)

    def test_trigger_exceeds_limit(self):
        """Should trigger when drawdown exceeds limit."""
        self.rm._current_equity = 470000  # 6% drawdown > 5% limit
        event = self.rm.check_drawdown_limit()

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, RiskEventType.DRAWDOWN_LIMIT)
        self.assertTrue(self.rm.is_risk_triggered)
        self.assertAlmostEqual(event.value, 0.06, places=2)

    def test_no_trigger_zero_peak_equity(self):
        """Should return None when peak equity is zero."""
        self.rm._peak_equity = 0
        self.rm._current_equity = -1000
        event = self.rm.check_drawdown_limit()
        self.assertIsNone(event)

    def test_drawdown_after_equity_growth(self):
        """Should calculate drawdown from peak, not initial equity."""
        self.rm._peak_equity = 600000  # Equity grew
        self.rm._current_equity = 560000  # 6.67% drawdown from peak
        event = self.rm.check_drawdown_limit()

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, RiskEventType.DRAWDOWN_LIMIT)

    def test_event_logged_on_trigger(self):
        """Should log event when triggered."""
        self.rm._current_equity = 470000
        self.rm.check_drawdown_limit()

        self.assertEqual(len(self.rm._events), 1)
        self.assertEqual(self.rm._events[0].event_type, RiskEventType.DRAWDOWN_LIMIT)


class TestPositionLimit(unittest.TestCase):
    """Tests for position limit checking."""

    def setUp(self):
        self.risk_cfg = RiskConfig(max_total_position=4)
        self.strat_cfg = StrategyConfig(max_position_per_symbol=2)
        self.rm = RiskManager(
            risk_config=self.risk_cfg,
            strategy_config=self.strat_cfg
        )
        self.pm = PositionManager(self.strat_cfg)

    def test_no_trigger_empty_positions(self):
        """Should return None when no positions exist."""
        event = self.rm.check_position_limit('IM0', self.pm)
        self.assertIsNone(event)

    def test_no_trigger_within_per_symbol_limit(self):
        """Should return None when within per-symbol limit."""
        self.pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)
        event = self.rm.check_position_limit('IM0', self.pm)
        self.assertIsNone(event)

    def test_trigger_per_symbol_limit(self):
        """Should trigger when per-symbol limit reached."""
        self.pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)
        self.pm.open_position(symbol='IM0', price=5780, quantity=1, level=2)

        event = self.rm.check_position_limit('IM0', self.pm)

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, RiskEventType.POSITION_LIMIT)
        self.assertIn('IM0', event.message)

    def test_no_trigger_different_symbol(self):
        """Should not trigger for a different symbol."""
        self.pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)
        self.pm.open_position(symbol='IM0', price=5780, quantity=1, level=2)

        # IC0 has no positions
        event = self.rm.check_position_limit('IC0', self.pm)
        self.assertIsNone(event)

    def test_trigger_total_position_limit(self):
        """Should trigger when total position limit reached."""
        self.pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)
        self.pm.open_position(symbol='IM0', price=5780, quantity=1, level=2)
        self.pm.open_position(symbol='IC0', price=5200, quantity=1, level=1)
        self.pm.open_position(symbol='IC0', price=5150, quantity=1, level=2)

        # Total = 4, limit = 4 → should trigger
        event = self.rm.check_position_limit('IF0', self.pm)

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, RiskEventType.POSITION_LIMIT)

    def test_event_logged_on_position_limit(self):
        """Should log event when position limit triggered."""
        self.pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)
        self.pm.open_position(symbol='IM0', price=5780, quantity=1, level=2)

        self.rm.check_position_limit('IM0', self.pm)

        self.assertEqual(len(self.rm._events), 1)


class TestCheckAllRisks(unittest.TestCase):
    """Tests for check_all_risks comprehensive check."""

    def setUp(self):
        self.risk_cfg = RiskConfig(max_daily_loss=10000, max_drawdown=0.05)
        self.rm = RiskManager(risk_config=self.risk_cfg)
        self.rm.initialize(500000)

    def test_no_risk_when_within_all_limits(self):
        """Should return None when all risks are within limits."""
        self.rm._daily_pnl = -3000
        self.rm._current_equity = 495000
        event = self.rm.check_all_risks()
        self.assertIsNone(event)

    def test_detects_daily_loss_first(self):
        """Should detect daily loss limit (checked first)."""
        self.rm._daily_pnl = -15000
        event = self.rm.check_all_risks()

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, RiskEventType.DAILY_LOSS_LIMIT)

    def test_detects_drawdown_when_daily_ok(self):
        """Should detect drawdown when daily loss is ok."""
        self.rm._daily_pnl = -3000  # Within limit
        self.rm._current_equity = 470000  # 6% drawdown > 5% limit
        event = self.rm.check_all_risks()

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, RiskEventType.DRAWDOWN_LIMIT)


class TestOnTrade(unittest.TestCase):
    """Tests for trade event handling."""

    def setUp(self):
        self.rm = RiskManager()
        self.rm.initialize(500000)

    def _make_mock_trade(self, net_pnl):
        """Helper to create a mock trade record."""
        trade = MagicMock()
        trade.net_pnl = net_pnl
        return trade

    def test_winning_trade_updates_pnl(self):
        """Should update daily P&L with winning trade."""
        trade = self._make_mock_trade(5000)
        self.rm.on_trade(trade)

        self.assertEqual(self.rm._daily_pnl, 5000)
        self.assertEqual(self.rm._daily_trades, 1)

    def test_losing_trade_updates_pnl(self):
        """Should update daily P&L with losing trade."""
        trade = self._make_mock_trade(-3000)
        self.rm.on_trade(trade)

        self.assertEqual(self.rm._daily_pnl, -3000)
        self.assertEqual(self.rm._daily_trades, 1)

    def test_multiple_trades_accumulate(self):
        """Should accumulate P&L from multiple trades."""
        self.rm.on_trade(self._make_mock_trade(5000))
        self.rm.on_trade(self._make_mock_trade(-2000))
        self.rm.on_trade(self._make_mock_trade(3000))

        self.assertEqual(self.rm._daily_pnl, 6000)
        self.assertEqual(self.rm._daily_trades, 3)

    def test_equity_updated_on_trade(self):
        """Should update current equity on trade."""
        self.rm.on_trade(self._make_mock_trade(5000))
        self.assertEqual(self.rm._current_equity, 505000)

    def test_peak_equity_updated_on_winning_trade(self):
        """Should update peak equity when equity makes new high."""
        self.rm.on_trade(self._make_mock_trade(5000))
        self.assertEqual(self.rm._peak_equity, 505000)

    def test_peak_equity_not_updated_on_losing_trade(self):
        """Should not update peak equity on losing trade."""
        self.rm.on_trade(self._make_mock_trade(-3000))
        self.assertEqual(self.rm._peak_equity, 500000)  # Stays at initial

    def test_peak_equity_tracks_highest(self):
        """Should track the highest equity value."""
        self.rm.on_trade(self._make_mock_trade(10000))   # 510000
        self.rm.on_trade(self._make_mock_trade(-5000))    # 505000
        self.rm.on_trade(self._make_mock_trade(8000))     # 513000

        self.assertEqual(self.rm._peak_equity, 513000)
        self.assertEqual(self.rm._current_equity, 513000)


class TestForceClose(unittest.TestCase):
    """Tests for force close mechanism."""

    def setUp(self):
        self.risk_cfg = RiskConfig(max_daily_loss=10000)
        self.strat_cfg = StrategyConfig(max_position_per_symbol=2)
        self.rm = RiskManager(
            risk_config=self.risk_cfg,
            strategy_config=self.strat_cfg
        )
        self.rm.initialize(500000)
        self.pm = PositionManager(self.strat_cfg)

    def test_force_close_all_positions(self):
        """Should force close all positions."""
        self.pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)
        self.pm.open_position(symbol='IC0', price=5200, quantity=1, level=1)

        current_prices = {'IM0': 5800, 'IC0': 5180}
        trades = self.rm.force_close_all(
            self.pm, current_prices, reason="daily_loss_limit"
        )

        self.assertEqual(len(trades), 2)
        self.assertEqual(self.pm.get_position_count(), 0)

    def test_force_close_logs_event(self):
        """Should log a FORCE_CLOSE event."""
        self.pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)

        current_prices = {'IM0': 5800}
        self.rm.force_close_all(self.pm, current_prices, reason="test_reason")

        force_events = [
            e for e in self.rm._events
            if e.event_type == RiskEventType.FORCE_CLOSE
        ]
        self.assertEqual(len(force_events), 1)
        self.assertIn('test_reason', force_events[0].message)

    def test_force_close_empty_positions(self):
        """Should return empty list when no positions to close."""
        current_prices = {'IM0': 5800}
        trades = self.rm.force_close_all(self.pm, current_prices, reason="test")
        self.assertEqual(len(trades), 0)

    def test_force_close_updates_risk_state(self):
        """Should update risk state (pnl/equity) after force close."""
        self.pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)

        current_prices = {'IM0': 5890}
        trades = self.rm.force_close_all(self.pm, current_prices, reason="test")

        # Should have updated daily_pnl and equity via on_trade
        self.assertNotEqual(self.rm._daily_pnl, 0.0)
        self.assertGreater(self.rm._daily_trades, 0)


class TestRiskStatus(unittest.TestCase):
    """Tests for risk status reporting."""

    def setUp(self):
        self.risk_cfg = RiskConfig(max_daily_loss=10000, max_drawdown=0.05)
        self.rm = RiskManager(risk_config=self.risk_cfg)
        self.rm.initialize(500000)

    def test_initial_status(self):
        """Should report correct initial status."""
        status = self.rm.get_risk_status()

        self.assertFalse(status['is_risk_triggered'])
        self.assertEqual(status['daily_pnl'], 0.0)
        self.assertEqual(status['daily_trades'], 0)
        self.assertEqual(status['daily_loss_limit'], 10000)
        self.assertEqual(status['daily_loss_remaining'], 10000)
        self.assertEqual(status['current_equity'], 500000)
        self.assertEqual(status['peak_equity'], 500000)
        self.assertEqual(status['current_drawdown'], 0.0)
        self.assertEqual(status['max_drawdown_limit'], 0.05)
        self.assertEqual(status['total_risk_events'], 0)

    def test_status_after_loss(self):
        """Should report correct status after a loss."""
        trade = MagicMock()
        trade.net_pnl = -5000
        self.rm.on_trade(trade)

        status = self.rm.get_risk_status()

        self.assertEqual(status['daily_pnl'], -5000)
        self.assertEqual(status['daily_trades'], 1)
        self.assertEqual(status['daily_loss_remaining'], 5000)
        self.assertEqual(status['current_equity'], 495000)

    def test_status_drawdown_calculation(self):
        """Should calculate drawdown correctly in status."""
        self.rm._peak_equity = 600000
        self.rm._current_equity = 570000
        # Drawdown = (600000 - 570000) / 600000 = 0.05

        status = self.rm.get_risk_status()
        self.assertAlmostEqual(status['current_drawdown'], 0.05, places=4)

    def test_status_after_risk_trigger(self):
        """Should report risk triggered in status."""
        self.rm._daily_pnl = -15000
        self.rm.check_daily_loss_limit()

        status = self.rm.get_risk_status()
        self.assertTrue(status['is_risk_triggered'])
        self.assertEqual(status['total_risk_events'], 1)


class TestRiskEvents(unittest.TestCase):
    """Tests for risk event logging and filtering."""

    def setUp(self):
        self.rm = RiskManager()
        self.rm.initialize(500000)

    def test_get_events_empty(self):
        """Should return empty list when no events."""
        events = self.rm.get_events()
        self.assertEqual(len(events), 0)

    def test_get_events_returns_dicts(self):
        """Should return list of dictionaries."""
        self.rm._events.append(RiskEvent(
            event_type=RiskEventType.DAILY_LOSS_LIMIT,
            message="test loss", value=-15000, limit=-10000
        ))

        events = self.rm.get_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], dict)
        self.assertEqual(events[0]['event_type'], 'daily_loss_limit')
        self.assertEqual(events[0]['message'], 'test loss')

    def test_get_events_filter_by_type(self):
        """Should filter events by type."""
        self.rm._events.append(RiskEvent(
            event_type=RiskEventType.DAILY_LOSS_LIMIT,
            message="loss", value=-15000, limit=-10000
        ))
        self.rm._events.append(RiskEvent(
            event_type=RiskEventType.POSITION_LIMIT,
            message="position", value=4, limit=4
        ))
        self.rm._events.append(RiskEvent(
            event_type=RiskEventType.DAILY_LOSS_LIMIT,
            message="loss2", value=-20000, limit=-10000
        ))

        loss_events = self.rm.get_events(event_type=RiskEventType.DAILY_LOSS_LIMIT)
        self.assertEqual(len(loss_events), 2)

        pos_events = self.rm.get_events(event_type=RiskEventType.POSITION_LIMIT)
        self.assertEqual(len(pos_events), 1)

    def test_get_events_limit(self):
        """Should respect limit parameter."""
        for i in range(10):
            self.rm._events.append(RiskEvent(
                event_type=RiskEventType.DAILY_LOSS_LIMIT,
                message=f"event_{i}", value=-15000, limit=-10000
            ))

        events = self.rm.get_events(limit=3)
        self.assertEqual(len(events), 3)

    def test_get_events_sorted_most_recent_first(self):
        """Should return events sorted by timestamp descending."""
        e1 = RiskEvent(
            event_type=RiskEventType.DAILY_LOSS_LIMIT,
            message="first", value=-15000, limit=-10000,
            timestamp=datetime(2026, 2, 9, 10, 0, 0)
        )
        e2 = RiskEvent(
            event_type=RiskEventType.POSITION_LIMIT,
            message="second", value=4, limit=4,
            timestamp=datetime(2026, 2, 9, 14, 0, 0)
        )
        self.rm._events.extend([e1, e2])

        events = self.rm.get_events()
        self.assertEqual(events[0]['message'], 'second')
        self.assertEqual(events[1]['message'], 'first')


class TestRiskEventDataclass(unittest.TestCase):
    """Tests for RiskEvent dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        ts = datetime(2026, 2, 9, 14, 30, 0)
        event = RiskEvent(
            event_type=RiskEventType.FORCE_CLOSE,
            message="Force closed due to loss",
            value=-15000,
            limit=-10000,
            timestamp=ts,
            action_taken="force_close"
        )

        d = event.to_dict()

        self.assertEqual(d['event_type'], 'force_close')
        self.assertEqual(d['message'], 'Force closed due to loss')
        self.assertEqual(d['value'], -15000)
        self.assertEqual(d['limit'], -10000)
        self.assertEqual(d['timestamp'], ts.isoformat())
        self.assertEqual(d['action_taken'], 'force_close')

    def test_to_dict_without_action(self):
        """Should handle None action_taken."""
        event = RiskEvent(
            event_type=RiskEventType.DAILY_LOSS_LIMIT,
            message="test", value=-15000, limit=-10000
        )

        d = event.to_dict()
        self.assertIsNone(d['action_taken'])

    def test_event_types(self):
        """Should support all event types."""
        types = [
            RiskEventType.POSITION_LIMIT,
            RiskEventType.DAILY_LOSS_LIMIT,
            RiskEventType.DRAWDOWN_LIMIT,
            RiskEventType.FORCE_CLOSE,
        ]
        for et in types:
            event = RiskEvent(
                event_type=et, message="test", value=0, limit=0
            )
            self.assertEqual(event.event_type, et)


class TestRiskManagerEdgeCases(unittest.TestCase):
    """Tests for edge cases and boundary conditions."""

    def test_on_trade_resets_daily_on_new_day(self):
        """Should reset daily counters on new day when on_trade is called."""
        rm = RiskManager()
        rm.initialize(500000)
        rm._daily_pnl = -5000
        rm._daily_trades = 2
        rm._current_date = date(2026, 2, 8)  # Yesterday

        trade = MagicMock()
        trade.net_pnl = 1000

        with patch('app.strategies.settlement_arbitrage.risk_manager.date') as mock_date:
            mock_date.today.return_value = date(2026, 2, 9)
            rm.on_trade(trade)

        # daily_pnl should be reset then updated with new trade
        self.assertEqual(rm._daily_pnl, 1000)
        self.assertEqual(rm._daily_trades, 1)

    def test_multiple_risk_triggers(self):
        """Should handle multiple risk triggers."""
        risk_cfg = RiskConfig(max_daily_loss=10000, max_drawdown=0.05)
        rm = RiskManager(risk_config=risk_cfg)
        rm.initialize(500000)

        # Trigger daily loss
        rm._daily_pnl = -15000
        rm.check_daily_loss_limit()

        # Trigger drawdown
        rm._current_equity = 470000
        rm.check_drawdown_limit()

        self.assertEqual(len(rm._events), 2)
        self.assertTrue(rm.is_risk_triggered)

    def test_force_close_partial_prices(self):
        """Should only close positions for symbols with prices provided."""
        strat_cfg = StrategyConfig(max_position_per_symbol=2)
        rm = RiskManager(strategy_config=strat_cfg)
        rm.initialize(500000)
        pm = PositionManager(strat_cfg)

        pm.open_position(symbol='IM0', price=5840, quantity=1, level=1)
        pm.open_position(symbol='IC0', price=5200, quantity=1, level=1)

        # Only provide price for IM0
        current_prices = {'IM0': 5800}
        trades = rm.force_close_all(pm, current_prices, reason="test")

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].position.symbol, 'IM0')
        # IC0 should still be open
        self.assertTrue(pm.has_open_positions('IC0'))

    def test_is_risk_triggered_property(self):
        """Should correctly reflect risk triggered state."""
        rm = RiskManager(risk_config=RiskConfig(max_daily_loss=10000))
        rm.initialize(500000)

        self.assertFalse(rm.is_risk_triggered)

        rm._daily_pnl = -15000
        rm.check_daily_loss_limit()

        self.assertTrue(rm.is_risk_triggered)

        rm.reset_daily()
        self.assertFalse(rm.is_risk_triggered)


if __name__ == '__main__':
    unittest.main()
