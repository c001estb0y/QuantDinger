"""
Futures Indicator Helpers - Helper functions for futures minute-level strategies

This module provides helper functions that are injected into the indicator editor
execution environment, enabling users to write minute-level futures strategies
without modifying any frontend or backend code.

Supported functions:
- get_minute_data(symbol, date) / get_minute_data_range(symbol, start, end)
- filter_by_time(df, start_time, end_time)
- get_price_at_time(df, target_time)
- VWAP(df) / VWAP_PERIOD(df, start_time, end_time)
- get_contract_info(symbol)
- calculate_margin(symbol, price, quantity)
- calculate_fee(symbol, price, quantity, direction)
"""

import re
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.data_sources.cn_futures import CNFuturesDataSource
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FuturesIndicatorHelpers:
    """
    Provides helper functions for futures indicator scripts.

    These functions are injected into the indicator editor execution environment
    to enable minute-level data access, VWAP calculation, time filtering, etc.

    Usage in BacktestService:
        helpers = FuturesIndicatorHelpers(symbol="IM0")
        funcs = helpers.get_all_functions()
        # Inject funcs into exec_env
    """

    # Default fee rates for CFFEX stock index futures
    DEFAULT_FEE_RATE_OPEN = 0.000023
    DEFAULT_FEE_RATE_CLOSE = 0.000023

    def __init__(
        self,
        symbol: str = "",
        data_source: Optional[CNFuturesDataSource] = None,
        daily_df: Optional[pd.DataFrame] = None,
    ):
        self.symbol = self._normalize_symbol(symbol)
        self.data_source = data_source or CNFuturesDataSource()
        # In-memory cache for minute data: {(symbol, date_str): DataFrame}
        self._minute_cache: Dict[Tuple[str, str], pd.DataFrame] = {}
        # Daily K-line DataFrame (injected from backtest engine for fallback)
        self._daily_df = daily_df
    
    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """
        Normalize symbol to ensure it's a valid contract code.
        
        Frontend may pass bare product codes like 'IM', 'IC' without
        the contract suffix. We auto-append '0' to indicate main contract.
        
        Examples:
            'IM'   -> 'IM0'   (main contract)
            'IC'   -> 'IC0'
            'IM0'  -> 'IM0'   (already valid)
            'IM2503' -> 'IM2503' (specific contract, keep as-is)
        """
        if not symbol:
            return symbol
        s = symbol.upper().strip()
        # If it's exactly 2 letters (bare product code), append '0' for main contract
        if len(s) == 2 and s.isalpha() and s in ('IC', 'IM', 'IF', 'IH'):
            return s + '0'
        return s

    # ========== FR-1: Minute-level data access ==========

    def get_minute_data(
        self, symbol: Optional[str] = None, date_str: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get minute-level K-line data for a specific date.

        First tries to fetch real minute data from the data source.
        If that fails (e.g. historical date beyond API range), falls back
        to synthesizing approximate minute data from the daily K-line bar.

        Args:
            symbol: Contract code (e.g., "IM0", "IC0"). Defaults to current symbol.
            date_str: Date string (YYYY-MM-DD). If None, returns latest data.

        Returns:
            DataFrame with columns: datetime, open, high, low, close, volume
            Returns None if data is unavailable.
        """
        sym = self._normalize_symbol(symbol) if symbol else self.symbol
        if not sym:
            logger.warning("get_minute_data: no symbol specified")
            return None

        cache_key = (sym, date_str or "latest")
        if cache_key in self._minute_cache:
            return self._minute_cache[cache_key].copy()

        # Attempt 1: Fetch real minute data from data source
        try:
            df = self.data_source.get_minute_bars(
                symbol=sym,
                period=1,
                count=240,
                start_date=date_str,
            )

            if df is not None and not df.empty:
                # Filter to the specific date if provided
                if date_str:
                    target_date = pd.Timestamp(date_str).date()
                    df = df[df["datetime"].dt.date == target_date]

                if not df.empty:
                    df = df.reset_index(drop=True)
                    self._minute_cache[cache_key] = df
                    return df.copy()
        except Exception as e:
            logger.debug(f"get_minute_data real fetch failed for {sym} on {date_str}: {e}")

        # Attempt 2: Synthesize from daily K-line data (fallback for historical dates)
        if date_str and self._daily_df is not None and not self._daily_df.empty:
            synth = self._synthesize_minute_from_daily(date_str)
            if synth is not None and not synth.empty:
                self._minute_cache[cache_key] = synth
                return synth.copy()

        return None

    def _synthesize_minute_from_daily(self, date_str: str) -> Optional[pd.DataFrame]:
        """
        Synthesize approximate minute-level data from daily K-line bar.

        When real minute data is unavailable (e.g. historical dates beyond
        the API's range), we create synthetic minute bars using the daily
        OHLCV data. The synthetic data distributes the price movement
        across key intraday time points.

        This allows strategies that need `get_price_at_time("14:30")` etc.
        to still function in backtesting, using reasonable approximations.

        Args:
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Synthetic minute DataFrame, or None if daily data is unavailable.
        """
        try:
            df = self._daily_df
            if df is None or df.empty:
                logger.debug(f"_synthesize_minute_from_daily: _daily_df is None or empty for {date_str}")
                return None
            
            target_date = pd.Timestamp(date_str).date()
            logger.debug(f"_synthesize_minute_from_daily: looking for date {target_date} in {len(df)} daily bars")

            # Find the daily bar for this date
            daily_row = None
            if 'datetime' in df.columns:
                mask = pd.to_datetime(df['datetime']).dt.date == target_date
                matched = df[mask]
                if not matched.empty:
                    daily_row = matched.iloc[0]
            elif hasattr(df.index, 'date'):
                try:
                    mask = df.index.date == target_date
                    matched = df[mask]
                    if not matched.empty:
                        daily_row = matched.iloc[0]
                except Exception:
                    pass

            if daily_row is None:
                return None

            o = float(daily_row['open'])
            h = float(daily_row['high'])
            l = float(daily_row['low'])
            c = float(daily_row['close'])
            v = float(daily_row.get('volume', 0))

            # Create synthetic minute bars at key time points
            # Chinese futures trading hours: 09:30-11:30, 13:00-15:00
            # We generate bars at 30-min intervals + key points (14:30, 14:59)
            time_prices = [
                ("09:30", o),
                ("10:00", o + (h - o) * 0.3),
                ("10:30", h),
                ("11:00", h - (h - l) * 0.2),
                ("11:30", o + (c - o) * 0.4),
                ("13:00", o + (c - o) * 0.45),
                ("13:30", o + (c - o) * 0.5),
                ("14:00", o + (c - o) * 0.6),
                ("14:30", o + (c - o) * 0.7),
                ("14:45", o + (c - o) * 0.85),
                ("14:59", c),
                ("15:00", c),
            ]

            rows = []
            bar_volume = v / len(time_prices) if v > 0 else 0
            for t_str, price in time_prices:
                dt = pd.Timestamp(f"{date_str} {t_str}:00")
                rows.append({
                    "datetime": dt,
                    "open": round(price, 2),
                    "high": round(min(price * 1.001, h), 2),
                    "low": round(max(price * 0.999, l), 2),
                    "close": round(price, 2),
                    "volume": round(bar_volume, 0),
                })

            result = pd.DataFrame(rows)
            logger.debug(f"Synthesized {len(result)} minute bars from daily data for {date_str}")
            return result

        except Exception as e:
            logger.error(f"_synthesize_minute_from_daily failed for {date_str}: {e}")
            return None

    def get_minute_data_range(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Get minute-level K-line data for a date range.

        Args:
            symbol: Contract code. Defaults to current symbol.
            start_date: Start date string (YYYY-MM-DD).
            end_date: End date string (YYYY-MM-DD).

        Returns:
            DataFrame with all minute bars in the date range.
        """
        sym = symbol or self.symbol
        if not sym:
            return None

        try:
            all_dfs = []
            start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

            if start and end:
                current = start
                while current <= end:
                    date_str = current.isoformat()
                    df = self.get_minute_data(sym, date_str)
                    if df is not None and not df.empty:
                        all_dfs.append(df)
                    current += timedelta(days=1)

            if all_dfs:
                result = pd.concat(all_dfs, ignore_index=True)
                result = result.sort_values("datetime").reset_index(drop=True)
                return result

            return None
        except Exception as e:
            logger.error(f"get_minute_data_range failed: {e}")
            return None

    # ========== FR-2: Time filtering ==========

    @staticmethod
    def filter_by_time(
        df: pd.DataFrame, start_time: str, end_time: str
    ) -> pd.DataFrame:
        """
        Filter DataFrame rows by time range.

        Args:
            df: DataFrame with 'datetime' column.
            start_time: Start time string (HH:MM or HH:MM:SS).
            end_time: End time string (HH:MM or HH:MM:SS).

        Returns:
            Filtered DataFrame.
        """
        if df is None or df.empty:
            return pd.DataFrame()

        try:
            df_copy = df.copy()
            if not pd.api.types.is_datetime64_any_dtype(df_copy["datetime"]):
                df_copy["datetime"] = pd.to_datetime(df_copy["datetime"])

            start_t = FuturesIndicatorHelpers._parse_time(start_time)
            end_t = FuturesIndicatorHelpers._parse_time(end_time)

            if start_t is None or end_t is None:
                logger.warning(f"filter_by_time: invalid time format: {start_time}, {end_time}")
                return df_copy

            mask = (df_copy["datetime"].dt.time >= start_t) & (
                df_copy["datetime"].dt.time <= end_t
            )
            return df_copy[mask].reset_index(drop=True)
        except Exception as e:
            logger.error(f"filter_by_time error: {e}")
            return df

    @staticmethod
    def get_price_at_time(
        df: pd.DataFrame, target_time: str, price_col: str = "close"
    ) -> Optional[float]:
        """
        Get the price at (or closest before) a specific time.

        Args:
            df: DataFrame with 'datetime' column.
            target_time: Target time string (HH:MM or HH:MM:SS).
            price_col: Price column name (default 'close').

        Returns:
            Price value, or None if not found.
        """
        if df is None or df.empty:
            return None

        try:
            df_copy = df.copy()
            if not pd.api.types.is_datetime64_any_dtype(df_copy["datetime"]):
                df_copy["datetime"] = pd.to_datetime(df_copy["datetime"])

            target_t = FuturesIndicatorHelpers._parse_time(target_time)
            if target_t is None:
                return None

            # Find closest bar at or before target time
            before = df_copy[df_copy["datetime"].dt.time <= target_t]
            if not before.empty:
                return float(before.iloc[-1][price_col])

            return None
        except Exception as e:
            logger.error(f"get_price_at_time error: {e}")
            return None

    # ========== FR-3: VWAP calculation ==========

    @staticmethod
    def VWAP(df: pd.DataFrame, price_col: str = "close") -> Optional[float]:
        """
        Calculate Volume-Weighted Average Price for the given DataFrame.

        VWAP = Σ(Price × Volume) / Σ(Volume)

        Args:
            df: DataFrame with price and volume columns.
            price_col: Price column name (default 'close').

        Returns:
            VWAP value, or None if insufficient data.
        """
        if df is None or df.empty:
            return None

        try:
            prices = df[price_col].astype(float)
            volumes = df["volume"].astype(float)

            total_volume = volumes.sum()
            if total_volume == 0:
                # No volume data, use simple average
                return float(prices.mean())

            return float((prices * volumes).sum() / total_volume)
        except Exception as e:
            logger.error(f"VWAP calculation error: {e}")
            return None

    @staticmethod
    def VWAP_PERIOD(
        df: pd.DataFrame,
        start_time: str,
        end_time: str,
        price_col: str = "close",
    ) -> Optional[float]:
        """
        Calculate VWAP for a specific time period.

        Args:
            df: DataFrame with datetime, price, and volume columns.
            start_time: Start time string (HH:MM).
            end_time: End time string (HH:MM).
            price_col: Price column name.

        Returns:
            VWAP value for the specified period.
        """
        filtered = FuturesIndicatorHelpers.filter_by_time(df, start_time, end_time)
        if filtered.empty:
            return None
        return FuturesIndicatorHelpers.VWAP(filtered, price_col)

    # ========== FR-5: Futures-specific parameters ==========

    def get_contract_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get contract information for a futures symbol.

        Args:
            symbol: Contract code. Defaults to current symbol.

        Returns:
            Dict with: multiplier, margin_ratio, fee_rate, tick_size, product, name
        """
        sym = symbol or self.symbol
        if not sym:
            return {}

        try:
            product = sym[:2].upper()
            product_info = CNFuturesDataSource.PRODUCTS.get(product, {})

            return {
                "symbol": sym,
                "product": product,
                "name": product_info.get("name", ""),
                "multiplier": product_info.get("multiplier", 200),
                "margin_ratio": product_info.get("margin_ratio", 0.12),
                "tick_size": product_info.get("tick_size", 0.2),
                "fee_rate_open": self.DEFAULT_FEE_RATE_OPEN,
                "fee_rate_close": self.DEFAULT_FEE_RATE_CLOSE,
            }
        except Exception as e:
            logger.error(f"get_contract_info error: {e}")
            return {}

    def calculate_margin(
        self, symbol: Optional[str] = None, price: float = 0, quantity: int = 1
    ) -> float:
        """
        Calculate margin required for opening a futures position.

        Margin = Price × Multiplier × Quantity × Margin_Ratio

        Args:
            symbol: Contract code. Defaults to current symbol.
            price: Entry price.
            quantity: Number of contracts.

        Returns:
            Required margin amount.
        """
        info = self.get_contract_info(symbol)
        multiplier = info.get("multiplier", 200)
        margin_ratio = info.get("margin_ratio", 0.12)
        return price * multiplier * quantity * margin_ratio

    def calculate_fee(
        self,
        symbol: Optional[str] = None,
        price: float = 0,
        quantity: int = 1,
        direction: str = "open",
    ) -> float:
        """
        Calculate trading fee for a futures trade.

        Fee = Price × Multiplier × Quantity × Fee_Rate

        Args:
            symbol: Contract code. Defaults to current symbol.
            price: Trade price.
            quantity: Number of contracts.
            direction: 'open' or 'close'.

        Returns:
            Fee amount.
        """
        info = self.get_contract_info(symbol)
        multiplier = info.get("multiplier", 200)
        fee_rate = (
            info.get("fee_rate_open", self.DEFAULT_FEE_RATE_OPEN)
            if direction == "open"
            else info.get("fee_rate_close", self.DEFAULT_FEE_RATE_CLOSE)
        )
        return price * multiplier * quantity * fee_rate

    # ========== FR-6: Strategy metadata parsing ==========

    @staticmethod
    def parse_strategy_metadata(code: str) -> Dict[str, Any]:
        """
        Parse strategy metadata from code comments.

        Supported metadata annotations:
            # @strategy_name: ...
            # @strategy_version: ...
            # @data_requirement: minute | daily | both

        Args:
            code: User's indicator code.

        Returns:
            Dict with parsed metadata.
        """
        metadata = {}

        patterns = {
            "strategy_name": r"#\s*@strategy_name:\s*(.+)",
            "strategy_version": r"#\s*@strategy_version:\s*(.+)",
            "data_requirement": r"#\s*@data_requirement:\s*(.+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, code)
            if match:
                metadata[key] = match.group(1).strip()

        return metadata

    # ========== Helper: get all functions for injection ==========

    def get_all_functions(self) -> Dict[str, Any]:
        """
        Get all helper functions ready for injection into execution environment.

        Returns:
            Dict of {function_name: callable}.
        """
        return {
            # FR-1: Minute data access
            "get_minute_data": self.get_minute_data,
            "get_minute_data_range": self.get_minute_data_range,
            # FR-2: Time filtering
            "filter_by_time": self.filter_by_time,
            "get_price_at_time": self.get_price_at_time,
            # FR-3: VWAP
            "VWAP": self.VWAP,
            "VWAP_PERIOD": self.VWAP_PERIOD,
            # FR-5: Futures parameters
            "get_contract_info": self.get_contract_info,
            "calculate_margin": self.calculate_margin,
            "calculate_fee": self.calculate_fee,
            # Symbol reference
            "symbol": self.symbol,
        }

    # ========== Internal helpers ==========

    @staticmethod
    def _parse_time(time_str: str) -> Optional[time]:
        """Parse time string (HH:MM or HH:MM:SS) to time object."""
        try:
            parts = time_str.strip().split(":")
            if len(parts) == 2:
                return time(int(parts[0]), int(parts[1]))
            elif len(parts) == 3:
                return time(int(parts[0]), int(parts[1]), int(parts[2]))
            return None
        except (ValueError, IndexError):
            return None

    def clear_cache(self):
        """Clear all minute data caches."""
        self._minute_cache.clear()
