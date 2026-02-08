# Settlement Arbitrage Strategy Module
# 结算价差套利策略模块

"""
This module implements the Settlement Price Arbitrage Strategy
for Chinese Index Futures (IC/IM/IF/IH).

Strategy Logic:
1. Monitor price movements after 14:30
2. Enter long position when price drops > 1% from 14:30 base price
3. Add position when price drops > 2%
4. Exit at next day's opening price

Main Components:
- strategy.py: Core strategy logic
- data_handler.py: Minute data processing
- vwap_calculator.py: Settlement price (VWAP) calculation
- position_manager.py: Position management
- risk_manager.py: Risk control
- scheduler.py: Strategy scheduler
- config.py: Configuration management
- backtest.py: Backtest engine
"""

from .config import StrategyConfig, RiskConfig, BacktestConfig
from .strategy import SettlementArbitrageStrategy, SignalType, StrategyState, Signal
from .data_handler import MinuteDataHandler, MinuteBar
from .vwap_calculator import VWAPCalculator
from .position_manager import PositionManager, Position, TradeRecord
from .risk_manager import RiskManager, RiskEvent, RiskEventType
from .scheduler import StrategyScheduler, get_scheduler, create_scheduler
from .backtest import SettlementStrategyBacktest, BacktestReport

__all__ = [
    # Config
    'StrategyConfig',
    'RiskConfig',
    'BacktestConfig',
    # Strategy
    'SettlementArbitrageStrategy',
    'SignalType',
    'StrategyState',
    'Signal',
    # Data
    'MinuteDataHandler',
    'MinuteBar',
    # VWAP
    'VWAPCalculator',
    # Position
    'PositionManager',
    'Position',
    'TradeRecord',
    # Risk
    'RiskManager',
    'RiskEvent',
    'RiskEventType',
    # Scheduler
    'StrategyScheduler',
    'get_scheduler',
    'create_scheduler',
    # Backtest
    'SettlementStrategyBacktest',
    'BacktestReport',
]

__version__ = '1.0.0'
