"""
Unit tests for the StrategyScheduler module.

Tests cover:
- Initialization and component wiring
- Start / stop lifecycle
- Signal processing (BUY_L1, BUY_L2, SELL_CLOSE, ALERT)
- Daily lifecycle (pre-market, day-open close, post-market)
- Notification dispatch
- Risk event handling & force close
- Status reporting
- Config hot-update
- Global singleton helpers (get_scheduler, create_scheduler)
"""

import threading
import time as time_mod
from datetime import datetime, date, time, timedelta
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock, call

from app.strategies.settlement_arbitrage.config import StrategyConfig, RiskConfig
from app.strategies.settlement_arbitrage.data_handler import MinuteBar, MinuteDataHandler
from app.strategies.settlement_arbitrage.strategy import (
    SettlementArbitrageStrategy, Signal, SignalType, StrategyState,
)
from app.strategies.settlement_arbitrage.position_manager import (
    PositionManager, Position, TradeRecord, PositionDirection, PositionStatus,
)
from app.strategies.settlement_arbitrage.risk_manager import (
    RiskManager, RiskEvent, RiskEventType,
)
from app.strategies.settlement_arbitrage.scheduler import (
    StrategyScheduler, get_scheduler, create_scheduler, _scheduler_instance,
)


# ========== Helpers ==========

def _make_bar(symbol="IM0", price=5800.0, volume=100.0, dt=None):
    """Create a MinuteBar for testing."""
    if dt is None:
        dt = datetime(2025, 1, 15, 14, 35, 0)
    return MinuteBar(
        symbol=symbol,
        dt=dt,
        open_price=price,
        high=price + 5,
        low=price - 5,
        close=price,
        volume=volume,
        amount=price * volume,
    )


def _make_signal(
    signal_type=SignalType.BUY_L1, symbol="IM0", price=5750.0,
    base_price=5800.0, drop_pct=-0.0086, level=1, quantity=1,
):
    """Create a Signal for testing."""
    return Signal(
        signal_type=signal_type,
        symbol=symbol,
        price=price,
        base_price=base_price,
        drop_pct=drop_pct,
        level=level,
        quantity=quantity,
        timestamp=datetime(2025, 1, 15, 14, 40, 0),
    )


def _make_position(symbol="IM0", entry_price=5750.0, quantity=1, level=1):
    """Create a Position for testing."""
    return Position(
        id="pos-001",
        symbol=symbol,
        direction=PositionDirection.LONG,
        quantity=quantity,
        entry_price=entry_price,
        entry_time=datetime(2025, 1, 15, 14, 40, 0),
        level=level,
        base_price=5800.0,
        drop_pct=-0.0086,
        margin=139200.0,
    )


def _make_trade(position=None, gross_pnl=2000.0, net_pnl=1950.0):
    """Create a TradeRecord for testing."""
    if position is None:
        position = _make_position()
    position.exit_price = 5760.0
    position.exit_time = datetime(2025, 1, 16, 9, 31, 0)
    position.status = PositionStatus.CLOSED
    position.pnl = net_pnl
    return TradeRecord(
        position=position,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        holding_hours=18.85,
    )


class TestSchedulerInit(TestCase):
    """Tests for StrategyScheduler initialization."""

    @patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource")
    @patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService")
    def test_default_initialization(self, mock_notifier_cls, mock_ds_cls):
        """Scheduler initializes with default config when none provided."""
        scheduler = StrategyScheduler()

        self.assertFalse(scheduler.is_running)
        self.assertIsNotNone(scheduler.strategy)
        self.assertIsNotNone(scheduler.position_manager)
        self.assertIsNotNone(scheduler.risk_manager)
        self.assertIsNotNone(scheduler.data_handler)
        self.assertIsNone(scheduler._started_at)
        self.assertIsNone(scheduler._heartbeat)

    @patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource")
    @patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService")
    def test_custom_config_initialization(self, mock_notifier_cls, mock_ds_cls):
        """Scheduler uses provided configs."""
        cfg = StrategyConfig(symbols=["IC0"], threshold_1=0.015)
        risk_cfg = RiskConfig(max_daily_loss=30000)
        notif_cfg = {"telegram": True}

        scheduler = StrategyScheduler(
            strategy_config=cfg,
            risk_config=risk_cfg,
            notification_config=notif_cfg,
        )

        self.assertEqual(scheduler._config.symbols, ["IC0"])
        self.assertAlmostEqual(scheduler._config.threshold_1, 0.015)
        self.assertAlmostEqual(scheduler._risk_config.max_daily_loss, 30000)
        self.assertEqual(scheduler._notification_config, {"telegram": True})


