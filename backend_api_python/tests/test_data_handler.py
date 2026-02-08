"""
Unit tests for data_handler module.
Tests: MinuteBar, MinuteDataHandler (subscribe, callback, cache, dedup, storage, polling).
"""

import os
import tempfile
import unittest
from datetime import datetime, date, time, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

import pandas as pd

from app.strategies.settlement_arbitrage.data_handler import MinuteBar, MinuteDataHandler


class TestMinuteBar(unittest.TestCase):
    """Tests for MinuteBar dataclass."""

    def test_creation(self):
        """MinuteBar should store all fields correctly."""
        dt = datetime(2026, 2, 9, 14, 30)
        bar = MinuteBar(
            symbol='IM0', dt=dt,
            open_price=5900, high=5910, low=5890, close=5905,
            volume=100, amount=590500
        )
        self.assertEqual(bar.symbol, 'IM0')
        self.assertEqual(bar.datetime, dt)
        self.assertEqual(bar.open, 5900)
        self.assertEqual(bar.high, 5910)
        self.assertEqual(bar.low, 5890)
        self.assertEqual(bar.close, 5905)
        self.assertEqual(bar.volume, 100)
        self.assertEqual(bar.amount, 590500)

    def test_default_volume_amount(self):
        """MinuteBar should default volume and amount to 0."""
        bar = MinuteBar(
            symbol='IC0', dt=datetime(2026, 2, 9, 14, 31),
            open_price=6000, high=6010, low=5990, close=6005
        )
        self.assertEqual(bar.volume, 0.0)
        self.assertEqual(bar.amount, 0.0)

    def test_to_dict(self):
        """to_dict should return all fields as a dictionary."""
        dt = datetime(2026, 2, 9, 14, 32)
        bar = MinuteBar('IM0', dt, 5900, 5910, 5890, 5905, 100, 590500)
        d = bar.to_dict()
        self.assertEqual(d['symbol'], 'IM0')
        self.assertEqual(d['datetime'], dt)
        self.assertEqual(d['open'], 5900)
        self.assertEqual(d['close'], 5905)
        self.assertEqual(d['volume'], 100)
        self.assertIn('amount', d)

    def test_repr(self):
        """repr should contain symbol and price info."""
        bar = MinuteBar('IM0', datetime(2026, 2, 9, 14, 30), 5900, 5910, 5890, 5905)
        r = repr(bar)
        self.assertIn('IM0', r)
        self.assertIn('5905', r)


class TestMinuteDataHandlerSubscribe(unittest.TestCase):
    """Tests for subscribe/unsubscribe functionality."""

    def setUp(self):
        self.handler = MinuteDataHandler(data_dir=tempfile.mkdtemp())

    def test_subscribe_single(self):
        """Should subscribe to a single symbol."""
        self.handler.subscribe(['IM0'])
        self.assertEqual(self.handler._symbols, ['IM0'])
        self.assertIn('IM0', self.handler._cache)

    def test_subscribe_multiple(self):
        """Should subscribe to multiple symbols."""
        self.handler.subscribe(['IM0', 'IC0', 'IF0'])
        self.assertEqual(len(self.handler._symbols), 3)

    def test_subscribe_dedup(self):
        """Should deduplicate symbols."""
        self.handler.subscribe(['IM0', 'IM0', 'IC0'])
        self.assertEqual(len(self.handler._symbols), 2)

    def test_unsubscribe_specific(self):
        """Should unsubscribe specific symbols."""
        self.handler.subscribe(['IM0', 'IC0', 'IF0'])
        self.handler.unsubscribe(['IC0'])
        self.assertNotIn('IC0', self.handler._symbols)
        self.assertEqual(len(self.handler._symbols), 2)

    def test_unsubscribe_all(self):
        """Should unsubscribe all when None is passed."""
        self.handler.subscribe(['IM0', 'IC0'])
        self.handler.unsubscribe(None)
        self.assertEqual(len(self.handler._symbols), 0)
        self.assertEqual(len(self.handler._cache), 0)

    def test_unsubscribe_nonexistent(self):
        """Should not error when unsubscribing non-existent symbol."""
        self.handler.subscribe(['IM0'])
        self.handler.unsubscribe(['IC0'])  # Not subscribed
        self.assertEqual(len(self.handler._symbols), 1)


