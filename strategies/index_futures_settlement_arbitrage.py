"""
Stock Index Futures Settlement Price Arbitrage Strategy
股指期货结算价差套利策略

Strategy Description:
=====================
This strategy exploits the difference between futures closing price and settlement price.

For IC (CSI 500) and IM (CSI 1000) index futures:
- Entry Condition: After 2:30 PM, if the far-month contract continues to drop more than 1% from 2:30 PM
- Exit Condition: Sell at next day's opening
- Alternative Entry: Buy if price drops another 1% after the initial 1% drop

Theoretical Basis:
==================
1. Futures closing price ≠ Settlement price
2. Stock index futures settlement is based on the last hour's volume-weighted average price (VWAP)
3. Gold futures are even more extreme - they use full-day VWAP for settlement
4. When there's excessive decline in late trading, buying can capture the settlement price differential

Key Points:
- IC: CSI 500 Index Futures (中证500股指期货)
- IM: CSI 1000 Index Futures (中证1000股指期货)
- Settlement uses last hour VWAP, not closing price
- Extreme late session moves often revert to VWAP settlement price
"""

import pandas as pd
import numpy as np
from datetime import datetime, time

# Strategy Parameters
ENTRY_TIME = time(14, 30)  # 2:30 PM
DROP_THRESHOLD = 0.01     # 1% drop threshold
ADDITIONAL_DROP = 0.01    # Additional 1% for second entry condition


def calculate_price_change_from_time(df: pd.DataFrame, reference_time: time) -> pd.Series:
    """
    Calculate price change percentage from a specific time point.
    
    Args:
        df: DataFrame with OHLCV data and 'time' column
        reference_time: Time to start calculating change from (e.g., 14:30)
    
    Returns:
        Series with percentage change from reference time
    """
    # Ensure we have datetime type
    if not pd.api.types.is_datetime64_any_dtype(df['time']):
        df['time'] = pd.to_datetime(df['time'])
    
    # Get the time component
    df_time = df['time'].dt.time
    
    # Find rows at or after reference time
    mask = df_time >= reference_time
    
    # Get reference price (close at 14:30)
    reference_prices = df.loc[mask].groupby(df['time'].dt.date)['close'].first()
    
    # Map reference prices back to all rows
    dates = df['time'].dt.date
    ref_price_series = dates.map(reference_prices)
    
    # Calculate change
    price_change = (df['close'] - ref_price_series) / ref_price_series
    
    return price_change


def is_after_time(df: pd.DataFrame, check_time: time) -> pd.Series:
    """Check if current time is after specified time."""
    if not pd.api.types.is_datetime64_any_dtype(df['time']):
        df['time'] = pd.to_datetime(df['time'])
    
    return df['time'].dt.time >= check_time


# ==============================================
# Main Strategy Logic for QuantDinger Platform
# ==============================================

# Assuming df is provided by QuantDinger with OHLCV data

# 1. Calculate price change from 14:30
# Note: This requires intraday data with timestamps
price_change = pd.Series(dtype=float)

# For demonstration, we'll use a simplified version
# In real implementation, you'd need minute-level data with proper timestamps

# Calculate simple price change from reference
df['price_change_pct'] = df['close'].pct_change()

# Cumulative change (for multi-bar analysis)
df['rolling_change'] = df['close'].rolling(window=5).apply(
    lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0] if len(x) > 0 and x.iloc[0] != 0 else 0
)

# 2. Signal Logic
# -----------------------

# Primary condition: Price drops more than 1%
condition_drop_1pct = df['rolling_change'] < -DROP_THRESHOLD

# Secondary condition: Price drops another 1% (total 2%)
condition_drop_2pct = df['rolling_change'] < -(DROP_THRESHOLD + ADDITIONAL_DROP)

# Buy signal: Either condition met
# Note: In real implementation, need to check time condition
raw_buy = condition_drop_1pct | condition_drop_2pct

# Sell signal: Next day opening (simplified to next bar)
raw_sell = raw_buy.shift(1).fillna(False)

# Clean NaN and ensure boolean
buy = raw_buy.fillna(False)
sell = raw_sell.fillna(False)

# Assign to df
df['buy'] = buy
df['sell'] = sell

# 3. Visualization Formatting
# -----------------------
buy_marks = [
    df['low'].iloc[i] * 0.995 if buy.iloc[i] else None 
    for i in range(len(df))
]

sell_marks = [
    df['high'].iloc[i] * 1.005 if sell.iloc[i] else None 
    for i in range(len(df))
]

# 4. Final Output
# -----------------------
output = {
    'name': '股指期货结算价差套利策略',
    'plots': [
        {
            'name': 'Rolling Change %',
            'data': (df['rolling_change'].fillna(0) * 100).tolist(),
            'color': '#ff6b6b',
            'overlay': False  # Show in separate panel
        },
        {
            'name': '-1% Threshold',
            'data': [-1.0] * len(df),
            'color': '#ffa502',
            'overlay': False
        },
        {
            'name': '-2% Threshold',
            'data': [-2.0] * len(df),
            'color': '#ff4757',
            'overlay': False
        }
    ],
    'signals': [
        {
            'type': 'buy',
            'text': '买',
            'data': buy_marks,
            'color': '#00E676'
        },
        {
            'type': 'sell',
            'text': '卖',
            'data': sell_marks,
            'color': '#FF5252'
        }
    ]
}
