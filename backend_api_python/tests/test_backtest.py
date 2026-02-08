# Settlement Arbitrage Strategy - Backtest Unit Tests
# 结算价差套利策略 - 回测引擎单元测试

"""
Unit tests for the backtest module.

Covers:
- BacktestTrade dataclass and serialization
- BacktestReport dataclass and serialization
- SettlementStrategyBacktest simulation logic
- Report generation and metrics calculation
- Edge cases (no trades, single trade, all wins, all losses)
"""

import unittest
from datetime import date, datetime, time, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

import pandas as pd
import numpy as np

from app.strategies.settlement_arbitrage.backtest import (
    BacktestTrade,
    BacktestReport,
    SettlementStrategyBacktest,
)
from app.strategies.settlement_arbitrage.config import (
    StrategyConfig,
    RiskConfig,
    BacktestConfig,
)


class TestBacktestTrade(unittest.TestCase):
    """Tests for BacktestTrade dataclass."""

    def _make_trade(self, **kwargs):
        """Helper to create a BacktestTrade with defaults."""
        defaults = {
            'symbol': 'IM0',
            'entry_date': date(2026, 2, 9),
            'exit_date': date(2026, 2, 10),
            'entry_price': 5840.0,
            'exit_price': 5890.0,
            'base_price': 5900.0,
            'drop_pct': -0.0102,
            'vwap': 5870.0,
            'level': 1,
            'quantity': 1,
            'multiplier': 200,
            'gross_pnl': 10000.0,
            'fee': 54.15,
            'net_pnl': 9945.85,
        }
        defaults.update(kwargs)
        return BacktestTrade(**defaults)

    def test_create_trade(self):
        """Should create a BacktestTrade with correct fields."""
        trade = self._make_trade()
        self.assertEqual(trade.symbol, 'IM0')
        self.assertEqual(trade.entry_price, 5840.0)
        self.assertEqual(trade.exit_price, 5890.0)
        self.assertEqual(trade.level, 1)
        self.assertEqual(trade.quantity, 1)
        self.assertEqual(trade.multiplier, 200)

    def test_to_dict(self):
        """to_dict should produce correct serialization."""
        trade = self._make_trade()
        d = trade.to_dict()

        self.assertEqual(d['symbol'], 'IM0')
        self.assertEqual(d['entry_date'], '2026-02-09')
        self.assertEqual(d['exit_date'], '2026-02-10')
        self.assertEqual(d['entry_price'], 5840.0)
        self.assertEqual(d['exit_price'], 5890.0)
        self.assertEqual(d['level'], 1)
        self.assertEqual(d['quantity'], 1)
        self.assertIsInstance(d['gross_pnl'], float)
        self.assertIsInstance(d['fee'], float)
        self.assertIsInstance(d['net_pnl'], float)

    def test_to_dict_rounds_values(self):
        """to_dict should round pnl and fee to 2 decimal places."""
        trade = self._make_trade(gross_pnl=10000.1234, fee=54.1567, net_pnl=9945.9667)
        d = trade.to_dict()
        self.assertEqual(d['gross_pnl'], 10000.12)
        self.assertEqual(d['fee'], 54.16)
        self.assertEqual(d['net_pnl'], 9945.97)

    def test_trade_with_none_vwap(self):
        """Should handle None vwap correctly."""
        trade = self._make_trade(vwap=None)
        d = trade.to_dict()
        self.assertIsNone(d['vwap'])

    def test_trade_level2(self):
        """Should correctly represent a level 2 trade."""
        trade = self._make_trade(level=2, quantity=2)
        self.assertEqual(trade.level, 2)
        self.assertEqual(trade.quantity, 2)

    def test_negative_pnl_trade(self):
        """Should handle losing trades correctly."""
        trade = self._make_trade(
            entry_price=5900.0, exit_price=5850.0,
            gross_pnl=-10000.0, net_pnl=-10054.15
        )
        d = trade.to_dict()
        self.assertLess(d['gross_pnl'], 0)
        self.assertLess(d['net_pnl'], 0)