class TestMinuteDataHandlerCallbacks(unittest.TestCase):
    """Tests for callback registration and firing."""

    def setUp(self):
        self.handler = MinuteDataHandler(data_dir=tempfile.mkdtemp())

    def test_register_callback(self):
        """Should register a callback."""
        cb = MagicMock()
        self.handler.on_bar(cb)
        self.assertEqual(len(self.handler._bar_callbacks), 1)

    def test_register_duplicate_callback(self):
        """Should not register the same callback twice."""
        cb = MagicMock()
        self.handler.on_bar(cb)
        self.handler.on_bar(cb)
        self.assertEqual(len(self.handler._bar_callbacks), 1)

    def test_remove_callback(self):
        """Should remove a registered callback."""
        cb = MagicMock()
        self.handler.on_bar(cb)
        self.handler.remove_bar_callback(cb)
        self.assertEqual(len(self.handler._bar_callbacks), 0)

    def test_remove_nonexistent_callback(self):
        """Should not error when removing non-existent callback."""
        cb = MagicMock()
        self.handler.remove_bar_callback(cb)  # Not registered
        self.assertEqual(len(self.handler._bar_callbacks), 0)

    def test_fire_callbacks(self):
        """Should fire all registered callbacks with the bar."""
        cb1 = MagicMock()
        cb2 = MagicMock()
        self.handler.on_bar(cb1)
        self.handler.on_bar(cb2)

        bar = MinuteBar('IM0', datetime(2026, 2, 9, 14, 30), 5900, 5910, 5890, 5905, 100)
        self.handler._fire_callbacks(bar)

        cb1.assert_called_once_with(bar)
        cb2.assert_called_once_with(bar)

    def test_callback_exception_does_not_break_others(self):
        """If one callback raises, others should still fire."""
        cb1 = MagicMock(side_effect=Exception("test error"))
        cb2 = MagicMock()
        self.handler.on_bar(cb1)
        self.handler.on_bar(cb2)

        bar = MinuteBar('IM0', datetime(2026, 2, 9, 14, 30), 5900, 5910, 5890, 5905)
        self.handler._fire_callbacks(bar)

        cb1.assert_called_once()
        cb2.assert_called_once()


class TestMinuteDataHandlerCache(unittest.TestCase):
    """Tests for in-memory cache management."""

    def setUp(self):
        self.handler = MinuteDataHandler(data_dir=tempfile.mkdtemp())

    def _make_df(self, start_time, periods=3):
        return pd.DataFrame({
            'datetime': pd.date_range(start_time, periods=periods, freq='1min'),
            'open': [100 + i for i in range(periods)],
            'high': [101 + i for i in range(periods)],
            'low': [99 + i for i in range(periods)],
            'close': [100.5 + i for i in range(periods)],
            'volume': [100 + i * 10 for i in range(periods)],
        })

    def test_update_cache_initial(self):
        """Should store data when cache is empty."""
        df = self._make_df('2026-02-09 14:30')
        self.handler._update_cache('IM0', df)
        cached = self.handler.get_cached_bars('IM0')
        self.assertIsNotNone(cached)
        self.assertEqual(len(cached), 3)

    def test_update_cache_merge_dedup(self):
        """Should merge and deduplicate by datetime."""
        df1 = self._make_df('2026-02-09 14:30', 3)
        df2 = self._make_df('2026-02-09 14:31', 3)  # Overlaps at 14:31 and 14:32
        self.handler._update_cache('IM0', df1)
        self.handler._update_cache('IM0', df2)
        cached = self.handler.get_cached_bars('IM0')
        self.assertIsNotNone(cached)
        self.assertEqual(len(cached), 4)  # 14:30, 14:31, 14:32, 14:33

    def test_get_cached_bars_with_time_filter(self):
        """Should filter cached bars by start/end time."""
        df = self._make_df('2026-02-09 14:30', 5)
        self.handler._update_cache('IM0', df)

        start = datetime(2026, 2, 9, 14, 31)
        end = datetime(2026, 2, 9, 14, 33)
        cached = self.handler.get_cached_bars('IM0', start_time=start, end_time=end)
        self.assertIsNotNone(cached)
        self.assertEqual(len(cached), 3)  # 14:31, 14:32, 14:33

    def test_get_cached_bars_empty_symbol(self):
        """Should return None for non-cached symbol."""
        result = self.handler.get_cached_bars('UNKNOWN')
        self.assertIsNone(result)

    def test_get_latest_price(self):
        """Should return the last close price."""
        df = self._make_df('2026-02-09 14:30', 3)
        self.handler._update_cache('IM0', df)
        price = self.handler.get_latest_price('IM0')
        self.assertIsNotNone(price)
        self.assertEqual(price, 102.5)  # 100.5 + 2

    def test_get_latest_price_no_data(self):
        """Should return None when no data cached."""
        price = self.handler.get_latest_price('IM0')
        self.assertIsNone(price)