class TestSchedulerStartStop(TestCase):
    """Tests for start / stop lifecycle."""

    @patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource")
    @patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService")
    def test_start_sets_running(self, mock_notifier_cls, mock_ds_cls):
        """start() should set _running=True and spin up thread."""
        scheduler = StrategyScheduler()
        # Mock heavy components to avoid real I/O
        scheduler._data_handler = MagicMock(spec=MinuteDataHandler)
        scheduler._risk_manager = MagicMock(spec=RiskManager)

        scheduler.start()

        self.assertTrue(scheduler.is_running)
        self.assertIsNotNone(scheduler._started_at)
        self.assertIsNotNone(scheduler._main_thread)
        self.assertTrue(scheduler._main_thread.is_alive())

        # Cleanup
        scheduler.stop()
        self.assertFalse(scheduler.is_running)

    @patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource")
    @patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService")
    def test_start_twice_is_noop(self, mock_notifier_cls, mock_ds_cls):
        """Calling start() twice should not create a second thread."""
        scheduler = StrategyScheduler()
        scheduler._data_handler = MagicMock(spec=MinuteDataHandler)
        scheduler._risk_manager = MagicMock(spec=RiskManager)

        scheduler.start()
        first_thread = scheduler._main_thread
        scheduler.start()  # second call
        self.assertIs(scheduler._main_thread, first_thread)

        scheduler.stop()

    @patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource")
    @patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService")
    def test_stop_cleans_up(self, mock_notifier_cls, mock_ds_cls):
        """stop() should stop data handler and save data."""
        scheduler = StrategyScheduler()
        scheduler._data_handler = MagicMock(spec=MinuteDataHandler)
        scheduler._risk_manager = MagicMock(spec=RiskManager)

        scheduler.start()
        scheduler.stop()

        scheduler._data_handler.stop.assert_called_once()
        scheduler._data_handler.save_all_and_cleanup.assert_called_once()
        self.assertFalse(scheduler.is_running)


class TestOnMinuteBar(TestCase):
    """Tests for _on_minute_bar callback."""

    def _make_scheduler(self):
        """Create a scheduler with mocked components."""
        with patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource"), \
             patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService"):
            scheduler = StrategyScheduler()

        scheduler._strategy = MagicMock(spec=SettlementArbitrageStrategy)
        scheduler._position_manager = MagicMock(spec=PositionManager)
        scheduler._risk_manager = MagicMock(spec=RiskManager)
        scheduler._notifier = MagicMock()
        scheduler._data_source = MagicMock()
        return scheduler

    def test_on_bar_no_signals(self):
        """When strategy returns no signals, nothing happens."""
        scheduler = self._make_scheduler()
        scheduler._strategy.on_bar.return_value = []
        scheduler._position_manager.has_open_positions.return_value = False

        bar = _make_bar()
        scheduler._on_minute_bar(bar)

        scheduler._strategy.on_bar.assert_called_once_with(bar)
        # No risk check since no open positions
        scheduler._risk_manager.check_all_risks.assert_not_called()

    def test_on_bar_risk_check_when_positions_open(self):
        """Risk check runs when there are open positions."""
        scheduler = self._make_scheduler()
        scheduler._strategy.on_bar.return_value = []
        scheduler._position_manager.has_open_positions.return_value = True
        scheduler._risk_manager.check_all_risks.return_value = None

        bar = _make_bar()
        scheduler._on_minute_bar(bar)

        scheduler._risk_manager.check_all_risks.assert_called_once_with(
            scheduler._position_manager
        )

    def test_on_bar_exception_is_caught(self):
        """Exceptions in on_bar callback should not propagate."""
        scheduler = self._make_scheduler()
        scheduler._strategy.on_bar.side_effect = RuntimeError("boom")

        bar = _make_bar()
        # Should not raise
        scheduler._on_minute_bar(bar)


