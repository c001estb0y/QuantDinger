# Settlement Arbitrage Strategy - Configuration
# 结算价差套利策略 - 配置管理

"""
Strategy configuration dataclasses for Settlement Arbitrage Strategy.
"""

from dataclasses import dataclass, field
from datetime import time
from typing import List, Optional


@dataclass
class StrategyConfig:
    """
    Strategy configuration for Settlement Arbitrage.
    结算价差套利策略配置
    """
    
    # Trading symbols / 交易品种
    symbols: List[str] = field(default_factory=lambda: ["IM0", "IC0"])
    
    # Entry conditions / 入场条件
    watch_start: time = field(default_factory=lambda: time(14, 30))  # 观察开始时间
    watch_end: time = field(default_factory=lambda: time(15, 0))      # 观察结束时间
    threshold_1: float = 0.01   # 首仓阈值 1%
    threshold_2: float = 0.02   # 追加阈值 2%
    alert_threshold: float = 0.008  # 预警阈值 0.8%
    
    # Position management / 仓位管理
    position_size_1: int = 1    # 首仓手数
    position_size_2: int = 1    # 追加手数
    max_position_per_symbol: int = 2  # 单品种最大持仓
    
    # Notification / 通知设置
    notification_channels: List[str] = field(default_factory=lambda: ["telegram"])
    telegram_chat_id: Optional[str] = None
    email_address: Optional[str] = None
    
    # Events to notify / 通知事件
    notify_on_entry: bool = True    # 入场信号通知
    notify_on_exit: bool = True     # 出场信号通知
    notify_on_alert: bool = True    # 价格预警通知
    notify_daily_report: bool = False  # 日报通知
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if not self.symbols:
            raise ValueError("At least one symbol must be specified")
        if self.threshold_1 <= 0 or self.threshold_1 >= 1:
            raise ValueError("threshold_1 must be between 0 and 1")
        if self.threshold_2 <= self.threshold_1:
            raise ValueError("threshold_2 must be greater than threshold_1")
        if self.position_size_1 <= 0:
            raise ValueError("position_size_1 must be positive")
        return True


@dataclass
class RiskConfig:
    """
    Risk management configuration.
    风控配置
    """
    
    # Daily loss limit / 单日亏损限制
    max_daily_loss: float = 10000.0  # 单日最大亏损（元）
    
    # Drawdown limit / 回撤限制
    max_drawdown: float = 0.05  # 最大回撤比例 5%
    
    # Force close settings / 强平设置
    force_close_on_limit: bool = True  # 触发限制后强制平仓
    
    # Position limits / 仓位限制
    max_total_position: int = 4  # 总最大持仓手数
    
    def validate(self) -> bool:
        """Validate risk configuration values."""
        if self.max_daily_loss <= 0:
            raise ValueError("max_daily_loss must be positive")
        if self.max_drawdown <= 0 or self.max_drawdown >= 1:
            raise ValueError("max_drawdown must be between 0 and 1")
        return True


@dataclass 
class BacktestConfig:
    """
    Backtest configuration.
    回测配置
    """
    
    # Initial capital / 初始资金
    initial_capital: float = 500000.0
    
    # Commission settings / 手续费设置
    use_default_commission: bool = True  # 使用默认手续费
    
    # Slippage / 滑点
    slippage_points: float = 0.0  # 滑点点数
    
    # Data settings / 数据设置
    use_minute_data: bool = True  # 使用分钟数据