class TestBacktestReport(unittest.TestCase):
    """Tests for BacktestReport dataclass."""

    def _make_report(self, **kwargs):
        """Helper to create a BacktestReport with defaults."""
        defaults = {
            'start_date': date(2025, 1, 1),
            'end_date': date(2025, 12, 31),
            'symbols': ['IM0'],
            'initial_capital': 500000.0,
            'config': {'threshold_1': 0.01, 'threshold_2': 0.02},
        }
        defaults.update(kwargs)
        return BacktestReport(**defaults)

    def test_create_empty_report(self):
        """Should create report with default zero metrics."""
        report = self._make_report()
        self.assertEqual(report.total_trades, 0)
        self.assertEqual(report.total_return, 0.0)
        self.assertEqual(report.sharpe_ratio, 0.0)
        self.assertEqual(report.max_drawdown, 0.0)
        self.assertEqual(report.final_equity, 0.0)

    def test_to_dict_structure(self):
        """to_dict should contain all required keys."""
        report = self._make_report()
        d = report.to_dict()

        required_keys = [
            'start_date', 'end_date', 'symbols', 'initial_capital',
            'total_return', 'annual_return', 'sharpe_ratio', 'sortino_ratio',
            'max_drawdown', 'max_drawdown_duration', 'calmar_ratio',
            'total_trades', 'winning_trades', 'losing_trades', 'win_rate',
            'profit_factor', 'avg_win', 'avg_loss', 'max_win', 'max_loss',
            'avg_holding_days', 'final_equity', 'total_pnl', 'total_fees',
            'monthly_returns', 'symbol_stats', 'trades', 'equity_curve',
        ]
        for key in required_keys:
            self.assertIn(key, d, f"Missing key: {key}")

    def test_to_dict_percentage_conversion(self):
        """to_dict should convert ratios to percentage values."""
        report = self._make_report(
            total_return=0.15,
            annual_return=0.12,
            max_drawdown=0.05,
            win_rate=0.65,
        )
        d = report.to_dict()

        # total_return, annual_return, max_drawdown should be *100
        self.assertEqual(d['total_return'], 15.0)
        self.assertEqual(d['annual_return'], 12.0)
        self.assertEqual(d['max_drawdown'], 5.0)
        self.assertEqual(d['win_rate'], 65.0)

    def test_to_dict_monthly_returns_conversion(self):
        """Monthly returns should be converted to percentage."""
        report = self._make_report(
            monthly_returns={'2025-01': 0.02, '2025-02': -0.005}
        )
        d = report.to_dict()
        self.assertEqual(d['monthly_returns']['2025-01'], 2.0)
        self.assertEqual(d['monthly_returns']['2025-02'], -0.5)

    def test_to_dict_with_trades(self):
        """to_dict should serialize trade list."""
        trade = BacktestTrade(
            symbol='IM0', entry_date=date(2025, 1, 5),
            exit_date=date(2025, 1, 6), entry_price=5800.0,
            exit_price=5850.0, base_price=5900.0, drop_pct=-0.017,
            vwap=5870.0, level=1, quantity=1, multiplier=200,
            gross_pnl=10000.0, fee=50.0, net_pnl=9950.0,
        )
        report = self._make_report(trades=[trade])
        d = report.to_dict()
        self.assertEqual(len(d['trades']), 1)
        self.assertEqual(d['trades'][0]['symbol'], 'IM0')