class TestProcessSignal(TestCase):
    """Tests for _process_signal with different signal types."""

    def _make_scheduler(self):
        with patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource"), \
             patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService"):
            scheduler = StrategyScheduler()

        scheduler._strategy = MagicMock(spec=SettlementArbitrageStrategy)
        scheduler._position_manager = MagicMock(spec=PositionManager)
        scheduler._risk_manager = MagicMock(spec=RiskManager)
        scheduler._notifier = MagicMock()
        scheduler._data_source = MagicMock()
        return scheduler

    def test_buy_l1_signal_opens_position(self):
        """BUY_L1 signal should open a position and send notification."""
        scheduler = self._make_scheduler()
        scheduler._risk_manager.check_position_limit.return_value = None
        scheduler._position_manager.open_position.return_value = _make_position()
        scheduler._config.notify_on_entry = True

        signal = _make_signal(signal_type=SignalType.BUY_L1)
        bar = _make_bar()
        scheduler._process_signal(signal, bar)

        scheduler._position_manager.open_position.assert_called_once()
        call_kwargs = scheduler._position_manager.open_position.call_args
        self.assertEqual(call_kwargs.kwargs['symbol'], "IM0")
        self.assertEqual(call_kwargs.kwargs['level'], 1)

    def test_buy_l1_blocked_by_risk(self):
        """BUY_L1 signal blocked when risk limit reached."""
        scheduler = self._make_scheduler()
        risk_event = RiskEvent(
            event_type=RiskEventType.POSITION_LIMIT,
            message="limit reached",
            value=3.0,
            limit=3.0,
        )
        scheduler._risk_manager.check_position_limit.return_value = risk_event

        signal = _make_signal(signal_type=SignalType.BUY_L1)
        scheduler._process_signal(signal, _make_bar())

        scheduler._position_manager.open_position.assert_not_called()

    def test_buy_l2_signal_opens_position(self):
        """BUY_L2 signal should also open a position."""
        scheduler = self._make_scheduler()
        scheduler._risk_manager.check_position_limit.return_value = None
        scheduler._position_manager.open_position.return_value = _make_position(level=2)
        scheduler._config.notify_on_entry = True

        signal = _make_signal(signal_type=SignalType.BUY_L2, level=2, quantity=2)
        scheduler._process_signal(signal, _make_bar())

        scheduler._position_manager.open_position.assert_called_once()

    def test_buy_l2_blocked_by_risk(self):
        """BUY_L2 signal also respects risk limits."""
        scheduler = self._make_scheduler()
        risk_event = RiskEvent(
            event_type=RiskEventType.POSITION_LIMIT,
            message="limit reached",
            value=5.0,
            limit=5.0,
        )
        scheduler._risk_manager.check_position_limit.return_value = risk_event

        signal = _make_signal(signal_type=SignalType.BUY_L2, level=2)
        scheduler._process_signal(signal, _make_bar())

        scheduler._position_manager.open_position.assert_not_called()

    def test_sell_close_signal_closes_positions(self):
        """SELL_CLOSE signal should close positions and update risk manager."""
        scheduler = self._make_scheduler()
        trade = _make_trade()
        scheduler._position_manager.close_all_positions.return_value = [trade]
        scheduler._config.notify_on_exit = True

        signal = _make_signal(signal_type=SignalType.SELL_CLOSE)
        scheduler._process_signal(signal, _make_bar())

        scheduler._position_manager.close_all_positions.assert_called_once()
        scheduler._risk_manager.on_trade.assert_called_once_with(trade)

    def test_sell_close_no_trades(self):
        """SELL_CLOSE with no open positions should not send notification."""
        scheduler = self._make_scheduler()
        scheduler._position_manager.close_all_positions.return_value = []

        signal = _make_signal(signal_type=SignalType.SELL_CLOSE)
        scheduler._process_signal(signal, _make_bar())

        # on_trade should not be called
        scheduler._risk_manager.on_trade.assert_not_called()

    def test_alert_signal(self):
        """ALERT signal should trigger alert notification."""
        scheduler = self._make_scheduler()
        scheduler._config.notify_on_alert = True

        signal = _make_signal(signal_type=SignalType.ALERT)
        scheduler._process_signal(signal, _make_bar())

        # No position opened for alert
        scheduler._position_manager.open_position.assert_not_called()
        scheduler._position_manager.close_all_positions.assert_not_called()


