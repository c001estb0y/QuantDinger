"""
Unit tests for VWAPCalculator module.

Tests cover:
- Basic VWAP calculation (close price)
- Typical price VWAP calculation
- Time window filtering
- Zero volume fallback to simple average
- Empty / None input handling
- Missing columns handling
- Real-time incremental VWAP updates
- Real-time VWAP reset (single symbol and all)
- Real-time stats retrieval
- Price vs settlement deviation calculation
- Settlement price retrieval with cache
- Settlement price fallback to VWAP calculation
- Cache clearing
"""

import unittest
from datetime import date, datetime, time, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import numpy as np

from app.strategies.settlement_arbitrage.vwap_calculator import (
    VWAPCalculator, DEFAULT_VWAP_START, DEFAULT_VWAP_END
)


class TestVWAPCalculateBasic(unittest.TestCase):
    """Tests for calculate_vwap with close price."""

    def setUp(self):
        self.calc = VWAPCalculator()

    def test_basic_vwap(self):
        """VWAP = sum(price*volume) / sum(volume) using close price."""
        bars = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=4, freq='15min'),
            'open': [100, 101, 99, 100],
            'high': [102, 103, 101, 102],
            'low': [99, 100, 98, 99],
            'close': [101, 99, 100, 101],
            'volume': [1000, 2000, 1500, 500],
        })
        vwap = self.calc.calculate_vwap(bars)
        expected = (101*1000 + 99*2000 + 100*1500 + 101*500) / 5000
        self.assertIsNotNone(vwap)
        self.assertAlmostEqual(vwap, round(expected, 2), places=2)

    def test_single_bar(self):
        """VWAP of a single bar equals its close price."""
        bars = pd.DataFrame({
            'datetime': [datetime(2026, 2, 9, 14, 30)],
            'close': [5800.0],
            'volume': [500],
        })
        vwap = self.calc.calculate_vwap(bars)
        self.assertAlmostEqual(vwap, 5800.0, places=2)

    def test_uniform_volume(self):
        """VWAP with uniform volume equals simple average."""
        bars = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=3, freq='20min'),
            'close': [100.0, 200.0, 300.0],
            'volume': [100, 100, 100],
        })
        vwap = self.calc.calculate_vwap(bars)
        self.assertAlmostEqual(vwap, 200.0, places=2)

    def test_zero_volume_fallback(self):
        """VWAP with zero total volume falls back to simple average."""
        bars = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=3, freq='20min'),
            'close': [100.0, 102.0, 104.0],
            'volume': [0, 0, 0],
        })
        vwap = self.calc.calculate_vwap(bars)
        self.assertIsNotNone(vwap)
        self.assertAlmostEqual(vwap, 102.0, places=1)

    def test_empty_dataframe(self):
        """VWAP of empty DataFrame returns None."""
        vwap = self.calc.calculate_vwap(pd.DataFrame())
        self.assertIsNone(vwap)

    def test_none_input(self):
        """VWAP of None input returns None."""
        vwap = self.calc.calculate_vwap(None)
        self.assertIsNone(vwap)

    def test_missing_columns(self):
        """VWAP returns None when required columns are missing."""
        bars = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=3, freq='20min'),
            'price': [100, 101, 102],  # Wrong column name
        })
        vwap = self.calc.calculate_vwap(bars)
        self.assertIsNone(vwap)

    def test_custom_price_column(self):
        """VWAP with custom price column (e.g., 'open')."""
        bars = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=2, freq='30min'),
            'open': [100.0, 200.0],
            'close': [150.0, 250.0],
            'volume': [100, 200],
        })
        vwap = self.calc.calculate_vwap(bars, price_col='open')
        expected = (100*100 + 200*200) / 300
        self.assertAlmostEqual(vwap, round(expected, 2), places=2)