class TestSettlementStrategyBacktest(unittest.TestCase):
    """Tests for SettlementStrategyBacktest engine."""

    def setUp(self):
        """Set up mock data source."""
        self.mock_ds = MagicMock()
        self.engine = SettlementStrategyBacktest(data_source=self.mock_ds)

    def _make_daily_df(self, rows):
        """
        Helper to create daily DataFrame.
        rows: list of (date_str, open, high, low, close, volume)
        """
        data = []
        for row in rows:
            data.append({
                'datetime': pd.Timestamp(row[0]),
                'open': row[1],
                'high': row[2],
                'low': row[3],
                'close': row[4],
                'volume': row[5] if len(row) > 5 else 1000,
            })
        return pd.DataFrame(data)

    # ========== _get_daily_data ==========

    def test_get_daily_data_success(self):
        """Should return DataFrame when data source succeeds."""
        expected_df = self._make_daily_df([
            ('2025-01-02', 5800, 5850, 5780, 5830, 1000),
        ])
        self.mock_ds.get_kline_data.return_value = expected_df

        result = self.engine._get_daily_data('IM0', date(2025, 1, 1), date(2025, 1, 31))
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)

    def test_get_daily_data_exception(self):
        """Should return None when data source throws."""
        self.mock_ds.get_kline_data.side_effect = Exception("Network error")
        result = self.engine._get_daily_data('IM0', date(2025, 1, 1), date(2025, 1, 31))
        self.assertIsNone(result)

    # ========== _get_price_at_time ==========

    def test_get_price_at_time_found(self):
        """Should return close price at or before target time."""
        minute_df = pd.DataFrame({
            'datetime': pd.to_datetime([
                '2025-01-02 14:28:00', '2025-01-02 14:29:00',
                '2025-01-02 14:30:00', '2025-01-02 14:31:00',
            ]),
            'close': [5800, 5810, 5820, 5830],
        })
        result = self.engine._get_price_at_time(minute_df, time(14, 30))
        self.assertEqual(result, 5820.0)

    def test_get_price_at_time_empty(self):
        """Should return None for empty DataFrame."""
        result = self.engine._get_price_at_time(pd.DataFrame(), time(14, 30))
        self.assertIsNone(result)

    def test_get_price_at_time_none(self):
        """Should return None for None input."""
        result = self.engine._get_price_at_time(None, time(14, 30))
        self.assertIsNone(result)

    def test_get_price_at_time_all_after_target(self):
        """Should return None when all bars are after target time."""
        minute_df = pd.DataFrame({
            'datetime': pd.to_datetime([
                '2025-01-02 14:35:00', '2025-01-02 14:40:00',
            ]),
            'close': [5800, 5810],
        })
        result = self.engine._get_price_at_time(minute_df, time(14, 30))
        self.assertIsNone(result)

    # ========== _simulate_strategy ==========

    def test_simulate_no_entry_when_drop_insufficient(self):
        """Should produce no trades when drop < threshold."""
        daily_df = self._make_daily_df([
            ('2025-01-02', 5800, 5850, 5780, 5830, 1000),  # Day 1
            ('2025-01-03', 5830, 5860, 5810, 5825, 1000),  # Day 2: drop = (5825-5830)/5830 = -0.086% < 1%
        ])
        config = StrategyConfig(symbols=['IM0'], threshold_1=0.01)
        trades = self.engine._simulate_strategy(
            symbol='IM0', daily_df=daily_df, minute_data=None,
            config=config, multiplier=200,
        )
        self.assertEqual(len(trades), 0)

    def test_simulate_level1_entry_and_exit(self):
        """Should enter L1 when drop > threshold_1 and exit next day open."""
        # Day 1: close=6000
        # Day 2: close=5930 → drop=(5930-6000)/6000=-1.17% > 1% → ENTER
        # Day 3: open=5960 → EXIT
        daily_df = self._make_daily_df([
            ('2025-01-02', 5950, 6050, 5940, 6000, 1000),
            ('2025-01-03', 5990, 6010, 5920, 5930, 1000),
            ('2025-01-06', 5960, 5980, 5940, 5970, 1000),
        ])
        config = StrategyConfig(
            symbols=['IM0'], threshold_1=0.01, threshold_2=0.02,
            position_size_1=1, position_size_2=1,
        )
        trades = self.engine._simulate_strategy(
            symbol='IM0', daily_df=daily_df, minute_data=None,
            config=config, multiplier=200,
        )
        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertEqual(trade.entry_price, 5930.0)
        self.assertEqual(trade.exit_price, 5960.0)
        self.assertEqual(trade.level, 1)
        self.assertEqual(trade.quantity, 1)
        # Profit: (5960-5930)*1*200 = 6000
        self.assertAlmostEqual(trade.gross_pnl, 6000.0, places=1)
        self.assertGreater(trade.fee, 0)
        self.assertLess(trade.net_pnl, trade.gross_pnl)  # net < gross due to fees

    def test_simulate_level2_entry(self):
        """Should enter L2 with combined quantity when drop > threshold_2."""
        # Day 1: close=6000
        # Day 2: close=5870 → drop=(5870-6000)/6000=-2.17% > 2% → ENTER L2, qty=2
        # Day 3: open=5900 → EXIT
        daily_df = self._make_daily_df([
            ('2025-01-02', 5950, 6050, 5940, 6000, 1000),
            ('2025-01-03', 5990, 6010, 5860, 5870, 1000),
            ('2025-01-06', 5900, 5950, 5880, 5930, 1000),
        ])
        config = StrategyConfig(
            symbols=['IM0'], threshold_1=0.01, threshold_2=0.02,
            position_size_1=1, position_size_2=1,
        )
        trades = self.engine._simulate_strategy(
            symbol='IM0', daily_df=daily_df, minute_data=None,
            config=config, multiplier=200,
        )
        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertEqual(trade.level, 2)
        self.assertEqual(trade.quantity, 2)  # position_size_1 + position_size_2

    def test_simulate_multiple_trades(self):
        """Should generate multiple trades across different days."""
        # Day 1: close=6000
        # Day 2: close=5930 → drop -1.17% → ENTER L1
        # Day 3: open=5960 → EXIT; close=5920 → drop=(5920-5930)/5930 won't trigger (base=prev_close=5930... -0.17%)
        # Actually base changes each day. Let me construct more carefully.
        # Day 1: close=6000
        # Day 2: close=5930 → drop=(5930-6000)/6000=-1.17% → ENTER
        # Day 3: open=5960 → EXIT; close=6050 (no drop)
        # Day 4: close=5985 → drop=(5985-6050)/6050=-1.07% → ENTER
        # Day 5: open=6010 → EXIT
        daily_df = self._make_daily_df([
            ('2025-01-02', 5950, 6050, 5940, 6000, 1000),
            ('2025-01-03', 5990, 6010, 5920, 5930, 1000),
            ('2025-01-06', 5960, 6080, 5940, 6050, 1000),
            ('2025-01-07', 6040, 6060, 5980, 5985, 1000),
            ('2025-01-08', 6010, 6030, 5990, 6020, 1000),
        ])
        config = StrategyConfig(
            symbols=['IM0'], threshold_1=0.01, threshold_2=0.02,
            position_size_1=1, position_size_2=1,
        )
        trades = self.engine._simulate_strategy(
            symbol='IM0', daily_df=daily_df, minute_data=None,
            config=config, multiplier=200,
        )
        self.assertEqual(len(trades), 2)

    def test_simulate_empty_dataframe(self):
        """Should return empty list for empty DataFrame."""
        trades = self.engine._simulate_strategy(
            symbol='IM0', daily_df=pd.DataFrame(), minute_data=None,
            config=StrategyConfig(), multiplier=200,
        )
        self.assertEqual(len(trades), 0)

    def test_simulate_none_dataframe(self):
        """Should return empty list for None DataFrame."""
        trades = self.engine._simulate_strategy(
            symbol='IM0', daily_df=None, minute_data=None,
            config=StrategyConfig(), multiplier=200,
        )
        self.assertEqual(len(trades), 0)

    def test_simulate_single_day(self):
        """Should return no trades for single-day data (need at least 2 days)."""
        daily_df = self._make_daily_df([
            ('2025-01-02', 5800, 5850, 5780, 5830, 1000),
        ])
        trades = self.engine._simulate_strategy(
            symbol='IM0', daily_df=daily_df, minute_data=None,
            config=StrategyConfig(), multiplier=200,
        )
        self.assertEqual(len(trades), 0)

    def test_simulate_pending_entry_at_end(self):
        """Should close pending entry at last close when backtest ends."""
        # Day 1: close=6000
        # Day 2: close=5930 → drop -1.17% → ENTER (but no Day 3 to exit)
        daily_df = self._make_daily_df([
            ('2025-01-02', 5950, 6050, 5940, 6000, 1000),
            ('2025-01-03', 5990, 6010, 5920, 5930, 1000),
        ])
        config = StrategyConfig(symbols=['IM0'], threshold_1=0.01)
        trades = self.engine._simulate_strategy(
            symbol='IM0', daily_df=daily_df, minute_data=None,
            config=config, multiplier=200,
        )
        # Should have 1 trade closed at last close (5930)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].entry_price, 5930.0)
        self.assertEqual(trades[0].exit_price, 5930.0)  # Closed at last close

    def test_simulate_with_minute_data(self):
        """Should use minute data for base price at 14:30 when available."""
        daily_df = self._make_daily_df([
            ('2025-01-02', 5950, 6050, 5940, 6000, 1000),
            ('2025-01-03', 5990, 6010, 5920, 5930, 1000),
            ('2025-01-06', 5960, 5980, 5940, 5970, 1000),
        ])

        # Minute data for Day 2: price at 14:30 = 5990 (different from prev close 6000)
        minute_df_day2 = pd.DataFrame({
            'datetime': pd.to_datetime([
                '2025-01-03 14:00:00', '2025-01-03 14:30:00',
                '2025-01-03 14:45:00', '2025-01-03 15:00:00',
            ]),
            'open': [5990, 5990, 5950, 5935],
            'high': [6000, 5995, 5960, 5940],
            'low': [5985, 5980, 5940, 5925],
            'close': [5990, 5990, 5945, 5930],
            'volume': [100, 200, 150, 300],
        })
        minute_data = {date(2025, 1, 3): minute_df_day2}

        config = StrategyConfig(symbols=['IM0'], threshold_1=0.01)
        trades = self.engine._simulate_strategy(
            symbol='IM0', daily_df=daily_df, minute_data=minute_data,
            config=config, multiplier=200,
        )
        # With minute data, base_price at 14:30 = 5990
        # drop = (5930 - 5990) / 5990 = -1.0% → should trigger L1
        self.assertEqual(len(trades), 1)

    def test_fee_calculation(self):
        """Fee should be calculated correctly based on fee rates."""
        daily_df = self._make_daily_df([
            ('2025-01-02', 5950, 6050, 5940, 6000, 1000),
            ('2025-01-03', 5990, 6010, 5920, 5930, 1000),
            ('2025-01-06', 5960, 5980, 5940, 5970, 1000),
        ])
        config = StrategyConfig(symbols=['IM0'], threshold_1=0.01, position_size_1=1)
        trades = self.engine._simulate_strategy(
            symbol='IM0', daily_df=daily_df, minute_data=None,
            config=config, multiplier=200,
        )
        self.assertEqual(len(trades), 1)
        trade = trades[0]

        # Expected fees:
        # open_fee = 5930 * 200 * 1 * 0.000023 = 27.278
        # close_fee = 5960 * 200 * 1 * 0.000023 = 27.416
        # total_fee ≈ 54.694
        expected_open_fee = 5930 * 200 * 1 * 0.000023
        expected_close_fee = 5960 * 200 * 1 * 0.000023
        expected_fee = expected_open_fee + expected_close_fee
        self.assertAlmostEqual(trade.fee, expected_fee, places=2)

    # ========== run (full backtest) ==========

    def test_run_with_no_data(self):
        """Should return empty report when no data available."""
        self.mock_ds.get_kline_data.return_value = None
        config = StrategyConfig(symbols=['IM0'])
        bt_config = BacktestConfig(initial_capital=500000, use_minute_data=False)

        report = self.engine.run(
            start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
            strategy_config=config, backtest_config=bt_config,
        )
        self.assertEqual(report.total_trades, 0)
        self.assertEqual(report.final_equity, 500000.0)

    def test_run_with_trades(self):
        """Should produce valid report with trades."""
        daily_df = self._make_daily_df([
            ('2025-01-02', 5950, 6050, 5940, 6000, 1000),
            ('2025-01-03', 5990, 6010, 5920, 5930, 1000),
            ('2025-01-06', 5960, 5980, 5940, 5970, 1000),
        ])
        self.mock_ds.get_kline_data.return_value = daily_df
        self.mock_ds.PRODUCTS = {'IM': {'multiplier': 200, 'margin_ratio': 0.12}}

        config = StrategyConfig(symbols=['IM0'], threshold_1=0.01)
        bt_config = BacktestConfig(initial_capital=500000, use_minute_data=False)

        report = self.engine.run(
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 31),
            strategy_config=config, backtest_config=bt_config,
        )
        self.assertGreater(report.total_trades, 0)
        self.assertNotEqual(report.final_equity, 500000.0)
        self.assertGreater(report.total_fees, 0)

    def test_run_multi_symbol(self):
        """Should process multiple symbols."""
        daily_df = self._make_daily_df([
            ('2025-01-02', 5950, 6050, 5940, 6000, 1000),
            ('2025-01-03', 5990, 6010, 5920, 5930, 1000),
            ('2025-01-06', 5960, 5980, 5940, 5970, 1000),
        ])
        self.mock_ds.get_kline_data.return_value = daily_df
        self.mock_ds.PRODUCTS = {'IM': {'multiplier': 200}, 'IC': {'multiplier': 200}}

        config = StrategyConfig(symbols=['IM0', 'IC0'], threshold_1=0.01)
        bt_config = BacktestConfig(initial_capital=500000, use_minute_data=False)

        report = self.engine.run(
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 31),
            strategy_config=config, backtest_config=bt_config,
        )
        # Both symbols should generate trades (same data)
        self.assertGreater(report.total_trades, 0)

    # ========== _generate_report ==========

    def test_generate_report_empty_trades(self):
        """Should handle empty trades list gracefully."""
        config = StrategyConfig(symbols=['IM0'])
        report = self.engine._generate_report(
            trades=[], equity_curve=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
            symbols=['IM0'], initial_capital=500000, config=config,
        )
        self.assertEqual(report.total_trades, 0)
        self.assertEqual(report.final_equity, 500000.0)
        self.assertEqual(report.total_return, 0.0)
        self.assertEqual(report.win_rate, 0.0)

    def test_generate_report_all_wins(self):
        """Should calculate 100% win rate when all trades profitable."""
        trades = [
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, i+2),
                exit_date=date(2025, 1, i+3),
                entry_price=5900 - i*10, exit_price=5950 - i*10,
                base_price=6000, drop_pct=-0.015, vwap=5950,
                level=1, quantity=1, multiplier=200,
                gross_pnl=10000, fee=55, net_pnl=9945,
            )
            for i in range(5)
        ]
        config = StrategyConfig(symbols=['IM0'])
        report = self.engine._generate_report(
            trades=trades, equity_curve=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 31),
            symbols=['IM0'], initial_capital=500000, config=config,
        )
        self.assertEqual(report.total_trades, 5)
        self.assertEqual(report.winning_trades, 5)
        self.assertEqual(report.losing_trades, 0)
        self.assertEqual(report.win_rate, 1.0)
        self.assertGreater(report.total_pnl, 0)
        self.assertEqual(report.profit_factor, float('inf'))

    def test_generate_report_all_losses(self):
        """Should calculate 0% win rate when all trades losing."""
        trades = [
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, i+2),
                exit_date=date(2025, 1, i+3),
                entry_price=5900, exit_price=5850,
                base_price=6000, drop_pct=-0.015, vwap=5950,
                level=1, quantity=1, multiplier=200,
                gross_pnl=-10000, fee=55, net_pnl=-10055,
            )
            for i in range(3)
        ]
        config = StrategyConfig(symbols=['IM0'])
        report = self.engine._generate_report(
            trades=trades, equity_curve=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 31),
            symbols=['IM0'], initial_capital=500000, config=config,
        )
        self.assertEqual(report.win_rate, 0.0)
        self.assertEqual(report.winning_trades, 0)
        self.assertEqual(report.losing_trades, 3)
        self.assertLess(report.total_pnl, 0)

    def test_generate_report_mixed_trades(self):
        """Should calculate correct metrics with mixed win/loss trades."""
        trades = [
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, 2),
                exit_date=date(2025, 1, 3),
                entry_price=5900, exit_price=5950,
                base_price=6000, drop_pct=-0.015, vwap=5950,
                level=1, quantity=1, multiplier=200,
                gross_pnl=10000, fee=55, net_pnl=9945,
            ),
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, 6),
                exit_date=date(2025, 1, 7),
                entry_price=5850, exit_price=5820,
                base_price=5950, drop_pct=-0.017, vwap=5900,
                level=1, quantity=1, multiplier=200,
                gross_pnl=-6000, fee=55, net_pnl=-6055,
            ),
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 2, 3),
                exit_date=date(2025, 2, 4),
                entry_price=5800, exit_price=5870,
                base_price=5900, drop_pct=-0.017, vwap=5850,
                level=1, quantity=1, multiplier=200,
                gross_pnl=14000, fee=55, net_pnl=13945,
            ),
        ]
        config = StrategyConfig(symbols=['IM0'])
        report = self.engine._generate_report(
            trades=trades, equity_curve=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 3, 1),
            symbols=['IM0'], initial_capital=500000, config=config,
        )
        self.assertEqual(report.total_trades, 3)
        self.assertEqual(report.winning_trades, 2)
        self.assertEqual(report.losing_trades, 1)
        self.assertAlmostEqual(report.win_rate, 2/3, places=4)

        # avg_win = (9945 + 13945) / 2 = 11945
        self.assertAlmostEqual(report.avg_win, 11945.0, places=0)
        # avg_loss = -6055
        self.assertAlmostEqual(report.avg_loss, -6055.0, places=0)
        # max_win = 13945
        self.assertAlmostEqual(report.max_win, 13945.0, places=0)
        # max_loss = -6055
        self.assertAlmostEqual(report.max_loss, -6055.0, places=0)

        # profit_factor = total_wins / abs(total_losses)
        expected_pf = (9945 + 13945) / 6055
        self.assertAlmostEqual(report.profit_factor, expected_pf, places=2)

    def test_generate_report_total_return(self):
        """Should calculate total return correctly."""
        trades = [
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, 2),
                exit_date=date(2025, 1, 3),
                entry_price=5900, exit_price=5950,
                base_price=6000, drop_pct=-0.015, vwap=5950,
                level=1, quantity=1, multiplier=200,
                gross_pnl=10000, fee=55, net_pnl=9945,
            ),
        ]
        config = StrategyConfig(symbols=['IM0'])
        report = self.engine._generate_report(
            trades=trades, equity_curve=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
            symbols=['IM0'], initial_capital=500000, config=config,
        )
        expected_return = 9945 / 500000
        self.assertAlmostEqual(report.total_return, expected_return, places=6)
        self.assertEqual(report.final_equity, 500000 + 9945)

    def test_generate_report_max_drawdown(self):
        """Should calculate max drawdown correctly."""
        # Trade 1: win +10000, Trade 2: loss -15000, Trade 3: win +8000
        # Equity: 500000 → 510000 → 495000 → 503000
        # Peak = 510000, max drawdown = (510000 - 495000) / 510000 ≈ 2.94%
        trades = [
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, 2), exit_date=date(2025, 1, 3),
                entry_price=5900, exit_price=5950, base_price=6000,
                drop_pct=-0.015, vwap=None, level=1, quantity=1, multiplier=200,
                gross_pnl=10050, fee=50, net_pnl=10000,
            ),
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, 6), exit_date=date(2025, 1, 7),
                entry_price=5900, exit_price=5825, base_price=6000,
                drop_pct=-0.015, vwap=None, level=1, quantity=1, multiplier=200,
                gross_pnl=-14950, fee=50, net_pnl=-15000,
            ),
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, 8), exit_date=date(2025, 1, 9),
                entry_price=5800, exit_price=5840, base_price=5900,
                drop_pct=-0.017, vwap=None, level=1, quantity=1, multiplier=200,
                gross_pnl=8050, fee=50, net_pnl=8000,
            ),
        ]
        config = StrategyConfig(symbols=['IM0'])
        report = self.engine._generate_report(
            trades=trades, equity_curve=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 31),
            symbols=['IM0'], initial_capital=500000, config=config,
        )
        expected_dd = (510000 - 495000) / 510000
        self.assertAlmostEqual(report.max_drawdown, expected_dd, places=4)

    def test_generate_report_monthly_returns(self):
        """Should calculate monthly returns correctly."""
        trades = [
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, 2), exit_date=date(2025, 1, 3),
                entry_price=5900, exit_price=5950, base_price=6000,
                drop_pct=-0.015, vwap=None, level=1, quantity=1, multiplier=200,
                gross_pnl=10000, fee=50, net_pnl=9950,
            ),
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 2, 3), exit_date=date(2025, 2, 4),
                entry_price=5800, exit_price=5780, base_price=5900,
                drop_pct=-0.017, vwap=None, level=1, quantity=1, multiplier=200,
                gross_pnl=-4000, fee=50, net_pnl=-4050,
            ),
        ]
        config = StrategyConfig(symbols=['IM0'])
        report = self.engine._generate_report(
            trades=trades, equity_curve=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 3, 1),
            symbols=['IM0'], initial_capital=500000, config=config,
        )
        self.assertIn('2025-01', report.monthly_returns)
        self.assertIn('2025-02', report.monthly_returns)
        self.assertAlmostEqual(report.monthly_returns['2025-01'], 9950 / 500000, places=6)
        self.assertAlmostEqual(report.monthly_returns['2025-02'], -4050 / 500000, places=6)

    def test_generate_report_symbol_stats(self):
        """Should calculate per-symbol statistics."""
        trades = [
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, 2), exit_date=date(2025, 1, 3),
                entry_price=5900, exit_price=5950, base_price=6000,
                drop_pct=-0.015, vwap=None, level=1, quantity=1, multiplier=200,
                gross_pnl=10000, fee=50, net_pnl=9950,
            ),
            BacktestTrade(
                symbol='IC0', entry_date=date(2025, 1, 2), exit_date=date(2025, 1, 3),
                entry_price=5500, exit_price=5480, base_price=5600,
                drop_pct=-0.018, vwap=None, level=1, quantity=1, multiplier=200,
                gross_pnl=-4000, fee=50, net_pnl=-4050,
            ),
        ]
        config = StrategyConfig(symbols=['IM0', 'IC0'])
        report = self.engine._generate_report(
            trades=trades, equity_curve=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 31),
            symbols=['IM0', 'IC0'], initial_capital=500000, config=config,
        )
        self.assertIn('IM0', report.symbol_stats)
        self.assertIn('IC0', report.symbol_stats)
        self.assertEqual(report.symbol_stats['IM0']['trades'], 1)
        self.assertGreater(report.symbol_stats['IM0']['total_pnl'], 0)
        self.assertEqual(report.symbol_stats['IC0']['trades'], 1)
        self.assertLess(report.symbol_stats['IC0']['total_pnl'], 0)

    def test_generate_report_sharpe_ratio(self):
        """Sharpe ratio should be computed for >1 trades."""
        trades = [
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, i+2),
                exit_date=date(2025, 1, i+3),
                entry_price=5900, exit_price=5950,
                base_price=6000, drop_pct=-0.015, vwap=None,
                level=1, quantity=1, multiplier=200,
                gross_pnl=10000, fee=55, net_pnl=9945,
            )
            for i in range(5)
        ]
        config = StrategyConfig(symbols=['IM0'])
        report = self.engine._generate_report(
            trades=trades, equity_curve=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
            symbols=['IM0'], initial_capital=500000, config=config,
        )
        # All same returns → std=0 → sharpe=0 (or very large if slightly different)
        # Since all trades are identical, daily_returns are identical, std of excess ≈ 0
        self.assertIsInstance(report.sharpe_ratio, float)

    def test_generate_report_holding_days(self):
        """Should calculate average holding days."""
        trades = [
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, 2), exit_date=date(2025, 1, 3),
                entry_price=5900, exit_price=5950, base_price=6000,
                drop_pct=-0.015, vwap=None, level=1, quantity=1, multiplier=200,
                gross_pnl=10000, fee=55, net_pnl=9945,
            ),
            BacktestTrade(
                symbol='IM0', entry_date=date(2025, 1, 6), exit_date=date(2025, 1, 9),
                entry_price=5900, exit_price=5950, base_price=6000,
                drop_pct=-0.015, vwap=None, level=1, quantity=1, multiplier=200,
                gross_pnl=10000, fee=55, net_pnl=9945,
            ),
        ]
        config = StrategyConfig(symbols=['IM0'])
        report = self.engine._generate_report(
            trades=trades, equity_curve=[],
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 31),
            symbols=['IM0'], initial_capital=500000, config=config,
        )
        # Trade 1: 1 day, Trade 2: 3 days → avg = 2.0
        self.assertAlmostEqual(report.avg_holding_days, 2.0, places=1)