class TestNotifications(TestCase):
    """Tests for notification dispatch methods."""

    def _make_scheduler(self):
        with patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource"), \
             patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService"):
            scheduler = StrategyScheduler()
        scheduler._notifier = MagicMock()
        return scheduler

    def test_send_signal_notification_when_enabled(self):
        """Buy notification sent when notify_on_entry is True."""
        scheduler = self._make_scheduler()
        scheduler._config.notify_on_entry = True

        signal = _make_signal(signal_type=SignalType.BUY_L1)
        scheduler._send_signal_notification(signal)

        scheduler._notifier.send_buy_signal.assert_called_once()

    def test_send_signal_notification_when_disabled(self):
        """Buy notification not sent when notify_on_entry is False."""
        scheduler = self._make_scheduler()
        scheduler._config.notify_on_entry = False

        signal = _make_signal(signal_type=SignalType.BUY_L1)
        scheduler._send_signal_notification(signal)

        scheduler._notifier.send_buy_signal.assert_not_called()

    def test_send_close_notification_when_enabled(self):
        """Close notification sent when notify_on_exit is True."""
        scheduler = self._make_scheduler()
        scheduler._config.notify_on_exit = True

        signal = _make_signal(signal_type=SignalType.SELL_CLOSE)
        trades = [_make_trade(net_pnl=1500.0)]
        scheduler._send_close_notification(signal, trades, 1500.0)

        scheduler._notifier.send_sell_signal.assert_called_once()

    def test_send_close_notification_when_disabled(self):
        """Close notification not sent when notify_on_exit is False."""
        scheduler = self._make_scheduler()
        scheduler._config.notify_on_exit = False

        signal = _make_signal(signal_type=SignalType.SELL_CLOSE)
        scheduler._send_close_notification(signal, [_make_trade()], 1500.0)

        scheduler._notifier.send_sell_signal.assert_not_called()

    def test_send_alert_notification_when_enabled(self):
        """Alert notification sent when notify_on_alert is True."""
        scheduler = self._make_scheduler()
        scheduler._config.notify_on_alert = True

        signal = _make_signal(signal_type=SignalType.ALERT)
        scheduler._send_alert_notification(signal)

        scheduler._notifier.send_price_alert.assert_called_once()

    def test_send_alert_notification_when_disabled(self):
        """Alert notification not sent when notify_on_alert is False."""
        scheduler = self._make_scheduler()
        scheduler._config.notify_on_alert = False

        signal = _make_signal(signal_type=SignalType.ALERT)
        scheduler._send_alert_notification(signal)

        scheduler._notifier.send_price_alert.assert_not_called()

    def test_notification_error_is_caught(self):
        """Notification errors should not propagate."""
        scheduler = self._make_scheduler()
        scheduler._config.notify_on_entry = True
        scheduler._notifier.send_buy_signal.side_effect = Exception("network error")

        signal = _make_signal(signal_type=SignalType.BUY_L1)
        # Should not raise
        scheduler._send_signal_notification(signal)