class TestVWAPTimeWindowFiltering(unittest.TestCase):
    """Tests for VWAP time window filtering."""

    def setUp(self):
        self.calc = VWAPCalculator()

    def test_default_window_filters_correctly(self):
        """Only bars within 14:00-15:00 should be included."""
        bars = pd.DataFrame({
            'datetime': [
                datetime(2026, 2, 9, 13, 50),  # Before window
                datetime(2026, 2, 9, 14, 0),   # Start of window
                datetime(2026, 2, 9, 14, 30),  # In window
                datetime(2026, 2, 9, 15, 0),   # End of window
                datetime(2026, 2, 9, 15, 10),  # After window
            ],
            'close': [1000, 100, 200, 300, 9999],
            'volume': [999, 100, 200, 300, 999],
        })
        vwap = self.calc.calculate_vwap(bars)
        # Only bars at 14:00, 14:30, 15:00 should be included
        expected = (100*100 + 200*200 + 300*300) / (100+200+300)
        self.assertAlmostEqual(vwap, round(expected, 2), places=2)

    def test_custom_time_window(self):
        """VWAP with custom time window."""
        bars = pd.DataFrame({
            'datetime': [
                datetime(2026, 2, 9, 14, 30),
                datetime(2026, 2, 9, 14, 45),
                datetime(2026, 2, 9, 15, 0),
            ],
            'close': [100, 200, 300],
            'volume': [100, 100, 100],
        })
        # Only 14:30-14:45
        vwap = self.calc.calculate_vwap(
            bars,
            start_time=time(14, 30),
            end_time=time(14, 45)
        )
        expected = (100*100 + 200*100) / 200
        self.assertAlmostEqual(vwap, round(expected, 2), places=2)

    def test_no_bars_in_window(self):
        """VWAP returns None when no bars fall in the time window."""
        bars = pd.DataFrame({
            'datetime': [
                datetime(2026, 2, 9, 10, 0),
                datetime(2026, 2, 9, 11, 0),
            ],
            'close': [100, 200],
            'volume': [100, 200],
        })
        vwap = self.calc.calculate_vwap(bars)
        self.assertIsNone(vwap)

    def test_string_datetime_column(self):
        """VWAP should handle string datetime column correctly."""
        bars = pd.DataFrame({
            'datetime': ['2026-02-09 14:00:00', '2026-02-09 14:30:00'],
            'close': [100.0, 200.0],
            'volume': [100, 200],
        })
        vwap = self.calc.calculate_vwap(bars)
        self.assertIsNotNone(vwap)


class TestVWAPTypicalPrice(unittest.TestCase):
    """Tests for calculate_vwap_typical (HLC typical price)."""

    def setUp(self):
        self.calc = VWAPCalculator()

    def test_typical_price_vwap(self):
        """Typical price VWAP = sum(TP*vol)/sum(vol), TP=(H+L+C)/3."""
        bars = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=2, freq='30min'),
            'high': [105, 205],
            'low': [95, 195],
            'close': [100, 200],
            'volume': [100, 200],
        })
        vwap = self.calc.calculate_vwap_typical(bars)
        tp1 = (105 + 95 + 100) / 3
        tp2 = (205 + 195 + 200) / 3
        expected = (tp1*100 + tp2*200) / 300
        self.assertAlmostEqual(vwap, round(expected, 2), places=2)

    def test_typical_price_empty(self):
        """Typical price VWAP returns None for empty data."""
        self.assertIsNone(self.calc.calculate_vwap_typical(pd.DataFrame()))
        self.assertIsNone(self.calc.calculate_vwap_typical(None))

    def test_typical_price_zero_volume(self):
        """Typical price VWAP falls back to simple average with zero volume."""
        bars = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=2, freq='30min'),
            'high': [105, 205],
            'low': [95, 195],
            'close': [100, 200],
            'volume': [0, 0],
        })
        vwap = self.calc.calculate_vwap_typical(bars)
        tp1 = (105 + 95 + 100) / 3
        tp2 = (205 + 195 + 200) / 3
        expected = (tp1 + tp2) / 2
        self.assertAlmostEqual(vwap, round(expected, 2), places=1)


