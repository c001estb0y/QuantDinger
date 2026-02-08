# Settlement Arbitrage Strategy - Minute Data Handler
# 结算价差套利策略 - 分钟数据处理器

"""
Handles real-time minute-level data subscription, polling,
caching, and local storage for the Settlement Arbitrage Strategy.
"""

import os
import threading
import time as time_mod
from datetime import datetime, date, time, timedelta
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from app.data_sources.cn_futures import CNFuturesDataSource
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Default data storage directory
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'futures', 'minute')


class MinuteBar:
    """
    Represents a single minute K-line bar.
    
    Attributes:
        symbol: Contract code (e.g., "IM2503")
        datetime: Bar timestamp
        open: Open price
        high: High price
        low: Low price
        close: Close price
        volume: Volume (lots)
        amount: Turnover amount (yuan)
    """
    __slots__ = ['symbol', 'datetime', 'open', 'high', 'low', 'close', 'volume', 'amount']
    
    def __init__(
        self,
        symbol: str,
        dt: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float = 0.0,
        amount: float = 0.0
    ):
        self.symbol = symbol
        self.datetime = dt
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.amount = amount
    
    def __repr__(self):
        return (
            f"MinuteBar({self.symbol}, {self.datetime}, "
            f"O={self.open}, H={self.high}, L={self.low}, C={self.close}, V={self.volume})"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'datetime': self.datetime,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'amount': self.amount,
        }