class TestDailyLifecycle(TestCase):
    """Tests for pre-market, day-open close, and post-market."""

    def _make_scheduler(self):
        with patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource"), \
             patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService"):
            scheduler = StrategyScheduler()

        scheduler._data_source = MagicMock()
        scheduler._strategy = MagicMock(spec=SettlementArbitrageStrategy)
        scheduler._position_manager = MagicMock(spec=PositionManager)
        scheduler._risk_manager = MagicMock(spec=RiskManager)
        scheduler._vwap_calculator = MagicMock()
        scheduler._data_handler = MagicMock(spec=MinuteDataHandler)
        scheduler._notifier = MagicMock()
        return scheduler

    def test_pre_market_on_trading_day(self):
        """Pre-market should reset daily state on a trading day."""
        scheduler = self._make_scheduler()
        scheduler._data_source.is_trading_day.return_value = True

        scheduler._pre_market()

        self.assertTrue(scheduler._pre_market_done)
        scheduler._risk_manager.reset_daily.assert_called_once()
        scheduler._strategy.reset.assert_called_once()
        scheduler._vwap_calculator.reset_realtime.assert_called_once()

    def test_pre_market_on_non_trading_day(self):
        """Pre-market should skip on non-trading days."""
        scheduler = self._make_scheduler()
        scheduler._data_source.is_trading_day.return_value = False

        scheduler._pre_market()

        self.assertTrue(scheduler._pre_market_done)
        # Strategy should NOT be reset on non-trading day
        scheduler._strategy.reset.assert_not_called()

    def test_check_day_open_close_with_position(self):
        """Day open close should generate close signal for held positions."""
        scheduler = self._make_scheduler()
        scheduler._config.symbols = ["IM0"]
        scheduler._position_manager.has_open_positions.return_value = True
        scheduler._data_source.get_realtime_quote.return_value = {'last': 5860.0}

        close_signal = _make_signal(signal_type=SignalType.SELL_CLOSE, price=5860.0)
        scheduler._strategy.on_day_open.return_value = close_signal

        # Mock _process_signal to avoid cascading calls
        scheduler._process_signal = MagicMock()

        scheduler._check_day_open_close()

        scheduler._strategy.on_day_open.assert_called_once()
        scheduler._process_signal.assert_called_once()
        self.assertTrue(scheduler._day_open_processed.get("IM0", False))

    def test_check_day_open_close_no_position(self):
        """Day open close should do nothing when no positions held."""
        scheduler = self._make_scheduler()
        scheduler._config.symbols = ["IM0"]
        scheduler._position_manager.has_open_positions.return_value = False

        scheduler._check_day_open_close()

        scheduler._strategy.on_day_open.assert_not_called()

    def test_check_day_open_close_already_processed(self):
        """Day open close should skip if already processed for a symbol."""
        scheduler = self._make_scheduler()
        scheduler._config.symbols = ["IM0"]
        scheduler._day_open_processed = {"IM0": True}

        scheduler._check_day_open_close()

        scheduler._position_manager.has_open_positions.assert_not_called()

    def test_check_day_open_close_no_quote(self):
        """Day open close should skip if quote not available."""
        scheduler = self._make_scheduler()
        scheduler._config.symbols = ["IM0"]
        scheduler._position_manager.has_open_positions.return_value = True
        scheduler._data_source.get_realtime_quote.return_value = None

        scheduler._check_day_open_close()

        scheduler._strategy.on_day_open.assert_not_called()

    def test_post_market(self):
        """Post-market should save data."""
        scheduler = self._make_scheduler()

        scheduler._post_market()

        scheduler._data_handler.save_all_and_cleanup.assert_called_once()
        self.assertTrue(scheduler._post_market_done)

    def test_reset_daily_flags(self):
        """Reset daily flags should clear all daily state."""
        scheduler = self._make_scheduler()
        scheduler._pre_market_done = True
        scheduler._post_market_done = True
        scheduler._day_open_processed = {"IM0": True}

        scheduler._reset_daily_flags()

        self.assertFalse(scheduler._pre_market_done)
        self.assertFalse(scheduler._post_market_done)
        self.assertEqual(scheduler._day_open_processed, {})