class TestRealtimeVWAP(unittest.TestCase):
    """Tests for real-time incremental VWAP."""

    def setUp(self):
        self.calc = VWAPCalculator()

    def test_single_update(self):
        """First update should return the price itself."""
        vwap = self.calc.update_realtime('IM0', 5800.0, 100)
        self.assertEqual(vwap, 5800.0)

    def test_multiple_updates(self):
        """Incremental VWAP should match batch calculation."""
        self.calc.reset_realtime('IM0')
        self.calc.update_realtime('IM0', 5800.0, 100)
        vwap = self.calc.update_realtime('IM0', 5900.0, 200)
        expected = (5800*100 + 5900*200) / 300
        self.assertAlmostEqual(vwap, round(expected, 2), places=2)

    def test_get_realtime_vwap(self):
        """get_realtime_vwap should return current accumulated VWAP."""
        self.calc.update_realtime('IC0', 6000.0, 50)
        self.calc.update_realtime('IC0', 6100.0, 150)
        vwap = self.calc.get_realtime_vwap('IC0')
        expected = (6000*50 + 6100*150) / 200
        self.assertAlmostEqual(vwap, round(expected, 2), places=2)

    def test_get_realtime_vwap_no_data(self):
        """get_realtime_vwap returns None for unseen symbol."""
        self.assertIsNone(self.calc.get_realtime_vwap('UNKNOWN'))

    def test_zero_volume_realtime(self):
        """Real-time VWAP with zero volume uses simple average."""
        self.calc.reset_realtime('IM0')
        self.calc.update_realtime('IM0', 5800.0, 0)
        vwap = self.calc.update_realtime('IM0', 5900.0, 0)
        # cumulative_pv = 0, cumulative_v = 0, bar_count = 2
        # Fallback: cumulative_pv / bar_count = 0 / 2 = 0
        self.assertEqual(vwap, 0.0)

    def test_reset_single_symbol(self):
        """reset_realtime(symbol) should clear only that symbol."""
        self.calc.update_realtime('IM0', 5800, 100)
        self.calc.update_realtime('IC0', 6000, 100)
        self.calc.reset_realtime('IM0')

        self.assertIsNone(self.calc.get_realtime_vwap('IM0'))
        self.assertIsNotNone(self.calc.get_realtime_vwap('IC0'))

    def test_reset_all(self):
        """reset_realtime() with no arg should clear all symbols."""
        self.calc.update_realtime('IM0', 5800, 100)
        self.calc.update_realtime('IC0', 6000, 100)
        self.calc.reset_realtime()

        self.assertIsNone(self.calc.get_realtime_vwap('IM0'))
        self.assertIsNone(self.calc.get_realtime_vwap('IC0'))

    def test_realtime_stats(self):
        """get_realtime_stats should return correct statistics."""
        self.calc.reset_realtime()
        self.calc.update_realtime('IM0', 5800, 100)
        self.calc.update_realtime('IM0', 5900, 200)

        stats = self.calc.get_realtime_stats('IM0')
        self.assertEqual(stats['symbol'], 'IM0')
        self.assertEqual(stats['bar_count'], 2)
        self.assertEqual(stats['total_volume'], 300)
        self.assertAlmostEqual(
            stats['total_pv'], 5800*100 + 5900*200, places=2
        )
        self.assertIsNotNone(stats['vwap'])

    def test_multiple_symbols_independent(self):
        """Real-time VWAP for different symbols should be independent."""
        self.calc.reset_realtime()
        self.calc.update_realtime('IM0', 5800, 100)
        self.calc.update_realtime('IC0', 6200, 200)

        self.assertAlmostEqual(self.calc.get_realtime_vwap('IM0'), 5800.0, places=2)
        self.assertAlmostEqual(self.calc.get_realtime_vwap('IC0'), 6200.0, places=2)