class MinuteDataHandler:
    """
    Minute-level data handler for the Settlement Arbitrage Strategy.
    
    Provides:
    - Real-time minute data polling via CNFuturesDataSource
    - K-line bar callback mechanism
    - In-memory cache for current day's data
    - Local file storage (parquet format) for historical data
    - Data deduplication and integrity checking
    
    Usage:
        handler = MinuteDataHandler()
        handler.subscribe(["IM0", "IC0"])
        handler.on_bar(my_callback_function)
        handler.start_polling(interval=60)
        # ... later
        handler.stop()
    """
    
    def __init__(
        self,
        data_source: Optional[CNFuturesDataSource] = None,
        data_dir: Optional[str] = None
    ):
        self.data_source = data_source or CNFuturesDataSource()
        self.data_dir = data_dir or DATA_DIR
        
        # Subscribed symbols
        self._symbols: List[str] = []
        
        # Callbacks
        self._bar_callbacks: List[Callable[[MinuteBar], None]] = []
        
        # In-memory cache: {symbol: DataFrame}
        self._cache: Dict[str, pd.DataFrame] = {}
        
        # Track last seen bar timestamp per symbol for dedup
        self._last_bar_time: Dict[str, datetime] = {}
        
        # Polling control
        self._polling_thread: Optional[threading.Thread] = None
        self._running = False
        self._poll_interval = 60  # seconds
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
    
    def subscribe(self, symbols: List[str]):
        """
        Subscribe to minute data for multiple symbols.
        
        Args:
            symbols: List of contract codes (e.g., ["IM0", "IC0"])
        """
        self._symbols = list(set(symbols))
        logger.info(f"MinuteDataHandler: subscribed to {self._symbols}")
        
        # Initialize cache for each symbol
        for symbol in self._symbols:
            if symbol not in self._cache:
                self._cache[symbol] = pd.DataFrame()
                # Try to load today's cached data
                self._load_today_cache(symbol)
    
    def unsubscribe(self, symbols: Optional[List[str]] = None):
        """
        Unsubscribe from symbols.
        
        Args:
            symbols: Symbols to unsubscribe. None to unsubscribe all.
        """
        if symbols is None:
            self._symbols = []
            self._cache.clear()
        else:
            for s in symbols:
                if s in self._symbols:
                    self._symbols.remove(s)
                self._cache.pop(s, None)
    
    def on_bar(self, callback: Callable[[MinuteBar], None]):
        """
        Register a callback function for new minute bars.
        
        The callback will be called with a MinuteBar instance
        each time a new bar is received.
        
        Args:
            callback: Function that accepts a MinuteBar
        """
        if callback not in self._bar_callbacks:
            self._bar_callbacks.append(callback)
    
    def remove_bar_callback(self, callback: Callable):
        """Remove a previously registered callback."""
        if callback in self._bar_callbacks:
            self._bar_callbacks.remove(callback)
    
    def start_polling(self, interval: int = 60):
        """
        Start polling for minute data in a background thread.
        
        Args:
            interval: Polling interval in seconds (default 60)
        """
        if self._running:
            logger.warning("MinuteDataHandler: polling already running")
            return
        
        self._poll_interval = interval
        self._running = True
        self._polling_thread = threading.Thread(
            target=self._polling_loop,
            name="MinuteDataHandler-Polling",
            daemon=True
        )
        self._polling_thread.start()
        logger.info(f"MinuteDataHandler: polling started (interval={interval}s)")
    
    def stop(self):
        """Stop polling and clean up."""
        self._running = False
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=5)
        logger.info("MinuteDataHandler: polling stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if polling is active."""
        return self._running
    
    def _polling_loop(self):
        """Main polling loop running in background thread."""
        while self._running:
            try:
                # Only poll during trading hours
                if self.data_source.is_trading_time():
                    self._fetch_and_process()
                else:
                    logger.debug("MinuteDataHandler: outside trading hours, skipping poll")
            except Exception as e:
                logger.error(f"MinuteDataHandler polling error: {e}", exc_info=True)
            
            # Sleep with early exit check
            for _ in range(self._poll_interval):
                if not self._running:
                    return
                time_mod.sleep(1)
    
    def _fetch_and_process(self):
        """Fetch latest minute data for all subscribed symbols and process."""
        for symbol in self._symbols:
            try:
                df = self.data_source.get_minute_bars(
                    symbol=symbol,
                    period=1,
                    count=10  # Only fetch recent bars for polling
                )
                
                if df is None or df.empty:
                    continue
                
                # Process new bars
                new_bars = self._extract_new_bars(symbol, df)
                
                if new_bars:
                    # Update cache
                    self._update_cache(symbol, df)
                    
                    # Fire callbacks
                    for bar in new_bars:
                        self._fire_callbacks(bar)
                        
            except Exception as e:
                logger.error(f"MinuteDataHandler: fetch error for {symbol}: {e}")
    
    def _extract_new_bars(self, symbol: str, df: pd.DataFrame) -> List[MinuteBar]:
        """
        Extract bars that haven't been seen yet (deduplication).
        
        Args:
            symbol: Contract symbol
            df: New data from source
            
        Returns:
            List of new MinuteBar instances
        """
        new_bars = []
        last_time = self._last_bar_time.get(symbol)
        
        for _, row in df.iterrows():
            bar_dt = pd.Timestamp(row['datetime']).to_pydatetime()
            
            if last_time is None or bar_dt > last_time:
                bar = MinuteBar(
                    symbol=symbol,
                    dt=bar_dt,
                    open_price=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row.get('volume', 0)),
                    amount=float(row.get('amount', 0)),
                )
                new_bars.append(bar)
        
        if new_bars:
            # Update last seen time
            self._last_bar_time[symbol] = max(b.datetime for b in new_bars)
        
        return new_bars
    
    def _fire_callbacks(self, bar: MinuteBar):
        """Fire all registered callbacks with a new bar."""
        for callback in self._bar_callbacks:
            try:
                callback(bar)
            except Exception as e:
                logger.error(f"MinuteDataHandler callback error: {e}", exc_info=True)
    
    # ========== Cache Management ==========
    
    def _update_cache(self, symbol: str, new_df: pd.DataFrame):
        """
        Update in-memory cache with new data.
        Deduplicates by datetime.
        
        Args:
            symbol: Contract symbol
            new_df: New data to merge
        """
        existing = self._cache.get(symbol)
        
        if existing is not None and not existing.empty:
            # Concatenate and deduplicate
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['datetime'], keep='last')
            combined = combined.sort_values('datetime').reset_index(drop=True)
            self._cache[symbol] = combined
        else:
            self._cache[symbol] = new_df.copy()
    
    def get_cached_bars(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get cached minute bars for a symbol.
        
        Args:
            symbol: Contract symbol
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            DataFrame or None
        """
        df = self._cache.get(symbol)
        if df is None or df.empty:
            return None
        
        result = df.copy()
        
        if start_time:
            result = result[result['datetime'] >= pd.Timestamp(start_time)]
        if end_time:
            result = result[result['datetime'] <= pd.Timestamp(end_time)]
        
        return result if not result.empty else None
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get the latest cached close price for a symbol.
        
        Args:
            symbol: Contract symbol
            
        Returns:
            Latest close price or None
        """
        df = self._cache.get(symbol)
        if df is not None and not df.empty:
            return float(df.iloc[-1]['close'])
        return None
    
    def get_price_at_time(self, symbol: str, target_time: time) -> Optional[float]:
        """
        Get the close price at a specific time (e.g., 14:30).
        
        Uses the bar closest to the target time.
        
        Args:
            symbol: Contract symbol
            target_time: Target time (e.g., time(14, 30))
            
        Returns:
            Close price at the target time, or None
        """
        df = self._cache.get(symbol)
        if df is None or df.empty:
            return None
        
        today = date.today()
        target_dt = datetime.combine(today, target_time)
        
        # Find the bar closest to (but not after) the target time
        df_today = df[df['datetime'].dt.date == today]
        if df_today.empty:
            return None
        
        before_target = df_today[df_today['datetime'] <= pd.Timestamp(target_dt)]
        if before_target.empty:
            return None
        
        return float(before_target.iloc[-1]['close'])
    
    # ========== Local Storage (Parquet) ==========
    
    def save_to_local(self, symbol: str, target_date: Optional[date] = None):
        """
        Save cached data to local parquet file.
        
        Args:
            symbol: Contract symbol
            target_date: Date to save. None for today.
        """
        df = self._cache.get(symbol)
        if df is None or df.empty:
            return
        
        if target_date is None:
            target_date = date.today()
        
        # Filter to target date
        df_day = df[df['datetime'].dt.date == target_date]
        if df_day.empty:
            return
        
        # Create directory
        product = symbol[:2].upper()
        symbol_dir = os.path.join(self.data_dir, product)
        os.makedirs(symbol_dir, exist_ok=True)
        
        # Save as parquet
        filepath = os.path.join(symbol_dir, f"{target_date.isoformat()}.parquet")
        df_day.to_parquet(filepath, index=False)
        logger.info(f"Saved {len(df_day)} bars to {filepath}")
    
    def load_from_local(
        self,
        symbol: str,
        target_date: date
    ) -> Optional[pd.DataFrame]:
        """
        Load historical minute data from local parquet file.
        
        Args:
            symbol: Contract symbol
            target_date: Date to load
            
        Returns:
            DataFrame or None
        """
        product = symbol[:2].upper()
        filepath = os.path.join(self.data_dir, product, f"{target_date.isoformat()}.parquet")
        
        if os.path.exists(filepath):
            try:
                df = pd.read_parquet(filepath)
                logger.info(f"Loaded {len(df)} bars from {filepath}")
                return df
            except Exception as e:
                logger.error(f"Failed to load {filepath}: {e}")
        
        return None
    
    def _load_today_cache(self, symbol: str):
        """Load today's data from local storage into cache if available."""
        today = date.today()
        df = self.load_from_local(symbol, today)
        if df is not None and not df.empty:
            self._cache[symbol] = df
            # Set last bar time
            self._last_bar_time[symbol] = pd.Timestamp(df['datetime'].iloc[-1]).to_pydatetime()
            logger.info(f"Cache warmed for {symbol}: {len(df)} bars")
    
    def save_all_and_cleanup(self):
        """
        Save all cached data to local storage and clean up old data.
        Typically called at end of trading day (e.g., 15:05).
        """
        today = date.today()
        
        for symbol in self._symbols:
            self.save_to_local(symbol, today)
        
        # Clean up data older than 30 days
        self._cleanup_old_data(max_age_days=30)
    
    def _cleanup_old_data(self, max_age_days: int = 30):
        """
        Remove local data files older than max_age_days.
        
        Args:
            max_age_days: Maximum age in days for local data files
        """
        cutoff = date.today() - timedelta(days=max_age_days)
        
        if not os.path.exists(self.data_dir):
            return
        
        removed_count = 0
        for product_dir in os.listdir(self.data_dir):
            full_path = os.path.join(self.data_dir, product_dir)
            if not os.path.isdir(full_path):
                continue
            
            for filename in os.listdir(full_path):
                if not filename.endswith('.parquet'):
                    continue
                try:
                    file_date = date.fromisoformat(filename.replace('.parquet', ''))
                    if file_date < cutoff:
                        os.remove(os.path.join(full_path, filename))
                        removed_count += 1
                except (ValueError, OSError):
                    continue
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old data files")
    
    # ========== Bulk Historical Data ==========
    
    def fetch_historical_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        period: int = 1
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical minute bars for a date range.
        
        First checks local cache, then fetches from data source if needed.
        
        Args:
            symbol: Contract symbol
            start_date: Start date
            end_date: End date
            period: K-line period in minutes
            
        Returns:
            DataFrame with combined data, or None
        """
        all_data = []
        
        current = start_date
        while current <= end_date:
            # Try local first
            df = self.load_from_local(symbol, current)
            
            if df is None:
                # Fetch from source
                df = self.data_source.get_minute_bars(
                    symbol=symbol,
                    period=period,
                    count=240,
                    start_date=current.isoformat()
                )
                
                if df is not None and not df.empty:
                    # Save locally for future use
                    product = symbol[:2].upper()
                    symbol_dir = os.path.join(self.data_dir, product)
                    os.makedirs(symbol_dir, exist_ok=True)
                    filepath = os.path.join(symbol_dir, f"{current.isoformat()}.parquet")
                    df.to_parquet(filepath, index=False)
            
            if df is not None and not df.empty:
                all_data.append(df)
            
            current += timedelta(days=1)
        
        if not all_data:
            return None
        
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.drop_duplicates(subset=['datetime'], keep='last')
        combined = combined.sort_values('datetime').reset_index(drop=True)
        
        return combined
    
    def get_realtime_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time quote for a symbol.
        Delegates to the data source.
        
        Args:
            symbol: Contract symbol
            
        Returns:
            Quote dict or None
        """
        return self.data_source.get_realtime_quote(symbol)