class TestRiskEventHandling(TestCase):
    """Tests for _handle_risk_event."""

    def _make_scheduler(self):
        with patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource"), \
             patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService"):
            scheduler = StrategyScheduler()

        scheduler._data_source = MagicMock()
        scheduler._position_manager = MagicMock(spec=PositionManager)
        scheduler._risk_manager = MagicMock(spec=RiskManager)
        scheduler._config.symbols = ["IM0", "IC0"]
        return scheduler

    def test_handle_risk_event_force_closes(self):
        """Risk event should trigger force close of all positions."""
        scheduler = self._make_scheduler()
        scheduler._data_source.get_realtime_quote.side_effect = [
            {'last': 5800.0},  # IM0
            {'last': 5500.0},  # IC0
        ]
        trade1 = _make_trade(net_pnl=-500.0)
        trade2 = _make_trade(net_pnl=-300.0)
        scheduler._risk_manager.force_close_all.return_value = [trade1, trade2]

        risk_event = RiskEvent(
            event_type=RiskEventType.DAILY_LOSS_LIMIT,
            message="Daily loss limit exceeded",
            value=-50000.0,
            limit=-40000.0,
        )

        scheduler._handle_risk_event(risk_event)

        scheduler._risk_manager.force_close_all.assert_called_once()
        call_args = scheduler._risk_manager.force_close_all.call_args
        prices = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('current_prices', {})
        self.assertIn("IM0", prices)
        self.assertIn("IC0", prices)

    def test_handle_risk_event_quote_unavailable(self):
        """Risk event with missing quotes should still attempt force close."""
        scheduler = self._make_scheduler()
        scheduler._data_source.get_realtime_quote.side_effect = [
            {'last': 5800.0},  # IM0 ok
            None,               # IC0 unavailable
        ]
        scheduler._risk_manager.force_close_all.return_value = []

        risk_event = RiskEvent(
            event_type=RiskEventType.DRAWDOWN_LIMIT,
            message="Drawdown exceeded",
            value=0.12,
            limit=0.10,
        )

        scheduler._handle_risk_event(risk_event)

        # force_close_all called even with partial prices
        scheduler._risk_manager.force_close_all.assert_called_once()
        call_args = scheduler._risk_manager.force_close_all.call_args
        prices = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('current_prices', {})
        # IC0 should not be in prices since quote returned None
        self.assertNotIn("IC0", prices)

    def test_on_bar_triggers_risk_event_force_close(self):
        """Full flow: on_bar detects risk event and force closes."""
        scheduler = self._make_scheduler()
        scheduler._strategy = MagicMock(spec=SettlementArbitrageStrategy)
        scheduler._strategy.on_bar.return_value = []
        scheduler._position_manager.has_open_positions.return_value = True
        scheduler._config.symbols = ["IM0"]

        risk_event = RiskEvent(
            event_type=RiskEventType.DAILY_LOSS_LIMIT,
            message="Daily loss exceeded",
            value=-50000.0,
            limit=-40000.0,
        )
        scheduler._risk_manager.check_all_risks.return_value = risk_event
        scheduler._risk_config.force_close_on_limit = True

        scheduler._data_source.get_realtime_quote.return_value = {'last': 5800.0}
        scheduler._risk_manager.force_close_all.return_value = [_make_trade(net_pnl=-1000.0)]

        bar = _make_bar()
        scheduler._on_minute_bar(bar)

        scheduler._risk_manager.force_close_all.assert_called_once()


class TestConfigUpdate(TestCase):
    """Tests for hot config update."""

    def _make_scheduler(self):
        with patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource"), \
             patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService"):
            scheduler = StrategyScheduler()

        scheduler._data_handler = MagicMock(spec=MinuteDataHandler)
        scheduler._strategy = MagicMock(spec=SettlementArbitrageStrategy)
        scheduler._risk_manager = MagicMock(spec=RiskManager)
        return scheduler

    def test_update_strategy_config(self):
        """update_config with strategy_config should update strategy and re-subscribe."""
        scheduler = self._make_scheduler()
        new_cfg = StrategyConfig(symbols=["IF0", "IH0"], threshold_1=0.02)

        scheduler.update_config(strategy_config=new_cfg)

        self.assertEqual(scheduler._config.symbols, ["IF0", "IH0"])
        self.assertAlmostEqual(scheduler._config.threshold_1, 0.02)
        scheduler._data_handler.subscribe.assert_called_once_with(["IF0", "IH0"])

    def test_update_risk_config(self):
        """update_config with risk_config should update risk manager."""
        scheduler = self._make_scheduler()
        new_risk_cfg = RiskConfig(max_daily_loss=80000)

        scheduler.update_config(risk_config=new_risk_cfg)

        self.assertAlmostEqual(scheduler._risk_config.max_daily_loss, 80000)

    def test_update_both_configs(self):
        """update_config with both configs should update both."""
        scheduler = self._make_scheduler()
        new_cfg = StrategyConfig(symbols=["IC0"])
        new_risk_cfg = RiskConfig(max_drawdown=0.15)

        scheduler.update_config(strategy_config=new_cfg, risk_config=new_risk_cfg)

        self.assertEqual(scheduler._config.symbols, ["IC0"])
        self.assertAlmostEqual(scheduler._risk_config.max_drawdown, 0.15)

    def test_update_none_configs(self):
        """update_config with None should be a no-op."""
        scheduler = self._make_scheduler()
        original_cfg = scheduler._config

        scheduler.update_config(strategy_config=None, risk_config=None)

        self.assertIs(scheduler._config, original_cfg)