class TestMinuteDataHandlerDedup(unittest.TestCase):
    """Tests for bar deduplication (_extract_new_bars)."""

    def setUp(self):
        self.handler = MinuteDataHandler(data_dir=tempfile.mkdtemp())

    def test_extract_all_new(self):
        """All bars should be new when no last_bar_time."""
        df = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:30', periods=3, freq='1min'),
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [100, 200, 150],
        })
        bars = self.handler._extract_new_bars('IM0', df)
        self.assertEqual(len(bars), 3)

    def test_extract_only_new_bars(self):
        """Should only return bars newer than last seen."""
        self.handler._last_bar_time['IM0'] = datetime(2026, 2, 9, 14, 31)
        df = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:30', periods=4, freq='1min'),
            'open': [100, 101, 102, 103],
            'high': [101, 102, 103, 104],
            'low': [99, 100, 101, 102],
            'close': [100.5, 101.5, 102.5, 103.5],
            'volume': [100, 200, 150, 300],
        })
        bars = self.handler._extract_new_bars('IM0', df)
        self.assertEqual(len(bars), 2)  # 14:32 and 14:33

    def test_extract_updates_last_bar_time(self):
        """Should update _last_bar_time after extraction."""
        df = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:30', periods=3, freq='1min'),
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [100, 200, 150],
        })
        self.handler._extract_new_bars('IM0', df)
        self.assertEqual(
            self.handler._last_bar_time['IM0'],
            datetime(2026, 2, 9, 14, 32)
        )

    def test_extract_no_new_bars(self):
        """Should return empty list when all bars are old."""
        self.handler._last_bar_time['IM0'] = datetime(2026, 2, 9, 14, 35)
        df = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:30', periods=3, freq='1min'),
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [100, 200, 150],
        })
        bars = self.handler._extract_new_bars('IM0', df)
        self.assertEqual(len(bars), 0)


class TestMinuteDataHandlerLocalStorage(unittest.TestCase):
    """Tests for parquet local storage."""

    def setUp(self):
        self.data_dir = tempfile.mkdtemp()
        self.handler = MinuteDataHandler(data_dir=self.data_dir)

    def test_save_and_load(self):
        """Should save to parquet and load back correctly."""
        today = date(2026, 2, 9)
        df = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:30', periods=5, freq='1min'),
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'close': [100.5, 101.5, 102.5, 103.5, 104.5],
            'volume': [100, 200, 150, 300, 250],
        })
        self.handler._cache['IM0'] = df
        self.handler.subscribe(['IM0'])
        self.handler.save_to_local('IM0', today)

        loaded = self.handler.load_from_local('IM0', today)
        self.assertIsNotNone(loaded)
        self.assertEqual(len(loaded), 5)

    def test_load_nonexistent(self):
        """Should return None for non-existent date."""
        result = self.handler.load_from_local('IM0', date(2020, 1, 1))
        self.assertIsNone(result)

    def test_save_filters_by_date(self):
        """Should only save bars for the specified date."""
        df = pd.DataFrame({
            'datetime': [
                datetime(2026, 2, 8, 14, 30),
                datetime(2026, 2, 9, 14, 30),
                datetime(2026, 2, 9, 14, 31),
            ],
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [100, 200, 150],
        })
        self.handler._cache['IM0'] = df
        self.handler.save_to_local('IM0', date(2026, 2, 9))

        loaded = self.handler.load_from_local('IM0', date(2026, 2, 9))
        self.assertIsNotNone(loaded)
        self.assertEqual(len(loaded), 2)  # Only Feb 9 bars


