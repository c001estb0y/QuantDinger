# Settlement Arbitrage Strategy - Position Manager Unit Tests
# 结算价差套利策略 - 仓位管理器单元测试

"""
Unit tests for PositionManager module.

Covers:
- Position opening with correct fields
- Position closing and P&L calculation
- Fee calculation logic
- Batch close all positions
- Trade history query with filters
- P&L summary statistics
- Unrealized P&L calculation
- Position count and margin tracking
- Edge cases and error handling
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.strategies.settlement_arbitrage.config import StrategyConfig
from app.strategies.settlement_arbitrage.position_manager import (
    Position,
    PositionDirection,
    PositionManager,
    PositionStatus,
    TradeRecord,
)


class TestPosition(unittest.TestCase):
    """Tests for Position dataclass."""

    def test_default_values(self):
        """Position should have sensible defaults."""
        pos = Position()
        self.assertEqual(pos.symbol, "")
        self.assertEqual(pos.direction, PositionDirection.LONG)
        self.assertEqual(pos.quantity, 1)
        self.assertEqual(pos.entry_price, 0.0)
        self.assertEqual(pos.status, PositionStatus.OPEN)
        self.assertIsNone(pos.exit_price)
        self.assertIsNone(pos.exit_time)
        self.assertEqual(pos.pnl, 0.0)
        self.assertEqual(pos.fee, 0.0)

    def test_unique_id_generation(self):
        """Each position should get a unique ID."""
        pos1 = Position()
        pos2 = Position()
        self.assertNotEqual(pos1.id, pos2.id)

    def test_to_dict(self):
        """to_dict should return all fields as a dictionary."""
        ts = datetime(2026, 2, 9, 14, 35)
        pos = Position(
            symbol="IM0",
            direction=PositionDirection.LONG,
            quantity=2,
            entry_price=5840.0,
            entry_time=ts,
            level=1,
            base_price=5900.0,
            drop_pct=-0.0102,
            vwap=5870.0,
            status=PositionStatus.OPEN,
        )
        d = pos.to_dict()
        self.assertEqual(d['symbol'], "IM0")
        self.assertEqual(d['direction'], "long")
        self.assertEqual(d['quantity'], 2)
        self.assertEqual(d['entry_price'], 5840.0)
        self.assertEqual(d['entry_time'], ts.isoformat())
        self.assertEqual(d['level'], 1)
        self.assertEqual(d['status'], "open")
        self.assertIsNone(d['exit_price'])
        self.assertIsNone(d['exit_time'])

    def test_to_dict_with_exit(self):
        """to_dict should include exit info when closed."""
        entry_ts = datetime(2026, 2, 9, 14, 35)
        exit_ts = datetime(2026, 2, 10, 9, 30)
        pos = Position(
            symbol="IC0",
            entry_time=entry_ts,
            exit_price=6100.0,
            exit_time=exit_ts,
            status=PositionStatus.CLOSED,
            pnl=5000.0,
            fee=50.0,
        )
        d = pos.to_dict()
        self.assertEqual(d['exit_price'], 6100.0)
        self.assertEqual(d['exit_time'], exit_ts.isoformat())
        self.assertEqual(d['status'], "closed")
        self.assertEqual(d['pnl'], 5000.0)


class TestTradeRecord(unittest.TestCase):
    """Tests for TradeRecord dataclass."""

    def test_to_dict_merges_position_data(self):
        """TradeRecord.to_dict should merge position fields with trade fields."""
        pos = Position(symbol="IM0", entry_price=5840.0, exit_price=5890.0)
        trade = TradeRecord(
            position=pos,
            gross_pnl=10000.0,
            net_pnl=9950.0,
            holding_hours=18.5,
        )
        d = trade.to_dict()
        self.assertEqual(d['symbol'], "IM0")
        self.assertEqual(d['gross_pnl'], 10000.0)
        self.assertEqual(d['net_pnl'], 9950.0)
        self.assertEqual(d['holding_hours'], 18.5)


class TestPositionManagerOpen(unittest.TestCase):
    """Tests for PositionManager.open_position."""

    def setUp(self):
        self.pm = PositionManager()

    def test_open_position_basic(self):
        """Should create a position with correct fields."""
        pos = self.pm.open_position(
            symbol="IM0", price=5840.0, quantity=1, level=1,
            base_price=5900.0, drop_pct=-0.0102
        )
        self.assertEqual(pos.symbol, "IM0")
        self.assertEqual(pos.entry_price, 5840.0)
        self.assertEqual(pos.quantity, 1)
        self.assertEqual(pos.level, 1)
        self.assertEqual(pos.base_price, 5900.0)
        self.assertAlmostEqual(pos.drop_pct, -0.0102)
        self.assertEqual(pos.direction, PositionDirection.LONG)
        self.assertEqual(pos.status, PositionStatus.OPEN)
        self.assertIsNotNone(pos.entry_time)

    def test_open_position_margin_calculation(self):
        """Margin should be calculated based on product multiplier and margin ratio."""
        pos = self.pm.open_position(
            symbol="IM0", price=5840.0, quantity=1, level=1
        )
        # IM: multiplier=200, margin_ratio=0.12
        expected_margin = 5840.0 * 200 * 1 * 0.12
        self.assertAlmostEqual(pos.margin, expected_margin, places=2)

    def test_open_position_ic_margin(self):
        """IC product should use IC-specific multiplier."""
        pos = self.pm.open_position(
            symbol="IC0", price=6000.0, quantity=2, level=1
        )
        # IC: multiplier=200, margin_ratio=0.12
        expected_margin = 6000.0 * 200 * 2 * 0.12
        self.assertAlmostEqual(pos.margin, expected_margin, places=2)

    def test_open_position_with_vwap(self):
        """Should store VWAP value when provided."""
        pos = self.pm.open_position(
            symbol="IM0", price=5840.0, quantity=1, level=1, vwap=5870.0
        )
        self.assertEqual(pos.vwap, 5870.0)

    def test_open_position_with_timestamp(self):
        """Should use provided timestamp."""
        ts = datetime(2026, 2, 9, 14, 35, 0)
        pos = self.pm.open_position(
            symbol="IM0", price=5840.0, quantity=1, level=1, timestamp=ts
        )
        self.assertEqual(pos.entry_time, ts)

    def test_open_position_tracked_in_open_positions(self):
        """Opened position should appear in open positions list."""
        pos = self.pm.open_position(
            symbol="IM0", price=5840.0, quantity=1, level=1
        )
        positions = self.pm.get_current_positions()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].id, pos.id)

    def test_open_multiple_positions(self):
        """Should track multiple open positions independently."""
        pos1 = self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        pos2 = self.pm.open_position(symbol="IM0", price=5780.0, quantity=1, level=2)
        pos3 = self.pm.open_position(symbol="IC0", price=6000.0, quantity=1, level=1)

        self.assertEqual(len(self.pm.get_current_positions()), 3)
        self.assertEqual(self.pm.get_position_count(), 3)
        self.assertEqual(self.pm.get_position_count("IM0"), 2)
        self.assertEqual(self.pm.get_position_count("IC0"), 1)


class TestPositionManagerClose(unittest.TestCase):
    """Tests for PositionManager.close_position."""

    def setUp(self):
        self.pm = PositionManager()

    def test_close_position_profitable(self):
        """Should calculate positive P&L when price goes up."""
        pos = self.pm.open_position(
            symbol="IM0", price=5840.0, quantity=1, level=1
        )
        trade = self.pm.close_position(pos.id, exit_price=5890.0)

        self.assertIsNotNone(trade)
        # gross_pnl = (5890 - 5840) * 1 * 200 = 10000
        self.assertAlmostEqual(trade.gross_pnl, 10000.0, places=0)
        self.assertGreater(trade.net_pnl, 0)
        self.assertGreater(trade.position.fee, 0)
        self.assertEqual(trade.position.status, PositionStatus.CLOSED)

    def test_close_position_loss(self):
        """Should calculate negative P&L when price goes down."""
        pos = self.pm.open_position(
            symbol="IM0", price=5840.0, quantity=1, level=1
        )
        trade = self.pm.close_position(pos.id, exit_price=5800.0)

        self.assertIsNotNone(trade)
        # gross_pnl = (5800 - 5840) * 1 * 200 = -8000
        self.assertAlmostEqual(trade.gross_pnl, -8000.0, places=0)
        self.assertLess(trade.net_pnl, 0)

    def test_close_position_removes_from_open(self):
        """Closed position should no longer appear in open positions."""
        pos = self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        self.assertEqual(self.pm.get_position_count(), 1)

        self.pm.close_position(pos.id, exit_price=5890.0)
        self.assertEqual(self.pm.get_position_count(), 0)

    def test_close_position_added_to_history(self):
        """Closed position should appear in trade history."""
        pos = self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        self.pm.close_position(pos.id, exit_price=5890.0)

        history = self.pm.get_trade_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].position.symbol, "IM0")

    def test_close_nonexistent_position(self):
        """Should return None for non-existent position ID."""
        result = self.pm.close_position("nonexistent_id", exit_price=5890.0)
        self.assertIsNone(result)

    def test_close_position_holding_hours(self):
        """Should calculate correct holding hours."""
        entry_ts = datetime(2026, 2, 9, 14, 35, 0)
        exit_ts = datetime(2026, 2, 10, 9, 30, 0)

        pos = self.pm.open_position(
            symbol="IM0", price=5840.0, quantity=1, level=1, timestamp=entry_ts
        )
        trade = self.pm.close_position(pos.id, exit_price=5890.0, timestamp=exit_ts)

        expected_hours = (exit_ts - entry_ts).total_seconds() / 3600
        self.assertAlmostEqual(trade.holding_hours, expected_hours, places=1)

    def test_close_position_with_quantity(self):
        """P&L should scale with quantity."""
        pos = self.pm.open_position(
            symbol="IM0", price=5840.0, quantity=3, level=1
        )
        trade = self.pm.close_position(pos.id, exit_price=5890.0)

        # gross_pnl = (5890 - 5840) * 3 * 200 = 30000
        self.assertAlmostEqual(trade.gross_pnl, 30000.0, places=0)


class TestPositionManagerCloseAll(unittest.TestCase):
    """Tests for PositionManager.close_all_positions."""

    def setUp(self):
        self.pm = PositionManager()

    def test_close_all_positions(self):
        """Should close all open positions."""
        self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        self.pm.open_position(symbol="IM0", price=5780.0, quantity=1, level=2)

        trades = self.pm.close_all_positions(exit_price=5890.0)
        self.assertEqual(len(trades), 2)
        self.assertEqual(self.pm.get_position_count(), 0)

    def test_close_all_by_symbol(self):
        """Should only close positions for specified symbol."""
        self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        self.pm.open_position(symbol="IC0", price=6000.0, quantity=1, level=1)

        trades = self.pm.close_all_positions(exit_price=5890.0, symbol="IM0")
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].position.symbol, "IM0")
        self.assertEqual(self.pm.get_position_count(), 1)  # IC0 still open
        self.assertEqual(self.pm.get_position_count("IC0"), 1)

    def test_close_all_empty(self):
        """Should return empty list when no positions."""
        trades = self.pm.close_all_positions(exit_price=5890.0)
        self.assertEqual(len(trades), 0)

    def test_close_all_with_timestamp(self):
        """Should use provided timestamp for all closes."""
        self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        self.pm.open_position(symbol="IM0", price=5780.0, quantity=1, level=2)

        exit_ts = datetime(2026, 2, 10, 9, 30, 0)
        trades = self.pm.close_all_positions(exit_price=5890.0, timestamp=exit_ts)

        for trade in trades:
            self.assertEqual(trade.position.exit_time, exit_ts)


class TestPositionManagerFee(unittest.TestCase):
    """Tests for fee calculation logic."""

    def setUp(self):
        self.pm = PositionManager()

    def test_fee_calculation_basic(self):
        """Fee should be based on price * multiplier * quantity * rate."""
        pos = self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        trade = self.pm.close_position(pos.id, exit_price=5890.0)

        # open_fee = 5840 * 200 * 1 * 0.000023
        # close_fee = 5890 * 200 * 1 * 0.000023
        expected_open_fee = 5840 * 200 * 1 * 0.000023
        expected_close_fee = 5890 * 200 * 1 * 0.000023
        expected_total = round(expected_open_fee + expected_close_fee, 2)

        self.assertAlmostEqual(trade.position.fee, expected_total, places=2)

    def test_fee_scales_with_quantity(self):
        """Fee should increase proportionally with quantity."""
        pos1 = self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        trade1 = self.pm.close_position(pos1.id, exit_price=5890.0)

        pos2 = self.pm.open_position(symbol="IM0", price=5840.0, quantity=2, level=1)
        trade2 = self.pm.close_position(pos2.id, exit_price=5890.0)

        self.assertAlmostEqual(trade2.position.fee, trade1.position.fee * 2, places=1)

    def test_net_pnl_is_gross_minus_fee(self):
        """Net P&L should equal gross P&L minus fee."""
        pos = self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        trade = self.pm.close_position(pos.id, exit_price=5890.0)

        self.assertAlmostEqual(
            trade.net_pnl,
            trade.gross_pnl - trade.position.fee,
            places=2
        )


class TestPositionManagerQueries(unittest.TestCase):
    """Tests for query methods."""

    def setUp(self):
        self.pm = PositionManager()

    def test_get_current_positions_by_symbol(self):
        """Should filter positions by symbol."""
        self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        self.pm.open_position(symbol="IC0", price=6000.0, quantity=1, level=1)

        im_positions = self.pm.get_current_positions("IM0")
        self.assertEqual(len(im_positions), 1)
        self.assertEqual(im_positions[0].symbol, "IM0")

    def test_get_total_margin_used(self):
        """Should sum margin of all open positions."""
        self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        self.pm.open_position(symbol="IC0", price=6000.0, quantity=1, level=1)

        total_margin = self.pm.get_total_margin_used()
        expected = 5840.0 * 200 * 1 * 0.12 + 6000.0 * 200 * 1 * 0.12
        self.assertAlmostEqual(total_margin, expected, places=2)

    def test_has_open_positions(self):
        """Should correctly report open position status."""
        self.assertFalse(self.pm.has_open_positions())
        self.assertFalse(self.pm.has_open_positions("IM0"))

        self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        self.assertTrue(self.pm.has_open_positions())
        self.assertTrue(self.pm.has_open_positions("IM0"))
        self.assertFalse(self.pm.has_open_positions("IC0"))

    def test_calculate_unrealized_pnl(self):
        """Should calculate unrealized P&L based on current price."""
        self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        self.pm.open_position(symbol="IM0", price=5780.0, quantity=1, level=2)

        # Current price = 5900
        # pos1: (5900-5840)*1*200 = 12000
        # pos2: (5900-5780)*1*200 = 24000
        pnl = self.pm.calculate_unrealized_pnl("IM0", 5900.0)
        self.assertAlmostEqual(pnl, 36000.0, places=0)

    def test_calculate_unrealized_pnl_negative(self):
        """Should return negative unrealized P&L when price drops."""
        self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)

        pnl = self.pm.calculate_unrealized_pnl("IM0", 5800.0)
        # (5800-5840)*1*200 = -8000
        self.assertAlmostEqual(pnl, -8000.0, places=0)

    def test_calculate_unrealized_pnl_no_position(self):
        """Should return 0 when no positions for symbol."""
        pnl = self.pm.calculate_unrealized_pnl("IM0", 5900.0)
        self.assertEqual(pnl, 0.0)


class TestPositionManagerTradeHistory(unittest.TestCase):
    """Tests for trade history queries."""

    def setUp(self):
        self.pm = PositionManager()
        # Create several trades
        ts_base = datetime(2026, 2, 5, 14, 35)
        for i in range(5):
            symbol = "IM0" if i < 3 else "IC0"
            entry_ts = ts_base + timedelta(days=i)
            exit_ts = entry_ts + timedelta(hours=19)
            pos = self.pm.open_position(
                symbol=symbol, price=5840.0 + i * 10, quantity=1,
                level=1, timestamp=entry_ts
            )
            self.pm.close_position(pos.id, exit_price=5890.0, timestamp=exit_ts)

    def test_get_all_trade_history(self):
        """Should return all trades."""
        history = self.pm.get_trade_history()
        self.assertEqual(len(history), 5)

    def test_trade_history_by_symbol(self):
        """Should filter by symbol."""
        im_history = self.pm.get_trade_history(symbol="IM0")
        self.assertEqual(len(im_history), 3)

        ic_history = self.pm.get_trade_history(symbol="IC0")
        self.assertEqual(len(ic_history), 2)

    def test_trade_history_limit(self):
        """Should respect limit parameter."""
        history = self.pm.get_trade_history(limit=2)
        self.assertEqual(len(history), 2)

    def test_trade_history_sorted_by_exit_time(self):
        """Trades should be sorted by exit time descending."""
        history = self.pm.get_trade_history()
        for i in range(len(history) - 1):
            self.assertGreaterEqual(
                history[i].position.exit_time,
                history[i + 1].position.exit_time
            )

    def test_trade_history_date_filter(self):
        """Should filter by date range."""
        start = datetime(2026, 2, 7, 0, 0)
        end = datetime(2026, 2, 9, 23, 59)
        history = self.pm.get_trade_history(start_date=start, end_date=end)
        for trade in history:
            self.assertGreaterEqual(trade.position.entry_time, start)


class TestPositionManagerPnlSummary(unittest.TestCase):
    """Tests for P&L summary statistics."""

    def setUp(self):
        self.pm = PositionManager()

    def test_empty_summary(self):
        """Should return zero values when no trades."""
        summary = self.pm.get_pnl_summary()
        self.assertEqual(summary['total_trades'], 0)
        self.assertEqual(summary['total_pnl'], 0)
        self.assertEqual(summary['win_rate'], 0)

    def test_summary_with_wins_and_losses(self):
        """Should calculate correct summary stats."""
        # Winning trade
        pos1 = self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        self.pm.close_position(pos1.id, exit_price=5890.0)

        # Losing trade
        pos2 = self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        self.pm.close_position(pos2.id, exit_price=5800.0)

        summary = self.pm.get_pnl_summary()
        self.assertEqual(summary['total_trades'], 2)
        self.assertEqual(summary['winning_trades'], 1)
        self.assertEqual(summary['losing_trades'], 1)
        self.assertAlmostEqual(summary['win_rate'], 0.5, places=2)
        self.assertGreater(summary['avg_win'], 0)
        self.assertLess(summary['avg_loss'], 0)
        self.assertGreater(summary['total_fees'], 0)

    def test_summary_all_wins(self):
        """Win rate should be 1.0 when all trades profitable."""
        for _ in range(3):
            pos = self.pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
            self.pm.close_position(pos.id, exit_price=5890.0)

        summary = self.pm.get_pnl_summary()
        self.assertAlmostEqual(summary['win_rate'], 1.0, places=2)
        self.assertEqual(summary['losing_trades'], 0)


class TestPositionManagerReset(unittest.TestCase):
    """Tests for reset functionality."""

    def test_reset_clears_all(self):
        """Reset should clear all positions and history."""
        pm = PositionManager()
        pm.open_position(symbol="IM0", price=5840.0, quantity=1, level=1)
        pos = pm.open_position(symbol="IC0", price=6000.0, quantity=1, level=1)
        pm.close_position(pos.id, exit_price=6050.0)

        pm.reset()
        self.assertEqual(pm.get_position_count(), 0)
        self.assertEqual(len(pm.get_trade_history()), 0)
        self.assertFalse(pm.has_open_positions())


if __name__ == '__main__':
    unittest.main()