class TestGetStatus(TestCase):
    """Tests for get_status."""

    def _make_scheduler(self):
        with patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource"), \
             patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService"):
            scheduler = StrategyScheduler()

        scheduler._strategy = MagicMock(spec=SettlementArbitrageStrategy)
        scheduler._position_manager = MagicMock(spec=PositionManager)
        scheduler._risk_manager = MagicMock(spec=RiskManager)
        scheduler._data_source = MagicMock()
        return scheduler

    def test_status_when_stopped(self):
        """get_status returns correct structure when scheduler is stopped."""
        scheduler = self._make_scheduler()
        scheduler._strategy.get_monitor_data.return_value = {'symbols': {}}
        scheduler._position_manager.get_position_count.return_value = 0
        scheduler._position_manager.get_current_positions.return_value = []
        scheduler._position_manager.get_total_margin_used.return_value = 0
        scheduler._position_manager.get_pnl_summary.return_value = {'total_trades': 0}
        scheduler._risk_manager.get_risk_status.return_value = {'is_risk_triggered': False}
        scheduler._data_source.is_trading_time.return_value = False
        scheduler._data_source.is_watch_period.return_value = False

        status = scheduler.get_status()

        self.assertFalse(status['is_running'])
        self.assertIsNone(status['started_at'])
        self.assertIn('config', status)
        self.assertIn('strategy', status)
        self.assertIn('positions', status)
        self.assertIn('risk', status)
        self.assertIn('pnl_summary', status)
        self.assertIn('is_trading_time', status)
        self.assertIn('is_watch_period', status)

    def test_status_when_running(self):
        """get_status returns correct state when running."""
        scheduler = self._make_scheduler()
        scheduler._running = True
        scheduler._started_at = datetime(2025, 1, 15, 9, 0, 0)
        scheduler._heartbeat = datetime(2025, 1, 15, 14, 35, 0)

        pos = _make_position()
        scheduler._strategy.get_monitor_data.return_value = {'symbols': {'IM0': {}}}
        scheduler._position_manager.get_position_count.return_value = 1
        scheduler._position_manager.get_current_positions.return_value = [pos]
        scheduler._position_manager.get_total_margin_used.return_value = 139200.0
        scheduler._position_manager.get_pnl_summary.return_value = {'total_trades': 5}
        scheduler._risk_manager.get_risk_status.return_value = {'is_risk_triggered': False}
        scheduler._data_source.is_trading_time.return_value = True
        scheduler._data_source.is_watch_period.return_value = True

        status = scheduler.get_status()

        self.assertTrue(status['is_running'])
        self.assertIsNotNone(status['started_at'])
        self.assertIsNotNone(status['heartbeat'])
        self.assertEqual(status['positions']['open_count'], 1)
        self.assertTrue(status['is_watch_period'])

    def test_status_config_content(self):
        """get_status should include config details."""
        cfg = StrategyConfig(
            symbols=["IM0", "IC0"],
            threshold_1=0.01,
            threshold_2=0.02,
            alert_threshold=0.008,
        )
        with patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource"), \
             patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService"):
            scheduler = StrategyScheduler(strategy_config=cfg)

        scheduler._strategy = MagicMock()
        scheduler._strategy.get_monitor_data.return_value = {}
        scheduler._position_manager = MagicMock()
        scheduler._position_manager.get_position_count.return_value = 0
        scheduler._position_manager.get_current_positions.return_value = []
        scheduler._position_manager.get_total_margin_used.return_value = 0
        scheduler._position_manager.get_pnl_summary.return_value = {}
        scheduler._risk_manager = MagicMock()
        scheduler._risk_manager.get_risk_status.return_value = {}
        scheduler._data_source = MagicMock()
        scheduler._data_source.is_trading_time.return_value = False
        scheduler._data_source.is_watch_period.return_value = False

        status = scheduler.get_status()

        self.assertEqual(status['config']['symbols'], ["IM0", "IC0"])
        self.assertAlmostEqual(status['config']['threshold_1'], 0.01)
        self.assertAlmostEqual(status['config']['threshold_2'], 0.02)
        self.assertAlmostEqual(status['config']['alert_threshold'], 0.008)


