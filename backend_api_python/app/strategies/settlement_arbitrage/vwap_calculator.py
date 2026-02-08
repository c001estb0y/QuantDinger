# Settlement Arbitrage Strategy - VWAP Calculator
# 结算价差套利策略 - VWAP结算价计算器

"""
Calculates the Volume-Weighted Average Price (VWAP) used as the settlement
price for Chinese stock index futures.

The official settlement price for CFFEX index futures is the VWAP of the
last hour of trading (14:00 - 15:00). This module provides both historical
and real-time VWAP calculation capabilities.
"""

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.data_sources.cn_futures import CNFuturesDataSource
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Default VWAP calculation window: 14:00 - 15:00
DEFAULT_VWAP_START = time(14, 0)
DEFAULT_VWAP_END = time(15, 0)


class VWAPCalculator:
    """
    Settlement Price (VWAP) Calculator for Chinese Index Futures.
    
    VWAP = Σ(Price × Volume) / Σ(Volume)
    
    where Price is typically the close price of each minute bar
    during the settlement window (14:00 - 15:00).
    
    Usage:
        calculator = VWAPCalculator(data_source)
        vwap = calculator.calculate_vwap(minute_bars)
        settlement = calculator.get_settlement_price("IM0", date(2026, 2, 8))
    """
    
    def __init__(self, data_source: Optional[CNFuturesDataSource] = None):
        self.data_source = data_source or CNFuturesDataSource()
        
        # Cache for computed VWAP values: {(symbol, date_str): float}
        self._vwap_cache: Dict[Tuple[str, str], float] = {}
        
        # Incremental VWAP state for real-time calculation
        self._rt_cumulative_pv: Dict[str, float] = {}  # Σ(Price * Volume)
        self._rt_cumulative_v: Dict[str, float] = {}   # Σ(Volume)
        self._rt_bar_count: Dict[str, int] = {}
    
    def calculate_vwap(
        self,
        bars: pd.DataFrame,
        start_time: time = DEFAULT_VWAP_START,
        end_time: time = DEFAULT_VWAP_END,
        price_col: str = 'close'
    ) -> Optional[float]:
        """
        Calculate VWAP for a given set of minute bars within a time window.
        
        VWAP = Σ(Price × Volume) / Σ(Volume)
        
        Args:
            bars: DataFrame with columns: datetime, open, high, low, close, volume
            start_time: VWAP window start time (default 14:00)
            end_time: VWAP window end time (default 15:00)
            price_col: Which price column to use (default 'close')
            
        Returns:
            VWAP value, or None if insufficient data
        """
        if bars is None or bars.empty:
            logger.warning("calculate_vwap: empty bars input")
            return None
        
        if price_col not in bars.columns or 'volume' not in bars.columns:
            logger.error(f"calculate_vwap: missing required columns ({price_col}, volume)")
            return None
        
        # Ensure datetime column is proper type
        df = bars.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['datetime']):
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Filter to VWAP window
        df_time = df['datetime'].dt.time
        mask = (df_time >= start_time) & (df_time <= end_time)
        window_df = df[mask]
        
        if window_df.empty:
            logger.warning(
                f"calculate_vwap: no bars in window {start_time}-{end_time}, "
                f"available range: {df_time.min()}-{df_time.max()}"
            )
            return None
        
        # Calculate VWAP
        prices = window_df[price_col].astype(float)
        volumes = window_df['volume'].astype(float)
        
        total_volume = volumes.sum()
        
        if total_volume == 0:
            # If no volume data, use simple average
            logger.warning("calculate_vwap: zero total volume, using simple average")
            return float(prices.mean())
        
        pv_sum = (prices * volumes).sum()
        vwap = pv_sum / total_volume
        
        return round(float(vwap), 2)
    
    def calculate_vwap_typical(
        self,
        bars: pd.DataFrame,
        start_time: time = DEFAULT_VWAP_START,
        end_time: time = DEFAULT_VWAP_END
    ) -> Optional[float]:
        """
        Calculate VWAP using typical price = (High + Low + Close) / 3.
        
        This is an alternative calculation method that may better represent
        the average trading price within each bar.
        
        Args:
            bars: DataFrame with datetime, high, low, close, volume columns
            start_time: VWAP window start time
            end_time: VWAP window end time
            
        Returns:
            VWAP value, or None
        """
        if bars is None or bars.empty:
            return None
        
        df = bars.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['datetime']):
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Filter to window
        df_time = df['datetime'].dt.time
        mask = (df_time >= start_time) & (df_time <= end_time)
        window_df = df[mask].copy()
        
        if window_df.empty:
            return None
        
        # Calculate typical price
        typical = (
            window_df['high'].astype(float) +
            window_df['low'].astype(float) +
            window_df['close'].astype(float)
        ) / 3.0
        
        volumes = window_df['volume'].astype(float)
        total_volume = volumes.sum()
        
        if total_volume == 0:
            return float(typical.mean())
        
        vwap = (typical * volumes).sum() / total_volume
        return round(float(vwap), 2)
    
    def get_settlement_price(
        self,
        symbol: str,
        target_date: Optional[date] = None,
        use_cache: bool = True
    ) -> Optional[float]:
        """
        Get the settlement price for a symbol on a given date.
        
        First tries to get the official settlement price from the data source.
        If unavailable, calculates VWAP from minute data.
        
        Args:
            symbol: Contract code (e.g., "IM0")
            target_date: Date to query. None for latest.
            use_cache: Whether to use cached values
            
        Returns:
            Settlement price, or None
        """
        date_str = target_date.isoformat() if target_date else "latest"
        cache_key = (symbol, date_str)
        
        # Check cache
        if use_cache and cache_key in self._vwap_cache:
            return self._vwap_cache[cache_key]
        
        # Try 1: Get official settlement price from data source
        try:
            official = self.data_source.get_settlement_price(
                symbol,
                date_str if target_date else None
            )
            if official and official > 0:
                self._vwap_cache[cache_key] = official
                return official
        except Exception as e:
            logger.debug(f"Official settlement price unavailable: {e}")
        
        # Try 2: Calculate from minute data
        try:
            bars = self.data_source.get_minute_bars(
                symbol=symbol,
                period=1,
                count=240,
                start_date=date_str if target_date else None
            )
            
            if bars is not None and not bars.empty:
                vwap = self.calculate_vwap(bars)
                if vwap:
                    self._vwap_cache[cache_key] = vwap
                    return vwap
        except Exception as e:
            logger.debug(f"VWAP calculation from minute data failed: {e}")
        
        return None
    
    # ========== Real-time Incremental VWAP ==========
    
    def reset_realtime(self, symbol: Optional[str] = None):
        """
        Reset real-time VWAP state.
        
        Should be called at the start of each VWAP window (e.g., 14:00).
        
        Args:
            symbol: Symbol to reset. None to reset all.
        """
        if symbol:
            self._rt_cumulative_pv.pop(symbol, None)
            self._rt_cumulative_v.pop(symbol, None)
            self._rt_bar_count.pop(symbol, None)
        else:
            self._rt_cumulative_pv.clear()
            self._rt_cumulative_v.clear()
            self._rt_bar_count.clear()
    
    def update_realtime(
        self,
        symbol: str,
        price: float,
        volume: float
    ) -> float:
        """
        Update real-time VWAP with a new bar.
        
        Call this method for each new minute bar during the VWAP window.
        
        Args:
            symbol: Contract symbol
            price: Bar close price
            volume: Bar volume
            
        Returns:
            Current real-time VWAP value
        """
        if symbol not in self._rt_cumulative_pv:
            self._rt_cumulative_pv[symbol] = 0.0
            self._rt_cumulative_v[symbol] = 0.0
            self._rt_bar_count[symbol] = 0
        
        self._rt_cumulative_pv[symbol] += price * volume
        self._rt_cumulative_v[symbol] += volume
        self._rt_bar_count[symbol] += 1
        
        total_v = self._rt_cumulative_v[symbol]
        
        if total_v > 0:
            return round(self._rt_cumulative_pv[symbol] / total_v, 2)
        else:
            # No volume, return simple average
            return round(
                self._rt_cumulative_pv[symbol] / max(self._rt_bar_count[symbol], 1), 2
            )
    
    def get_realtime_vwap(self, symbol: str) -> Optional[float]:
        """
        Get current real-time VWAP for a symbol.
        
        Args:
            symbol: Contract symbol
            
        Returns:
            Current VWAP or None if no data
        """
        total_v = self._rt_cumulative_v.get(symbol, 0)
        total_pv = self._rt_cumulative_pv.get(symbol, 0)
        count = self._rt_bar_count.get(symbol, 0)
        
        if count == 0:
            return None
        
        if total_v > 0:
            return round(total_pv / total_v, 2)
        else:
            return round(total_pv / count, 2)
    
    def get_realtime_stats(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time VWAP calculation statistics.
        
        Args:
            symbol: Contract symbol
            
        Returns:
            Dict with vwap, total_volume, bar_count, etc.
        """
        vwap = self.get_realtime_vwap(symbol)
        return {
            'symbol': symbol,
            'vwap': vwap,
            'total_volume': self._rt_cumulative_v.get(symbol, 0),
            'total_pv': self._rt_cumulative_pv.get(symbol, 0),
            'bar_count': self._rt_bar_count.get(symbol, 0),
        }
    
    # ========== Utility Methods ==========
    
    def calculate_price_vs_settlement(
        self,
        current_price: float,
        settlement_price: float
    ) -> Dict[str, float]:
        """
        Calculate the deviation between current price and settlement price.
        
        This is the core metric for the Settlement Arbitrage Strategy.
        When current_price < settlement_price, there's a potential opportunity.
        
        Args:
            current_price: Current trading price
            settlement_price: Settlement (VWAP) price
            
        Returns:
            Dict with: deviation, deviation_pct
        """
        if settlement_price == 0:
            return {'deviation': 0, 'deviation_pct': 0}
        
        deviation = current_price - settlement_price
        deviation_pct = deviation / settlement_price
        
        return {
            'deviation': round(deviation, 2),
            'deviation_pct': round(deviation_pct, 6),
        }
    
    def clear_cache(self):
        """Clear all cached VWAP values."""
        self._vwap_cache.clear()
        self.reset_realtime()