class TestMinuteDataHandlerPolling(unittest.TestCase):
    """Tests for polling control."""

    def setUp(self):
        self.handler = MinuteDataHandler(data_dir=tempfile.mkdtemp())

    def test_is_running_default_false(self):
        """Should not be running by default."""
        self.assertFalse(self.handler.is_running)

    def test_stop_when_not_running(self):
        """Should not error when stopping while not running."""
        self.handler.stop()
        self.assertFalse(self.handler.is_running)

    @patch.object(MinuteDataHandler, '_polling_loop')
    def test_start_polling_sets_running(self, mock_loop):
        """start_polling should set _running to True."""
        self.handler.start_polling(interval=60)
        self.assertTrue(self.handler._running)
        self.handler.stop()

    @patch.object(MinuteDataHandler, '_polling_loop')
    def test_start_polling_twice_warns(self, mock_loop):
        """Starting polling twice should not create two threads."""
        self.handler.start_polling(interval=60)
        self.handler.start_polling(interval=60)  # Should warn, not double-start
        self.assertTrue(self.handler._running)
        self.handler.stop()


class TestMinuteDataHandlerGetPriceAtTime(unittest.TestCase):
    """Tests for get_price_at_time method."""

    def setUp(self):
        self.handler = MinuteDataHandler(data_dir=tempfile.mkdtemp())

    @patch('app.strategies.settlement_arbitrage.data_handler.date')
    def test_get_price_at_time(self, mock_date):
        """Should return close price at or before target time."""
        mock_date.today.return_value = date(2026, 2, 9)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        df = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:28', periods=5, freq='1min'),
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'close': [100.5, 101.5, 102.5, 103.5, 104.5],
            'volume': [100, 200, 150, 300, 250],
        })
        self.handler._cache['IM0'] = df

        price = self.handler.get_price_at_time('IM0', time(14, 30))
        self.assertIsNotNone(price)
        self.assertEqual(price, 102.5)  # 14:30 bar close

    def test_get_price_at_time_no_data(self):
        """Should return None when no data is cached."""
        result = self.handler.get_price_at_time('IM0', time(14, 30))
        self.assertIsNone(result)


class TestMinuteDataHandlerFetchHistorical(unittest.TestCase):
    """Tests for fetch_historical_bars method."""

    def setUp(self):
        self.data_dir = tempfile.mkdtemp()
        self.mock_ds = MagicMock()
        self.handler = MinuteDataHandler(data_source=self.mock_ds, data_dir=self.data_dir)

    def test_fetch_from_source_when_no_local(self):
        """Should fetch from data source when no local data exists."""
        df = pd.DataFrame({
            'datetime': pd.date_range('2026-02-09 14:00', periods=60, freq='1min'),
            'open': range(60),
            'high': range(60),
            'low': range(60),
            'close': range(60),
            'volume': range(60),
        })
        self.mock_ds.get_minute_bars.return_value = df

        result = self.handler.fetch_historical_bars(
            'IM0', date(2026, 2, 9), date(2026, 2, 9)
        )
        self.assertIsNotNone(result)
        self.mock_ds.get_minute_bars.assert_called()

    def test_fetch_returns_none_when_no_data(self):
        """Should return None when no data is available."""
        self.mock_ds.get_minute_bars.return_value = None
        result = self.handler.fetch_historical_bars(
            'IM0', date(2026, 2, 9), date(2026, 2, 9)
        )
        self.assertIsNone(result)


class TestMinuteDataHandlerRealtimeQuote(unittest.TestCase):
    """Tests for get_realtime_quote delegation."""

    def test_delegates_to_data_source(self):
        """Should delegate to data source's get_realtime_quote."""
        mock_ds = MagicMock()
        mock_ds.get_realtime_quote.return_value = {'last': 5900, 'volume': 1000}
        handler = MinuteDataHandler(data_source=mock_ds, data_dir=tempfile.mkdtemp())

        result = handler.get_realtime_quote('IM0')
        mock_ds.get_realtime_quote.assert_called_once_with('IM0')
        self.assertEqual(result['last'], 5900)


if __name__ == '__main__':
    unittest.main()