class TestPriceVsSettlement(unittest.TestCase):
    """Tests for calculate_price_vs_settlement."""

    def setUp(self):
        self.calc = VWAPCalculator()

    def test_negative_deviation(self):
        """When current < settlement, deviation should be negative."""
        result = self.calc.calculate_price_vs_settlement(5800, 5900)
        self.assertAlmostEqual(result['deviation'], -100.0, places=2)
        self.assertLess(result['deviation_pct'], 0)

    def test_positive_deviation(self):
        """When current > settlement, deviation should be positive."""
        result = self.calc.calculate_price_vs_settlement(6000, 5900)
        self.assertAlmostEqual(result['deviation'], 100.0, places=2)
        self.assertGreater(result['deviation_pct'], 0)

    def test_zero_deviation(self):
        """When current == settlement, deviation should be zero."""
        result = self.calc.calculate_price_vs_settlement(5900, 5900)
        self.assertAlmostEqual(result['deviation'], 0.0, places=2)
        self.assertAlmostEqual(result['deviation_pct'], 0.0, places=6)

    def test_zero_settlement_price(self):
        """When settlement = 0, should return zero to avoid division error."""
        result = self.calc.calculate_price_vs_settlement(5800, 0)
        self.assertEqual(result['deviation'], 0)
        self.assertEqual(result['deviation_pct'], 0)

    def test_deviation_percentage_accuracy(self):
        """Deviation percentage should be precisely calculated."""
        result = self.calc.calculate_price_vs_settlement(5841, 5900)
        expected_pct = (5841 - 5900) / 5900
        self.assertAlmostEqual(result['deviation_pct'], round(expected_pct, 6), places=6)


class TestGetSettlementPrice(unittest.TestCase):
    """Tests for get_settlement_price with mocked data source."""

    def setUp(self):
        self.mock_ds = MagicMock()
        self.calc = VWAPCalculator(data_source=self.mock_ds)

    def test_returns_official_price(self):
        """Should return official settlement price when available."""
        self.mock_ds.get_settlement_price.return_value = 5888.0
        result = self.calc.get_settlement_price('IM0', date(2026, 2, 9))
        self.assertEqual(result, 5888.0)

    def test_falls_back_to_vwap(self):
        """Should calculate VWAP when official price unavailable."""
        self.mock_ds.get_settlement_price.side_effect = Exception("not available")

        bars = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=3, freq='20min'),
            'close': [5800.0, 5850.0, 5900.0],
            'volume': [100, 200, 100],
        })
        self.mock_ds.get_minute_bars.return_value = bars

        result = self.calc.get_settlement_price('IM0', date(2026, 2, 9))
        self.assertIsNotNone(result)
        expected = (5800*100 + 5850*200 + 5900*100) / 400
        self.assertAlmostEqual(result, round(expected, 2), places=2)

    def test_returns_none_when_all_fail(self):
        """Should return None when both official and VWAP fail."""
        self.mock_ds.get_settlement_price.side_effect = Exception("fail")
        self.mock_ds.get_minute_bars.return_value = None

        result = self.calc.get_settlement_price('IM0', date(2026, 2, 9))
        self.assertIsNone(result)

    def test_uses_cache(self):
        """Should use cached value on second call."""
        self.mock_ds.get_settlement_price.return_value = 5888.0
        self.calc.get_settlement_price('IM0', date(2026, 2, 9))
        self.calc.get_settlement_price('IM0', date(2026, 2, 9))

        # Should only call data source once due to caching
        self.assertEqual(self.mock_ds.get_settlement_price.call_count, 1)

    def test_skip_cache(self):
        """Should bypass cache when use_cache=False."""
        self.mock_ds.get_settlement_price.return_value = 5888.0
        self.calc.get_settlement_price('IM0', date(2026, 2, 9))
        self.calc.get_settlement_price('IM0', date(2026, 2, 9), use_cache=False)

        self.assertEqual(self.mock_ds.get_settlement_price.call_count, 2)

    def test_ignores_zero_official_price(self):
        """Should not use official price if it's zero."""
        self.mock_ds.get_settlement_price.return_value = 0

        bars = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=2, freq='30min'),
            'close': [5800.0, 5900.0],
            'volume': [100, 100],
        })
        self.mock_ds.get_minute_bars.return_value = bars

        result = self.calc.get_settlement_price('IM0', date(2026, 2, 9))
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 5850.0, places=2)


class TestCacheClearing(unittest.TestCase):
    """Tests for cache clearing."""

    def setUp(self):
        self.calc = VWAPCalculator()

    def test_clear_cache(self):
        """clear_cache should clear both VWAP cache and realtime state."""
        self.calc._vwap_cache[('IM0', '2026-02-09')] = 5888.0
        self.calc.update_realtime('IM0', 5800, 100)

        self.calc.clear_cache()

        self.assertEqual(len(self.calc._vwap_cache), 0)
        self.assertIsNone(self.calc.get_realtime_vwap('IM0'))


if __name__ == '__main__':
    unittest.main()