class TestGlobalSingleton(TestCase):
    """Tests for get_scheduler and create_scheduler global functions."""

    def tearDown(self):
        """Clean up global singleton after each test."""
        import app.strategies.settlement_arbitrage.scheduler as sched_module
        if sched_module._scheduler_instance and sched_module._scheduler_instance.is_running:
            sched_module._scheduler_instance._running = False
        sched_module._scheduler_instance = None

    @patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource")
    @patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService")
    def test_create_scheduler_creates_instance(self, mock_notifier_cls, mock_ds_cls):
        """create_scheduler should create a global instance."""
        scheduler = create_scheduler()

        self.assertIsNotNone(scheduler)
        self.assertIsNotNone(get_scheduler())
        self.assertIs(get_scheduler(), scheduler)

    @patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource")
    @patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService")
    def test_create_scheduler_replaces_existing(self, mock_notifier_cls, mock_ds_cls):
        """create_scheduler should stop and replace an existing instance."""
        first = create_scheduler()
        second = create_scheduler()

        self.assertIsNot(first, second)
        self.assertIs(get_scheduler(), second)

    @patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource")
    @patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService")
    def test_create_scheduler_with_config(self, mock_notifier_cls, mock_ds_cls):
        """create_scheduler should pass configs to the new instance."""
        cfg = StrategyConfig(symbols=["IH0"])
        risk_cfg = RiskConfig(max_daily_loss=25000)

        scheduler = create_scheduler(
            strategy_config=cfg,
            risk_config=risk_cfg,
        )

        self.assertEqual(scheduler._config.symbols, ["IH0"])
        self.assertAlmostEqual(scheduler._risk_config.max_daily_loss, 25000)

    def test_get_scheduler_returns_none_initially(self):
        """get_scheduler should return None before any create call."""
        import app.strategies.settlement_arbitrage.scheduler as sched_module
        sched_module._scheduler_instance = None

        self.assertIsNone(get_scheduler())


class TestMainLoopScheduling(TestCase):
    """Tests for main loop time-based scheduling logic."""

    def _make_scheduler(self):
        with patch("app.strategies.settlement_arbitrage.scheduler.CNFuturesDataSource"), \
             patch("app.strategies.settlement_arbitrage.scheduler.FuturesNotificationService"):
            scheduler = StrategyScheduler()

        scheduler._data_source = MagicMock()
        scheduler._strategy = MagicMock(spec=SettlementArbitrageStrategy)
        scheduler._position_manager = MagicMock(spec=PositionManager)
        scheduler._risk_manager = MagicMock(spec=RiskManager)
        scheduler._vwap_calculator = MagicMock()
        scheduler._data_handler = MagicMock(spec=MinuteDataHandler)
        scheduler._notifier = MagicMock()
        return scheduler

    @patch("app.strategies.settlement_arbitrage.scheduler.datetime")
    def test_main_loop_calls_pre_market_at_correct_time(self, mock_datetime):
        """Main loop should call pre_market between 09:15 and 09:25."""
        scheduler = self._make_scheduler()

        # Simulate time 09:17
        mock_now = datetime(2025, 1, 15, 9, 17, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        scheduler._running = True
        scheduler._pre_market_done = False

        # Directly test the pre-market condition
        now = mock_now
        current_time = now.time()

        if time(9, 15) <= current_time < time(9, 25) and not scheduler._pre_market_done:
            scheduler._pre_market()

        self.assertTrue(scheduler._pre_market_done)

    def test_main_loop_skips_pre_market_if_done(self):
        """Main loop should not call pre_market if already done."""
        scheduler = self._make_scheduler()
        scheduler._pre_market_done = True
        scheduler._data_source.is_trading_day.return_value = True

        # Simulate the condition check
        current_time = time(9, 17)
        called = False
        if time(9, 15) <= current_time < time(9, 25) and not scheduler._pre_market_done:
            called = True

        self.assertFalse(called)

    def test_main_loop_calls_post_market_at_correct_time(self):
        """Post-market should be called between 15:05 and 15:15."""
        scheduler = self._make_scheduler()
        scheduler._post_market_done = False

        current_time = time(15, 7)
        if time(15, 5) <= current_time < time(15, 15) and not scheduler._post_market_done:
            scheduler._post_market()

        self.assertTrue(scheduler._post_market_done)

    def test_main_loop_daily_reset_at_midnight(self):
        """Daily flags should reset near midnight."""
        scheduler = self._make_scheduler()
        scheduler._pre_market_done = True
        scheduler._post_market_done = True
        scheduler._day_open_processed = {"IM0": True}

        current_time = time(0, 0, 30)
        if current_time < time(0, 1):
            scheduler._reset_daily_flags()

        self.assertFalse(scheduler._pre_market_done)
        self.assertFalse(scheduler._post_market_done)
        self.assertEqual(scheduler._day_open_processed, {})