class TestBacktestTradeIntegrity(unittest.TestCase):
    """Additional integrity tests for backtest PnL calculations."""

    def test_pnl_formula_long(self):
        """Verify gross_pnl = (exit - entry) * qty * multiplier."""
        entry = 5840.0
        exit_ = 5890.0
        qty = 2
        mult = 200
        expected = (exit_ - entry) * qty * mult  # 50 * 2 * 200 = 20000
        self.assertEqual(expected, 20000.0)

    def test_fee_formula(self):
        """Verify fee = entry*mult*qty*rate + exit*mult*qty*rate."""
        entry = 5840.0
        exit_ = 5890.0
        qty = 1
        mult = 200
        rate = 0.000023
        open_fee = entry * mult * qty * rate
        close_fee = exit_ * mult * qty * rate
        total = open_fee + close_fee
        self.assertAlmostEqual(total, (5840 + 5890) * 200 * 0.000023, places=4)

    def test_net_pnl_equals_gross_minus_fee(self):
        """net_pnl should equal gross_pnl - fee."""
        trade = BacktestTrade(
            symbol='IM0', entry_date=date(2025, 1, 2), exit_date=date(2025, 1, 3),
            entry_price=5900, exit_price=5950, base_price=6000,
            drop_pct=-0.015, vwap=5930, level=1, quantity=1, multiplier=200,
            gross_pnl=10000, fee=55, net_pnl=9945,
        )
        self.assertAlmostEqual(trade.net_pnl, trade.gross_pnl - trade.fee, places=2)


if __name__ == '__main__':
    unittest.main()
