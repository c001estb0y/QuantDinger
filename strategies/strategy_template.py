"""
Strategy Template for QuantDinger
策略模板

Usage:
1. Copy this file and rename it to your strategy name
2. Modify the strategy parameters and logic
3. Test with QuantDinger backtesting engine

Author: [Your Name]
Date: [Creation Date]
Version: 1.0
"""

# ============================================
# Strategy Information
# ============================================
STRATEGY_NAME = "My Strategy Name"
STRATEGY_VERSION = "1.0"
STRATEGY_DESCRIPTION = """
Brief description of your strategy.
Include the trading logic and expected behavior.
"""

# ============================================
# Strategy Parameters
# ============================================
# Customize these parameters for your strategy
PARAM_FAST_PERIOD = 10
PARAM_SLOW_PERIOD = 30
PARAM_STOP_LOSS_PCT = 0.02  # 2% stop loss
PARAM_TAKE_PROFIT_PCT = 0.05  # 5% take profit

# ============================================
# Indicator Calculation
# ============================================
# Example: Calculate moving averages
sma_fast = df['close'].rolling(PARAM_FAST_PERIOD).mean()
sma_slow = df['close'].rolling(PARAM_SLOW_PERIOD).mean()

# Add more indicators as needed
# rsi = calculate_rsi(df['close'], 14)
# macd, signal, hist = calculate_macd(df['close'])

# ============================================
# Signal Logic
# ============================================
# Buy condition: Fast MA crosses above Slow MA
raw_buy = (sma_fast > sma_slow) & (sma_fast.shift(1) <= sma_slow.shift(1))

# Sell condition: Fast MA crosses below Slow MA
raw_sell = (sma_fast < sma_slow) & (sma_fast.shift(1) >= sma_slow.shift(1))

# Clean NaN values and ensure boolean type
buy = raw_buy.fillna(False)
sell = raw_sell.fillna(False)

# Assign to DataFrame (required for backtesting)
df['buy'] = buy
df['sell'] = sell

# ============================================
# Visualization Formatting
# ============================================
# Calculate marker positions for chart display
buy_marks = [
    df['low'].iloc[i] * 0.995 if buy.iloc[i] else None 
    for i in range(len(df))
]

sell_marks = [
    df['high'].iloc[i] * 1.005 if sell.iloc[i] else None 
    for i in range(len(df))
]

# ============================================
# Output Configuration
# ============================================
output = {
    'name': STRATEGY_NAME,
    'plots': [
        {
            'name': f'SMA {PARAM_FAST_PERIOD}',
            'data': sma_fast.fillna(0).tolist(),
            'color': '#1890ff',  # Blue
            'overlay': True
        },
        {
            'name': f'SMA {PARAM_SLOW_PERIOD}',
            'data': sma_slow.fillna(0).tolist(),
            'color': '#faad14',  # Orange
            'overlay': True
        }
    ],
    'signals': [
        {
            'type': 'buy',
            'text': 'B',
            'data': buy_marks,
            'color': '#00E676'  # Green
        },
        {
            'type': 'sell',
            'text': 'S',
            'data': sell_marks,
            'color': '#FF5252'  # Red
        }
    ]
}

# ============================================
# Strategy Notes
# ============================================
"""
Notes for strategy development:

1. Data Handling:
   - df contains: time, open, high, low, close, volume
   - Always handle NaN values with fillna()
   - Use shift(1) for previous bar values
   
2. Signal Generation:
   - Use edge triggering to avoid repeated signals
   - buy/sell must be boolean Series
   
3. Visualization:
   - overlay=True: plot on main price chart
   - overlay=False: plot in separate panel
   
4. Performance:
   - Avoid for loops when possible
   - Use vectorized pandas/numpy operations
   
5. Testing:
   - Check backend logs for errors
   - Ensure data length matches for all plots
"""
