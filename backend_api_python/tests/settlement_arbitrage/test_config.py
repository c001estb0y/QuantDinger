# Settlement Arbitrage Strategy - Config Unit Tests

"""
Unit tests for config.py module.
Tests StrategyConfig, RiskConfig, and BacktestConfig dataclasses.
"""

import unittest
from datetime import time

from app.strategies.settlement_arbitrage.config import (
    StrategyConfig, RiskConfig, BacktestConfig
)


class TestStrategyConfig(unittest.TestCase):
    """Tests for StrategyConfig dataclass."""

    def test_default_values(self):
        """Default config should have sensible values."""
        config = StrategyConfig()
        self.assertEqual(config.symbols, ["IM0", "IC0"])
        self.assertEqual(config.watch_start, time(14, 30))
        self.assertEqual(config.watch_end, time(15, 0))
        self.assertEqual(config.threshold_1, 0.01)
        self.assertEqual(config.threshold_2, 0.02)
        self.assertEqual(config.alert_threshold, 0.008)
        self.assertEqual(config.position_size_1, 1)
        self.assertEqual(config.position_size_2, 1)
        self.assertEqual(config.max_position_per_symbol, 2)

    def test_custom_values(self):
        """Config should accept custom parameters."""
        config = StrategyConfig(
            symbols=["IF0", "IH0"],
            threshold_1=0.015,
            threshold_2=0.03,
            position_size_1=2,
            position_size_2=3,
            max_position_per_symbol=5,
        )
        self.assertEqual(config.symbols, ["IF0", "IH0"])
        self.assertEqual(config.threshold_1, 0.015)
        self.assertEqual(config.threshold_2, 0.03)
        self.assertEqual(config.position_size_1, 2)
        self.assertEqual(config.position_size_2, 3)
        self.assertEqual(config.max_position_per_symbol, 5)

    def test_validate_success(self):
        """Valid config should pass validation."""
        config = StrategyConfig()
        self.assertTrue(config.validate())

    def test_validate_empty_symbols(self):
        """Should reject empty symbols list."""
        config = StrategyConfig(symbols=[])
        with self.assertRaises(ValueError):
            config.validate()

    def test_validate_threshold_1_too_low(self):
        """Should reject threshold_1 <= 0."""
        config = StrategyConfig(threshold_1=0)
        with self.assertRaises(ValueError):
            config.validate()

    def test_validate_threshold_1_too_high(self):
        """Should reject threshold_1 >= 1."""
        config = StrategyConfig(threshold_1=1.0)
        with self.assertRaises(ValueError):
            config.validate()

    def test_validate_threshold_2_not_greater_than_1(self):
        """Should reject threshold_2 <= threshold_1."""
        config = StrategyConfig(threshold_1=0.02, threshold_2=0.01)
        with self.assertRaises(ValueError):
            config.validate()

    def test_validate_position_size_zero(self):
        """Should reject position_size_1 <= 0."""
        config = StrategyConfig(position_size_1=0)
        with self.assertRaises(ValueError):
            config.validate()

    def test_notification_defaults(self):
        """Default notification settings should be correct."""
        config = StrategyConfig()
        self.assertEqual(config.notification_channels, ["telegram"])
        self.assertIsNone(config.telegram_chat_id)
        self.assertIsNone(config.email_address)
        self.assertTrue(config.notify_on_entry)
        self.assertTrue(config.notify_on_exit)
        self.assertTrue(config.notify_on_alert)
        self.assertFalse(config.notify_daily_report)


class TestRiskConfig(unittest.TestCase):
    """Tests for RiskConfig dataclass."""

    def test_default_values(self):
        """Default risk config should have sensible values."""
        config = RiskConfig()
        self.assertEqual(config.max_daily_loss, 10000.0)
        self.assertEqual(config.max_drawdown, 0.05)
        self.assertTrue(config.force_close_on_limit)
        self.assertEqual(config.max_total_position, 4)

    def test_validate_success(self):
        """Valid risk config should pass validation."""
        config = RiskConfig()
        self.assertTrue(config.validate())

    def test_validate_max_daily_loss_zero(self):
        """Should reject max_daily_loss <= 0."""
        config = RiskConfig(max_daily_loss=0)
        with self.assertRaises(ValueError):
            config.validate()

    def test_validate_max_daily_loss_negative(self):
        """Should reject negative max_daily_loss."""
        config = RiskConfig(max_daily_loss=-1000)
        with self.assertRaises(ValueError):
            config.validate()

    def test_validate_drawdown_too_low(self):
        """Should reject max_drawdown <= 0."""
        config = RiskConfig(max_drawdown=0)
        with self.assertRaises(ValueError):
            config.validate()

    def test_validate_drawdown_too_high(self):
        """Should reject max_drawdown >= 1."""
        config = RiskConfig(max_drawdown=1.0)
        with self.assertRaises(ValueError):
            config.validate()

    def test_custom_risk_config(self):
        """Should accept custom risk parameters."""
        config = RiskConfig(
            max_daily_loss=20000,
            max_drawdown=0.10,
            force_close_on_limit=False,
            max_total_position=8,
        )
        self.assertEqual(config.max_daily_loss, 20000)
        self.assertEqual(config.max_drawdown, 0.10)
        self.assertFalse(config.force_close_on_limit)
        self.assertEqual(config.max_total_position, 8)


class TestBacktestConfig(unittest.TestCase):
    """Tests for BacktestConfig dataclass."""

    def test_default_values(self):
        """Default backtest config should have sensible values."""
        config = BacktestConfig()
        self.assertEqual(config.initial_capital, 500000.0)
        self.assertTrue(config.use_default_commission)
        self.assertEqual(config.slippage_points, 0.0)
        self.assertTrue(config.use_minute_data)

    def test_custom_backtest_config(self):
        """Should accept custom backtest parameters."""
        config = BacktestConfig(
            initial_capital=1000000.0,
            use_default_commission=False,
            slippage_points=2.0,
            use_minute_data=False,
        )
        self.assertEqual(config.initial_capital, 1000000.0)
        self.assertFalse(config.use_default_commission)
        self.assertEqual(config.slippage_points, 2.0)
        self.assertFalse(config.use_minute_data)


if __name__ == '__main__':
    unittest.main()
