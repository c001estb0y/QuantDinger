# MVP 并行开发任务拆分文档

> **文档版本**: v1.0  
> **创建时间**: 2026-02-04  
> **目的**: 将MVP开发任务拆分为可并行执行的独立模块，定义接口标准

---

## 📋 任务总览

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       可并行开发的4个独立模块                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   👤 开发者A                          👤 开发者B                         │
│   ┌─────────────────────┐            ┌─────────────────────┐            │
│   │ 模块1: 数据源       │            │ 模块2: 期货计算器   │            │
│   │ CNFuturesDataSource │            │ FuturesCalculator   │            │
│   │ 预计: 5小时         │            │ 预计: 5小时         │            │
│   └─────────────────────┘            └─────────────────────┘            │
│                                                                          │
│   👤 开发者C                          👤 开发者D                         │
│   ┌─────────────────────┐            ┌─────────────────────┐            │
│   │ 模块3: 通知模板     │            │ 模块4: 策略集成     │            │
│   │ FuturesNotification │            │ StrategyIntegration │            │
│   │ 预计: 3小时         │            │ 预计: 4小时         │            │
│   └─────────────────────┘            └─────────────────────┘            │
│                                                                          │
│   🎯 所有模块完成后 → 集成测试（约2小时）                               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🔗 模块依赖关系

```
模块1 (数据源) ─────────────────┐
                                ▼
模块2 (计算器) ─── 无依赖 ───► [集成测试]
                                ▲
模块3 (通知)   ─────────────────┤
                                │
模块4 (策略)   ─────────────────┘

✅ 模块1、2、3、4 之间无依赖，可完全并行开发
✅ 各模块通过约定的接口标准进行集成
```

---

# 📦 模块1: 中国期货数据源

## 基本信息

| 项目 | 内容 |
|------|------|
| **负责人** | 开发者A |
| **文件位置** | `/backend_api_python/app/data_sources/cn_futures.py` |
| **预计工时** | 5小时 |
| **依赖项** | akshare库 |

## 接口标准

### 1.1 类定义 (继承 BaseDataSource)

```python
# 文件: backend_api_python/app/data_sources/cn_futures.py

from typing import Dict, List, Any, Optional
from app.data_sources.base import BaseDataSource

class CNFuturesDataSource(BaseDataSource):
    """
    中国股指期货数据源
    支持 IC(中证500)、IM(中证1000)、IF(沪深300)、IH(上证50) 主力合约
    """
    
    name: str = "cn_futures"
    
    # 必须实现的方法
    def get_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取K线数据
        
        Args:
            symbol: 合约代码 (IC0, IM0, IF0, IH0 或 IC2503等)
            timeframe: 时间周期 (1m, 5m, 15m, 30m, 1H)
            limit: 数据条数 (最大1000)
            before_time: Unix时间戳（秒），获取此时间之前的数据
            
        Returns:
            K线数据列表，格式:
            [
                {
                    "time": 1704067200,      # Unix时间戳（秒）
                    "open": 5500.0,          # 开盘价
                    "high": 5520.0,          # 最高价
                    "low": 5480.0,           # 最低价
                    "close": 5510.0,         # 收盘价
                    "volume": 12345.0        # 成交量
                },
                ...
            ]
        """
        pass
    
    # 可选实现：获取实时行情
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        获取最新行情
        
        Args:
            symbol: 合约代码
            
        Returns:
            {
                "last": 5510.0,              # 最新价
                "bid": 5509.0,               # 买一价
                "ask": 5511.0,               # 卖一价
                "volume": 123456,            # 当日成交量
                "timestamp": 1704067200      # 时间戳
            }
        """
        pass
```

### 1.2 辅助方法接口

```python
class CNFuturesDataSource(BaseDataSource):
    
    # ... 上面的方法 ...
    
    def get_main_contract_code(self, product: str) -> str:
        """
        获取当前主力合约代码
        
        Args:
            product: 品种代码 (IC, IM, IF, IH)
            
        Returns:
            当前主力合约代码，如 "IC2503"
        """
        pass
    
    def get_contract_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取合约信息
        
        Args:
            symbol: 合约代码
            
        Returns:
            {
                "symbol": "IC2503",
                "product": "IC",
                "name": "中证500股指期货2503",
                "multiplier": 200,           # 合约乘数
                "margin_ratio": 0.12,        # 保证金比例
                "tick_size": 0.2,            # 最小变动价位
                "is_main": True              # 是否为主力合约
            }
        """
        pass
```

### 1.3 支持的品种和周期

| 品种代码 | 合约名称 | 主力合约 |
|---------|---------|---------|
| IC | 中证500股指期货 | IC0 |
| IM | 中证1000股指期货 | IM0 |
| IF | 沪深300股指期货 | IF0 |
| IH | 上证50股指期货 | IH0 |

| timeframe | 说明 |
|-----------|------|
| 1m | 1分钟 |
| 5m | 5分钟 |
| 15m | 15分钟 |
| 30m | 30分钟 |
| 1H | 1小时 |

### 1.4 工厂集成方法

完成后需要在 `factory.py` 中注册：

```python
# 文件: backend_api_python/app/data_sources/factory.py
# 在 _create_source 方法中添加：

elif market == 'CNFutures':
    from app.data_sources.cn_futures import CNFuturesDataSource
    return CNFuturesDataSource()
```

### 1.5 测试用例（验收标准）

```python
# 测试代码
def test_cn_futures_data_source():
    from app.data_sources.cn_futures import CNFuturesDataSource
    
    ds = CNFuturesDataSource()
    
    # 测试1: 获取IC主力合约1分钟K线
    klines = ds.get_kline(symbol="IC0", timeframe="1m", limit=100)
    assert len(klines) > 0
    assert all(k['time'] and k['open'] and k['close'] for k in klines)
    
    # 测试2: 获取主力合约代码
    main_code = ds.get_main_contract_code("IC")
    assert main_code.startswith("IC")
    
    # 测试3: 获取合约信息
    info = ds.get_contract_info("IC0")
    assert info['multiplier'] == 200
    
    print("✅ 所有测试通过")
```

---

# 📦 模块2: 期货计算器

## 基本信息

| 项目 | 内容 |
|------|------|
| **负责人** | 开发者B |
| **文件位置** | `/backend_api_python/app/services/futures_calculator.py` |
| **预计工时** | 5小时 |
| **依赖项** | 无外部依赖 |

## 接口标准

### 2.1 保证金计算器

```python
# 文件: backend_api_python/app/services/futures_calculator.py

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

@dataclass
class MarginInfo:
    """保证金信息"""
    contract_value: float    # 合约价值
    margin_ratio: float      # 保证金比例
    margin_required: float   # 所需保证金
    multiplier: int          # 合约乘数


class FuturesMarginCalculator:
    """
    期货保证金计算器
    """
    
    # 保证金比例配置
    MARGIN_RATIOS: Dict[str, float] = {
        'IC': 0.12,  # 中证500，12%
        'IM': 0.12,  # 中证1000，12%
        'IF': 0.10,  # 沪深300，10%
        'IH': 0.10,  # 上证50，10%
    }
    
    # 合约乘数配置
    MULTIPLIERS: Dict[str, int] = {
        'IC': 200,  # 每点200元
        'IM': 200,  # 每点200元
        'IF': 300,  # 每点300元
        'IH': 300,  # 每点300元
    }
    
    def calculate(
        self,
        symbol: str,
        price: float,
        quantity: int = 1
    ) -> MarginInfo:
        """
        计算保证金
        
        Args:
            symbol: 合约代码 (IC0, IM2503等)
            price: 当前价格
            quantity: 手数
            
        Returns:
            MarginInfo 对象
        """
        pass
    
    def get_margin_ratio(self, symbol: str) -> float:
        """获取保证金比例"""
        pass
    
    def get_multiplier(self, symbol: str) -> int:
        """获取合约乘数"""
        pass
```

### 2.2 手续费计算器

```python
@dataclass
class FeeInfo:
    """手续费信息"""
    contract_value: float    # 合约价值
    fee_rate: float          # 费率
    fee_amount: float        # 手续费金额
    is_close_today: bool     # 是否平今


class FuturesFeeCalculator:
    """
    期货手续费计算器
    """
    
    # 手续费率配置（按成交金额）
    FEE_RATES: Dict[str, Dict[str, float]] = {
        'IC': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
        'IM': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
        'IF': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
        'IH': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
    }
    
    def calculate(
        self,
        symbol: str,
        price: float,
        quantity: int = 1,
        is_open: bool = True,
        is_close_today: bool = False
    ) -> FeeInfo:
        """
        计算手续费
        
        Args:
            symbol: 合约代码
            price: 成交价格
            quantity: 手数
            is_open: 是否为开仓
            is_close_today: 是否为平今（仅当is_open=False时有效）
            
        Returns:
            FeeInfo 对象
        """
        pass
    
    def calculate_round_trip(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: int = 1,
        is_same_day: bool = True
    ) -> Dict[str, FeeInfo]:
        """
        计算往返手续费（开仓+平仓）
        
        Returns:
            {"open": FeeInfo, "close": FeeInfo, "total": float}
        """
        pass
```

### 2.3 结算价计算器

```python
from typing import List
import pandas as pd

class SettlementPriceCalculator:
    """
    结算价计算器
    股指期货结算价 = 最后一小时VWAP
    """
    
    def calculate_vwap(
        self,
        minute_bars: List[Dict[str, Any]],
        start_time: str = "14:00:00",
        end_time: str = "15:00:00"
    ) -> float:
        """
        计算VWAP（成交量加权平均价）
        
        Args:
            minute_bars: 分钟K线列表
                [{"time": int, "close": float, "volume": float}, ...]
            start_time: 开始时间 (HH:MM:SS)
            end_time: 结束时间 (HH:MM:SS)
            
        Returns:
            VWAP值
        """
        pass
    
    def estimate_settlement_price(
        self,
        minute_bars: List[Dict[str, Any]]
    ) -> float:
        """
        估算结算价
        使用最后一小时的分钟K线计算VWAP
        
        Returns:
            估算的结算价
        """
        pass
```

### 2.4 涨跌停检测器

```python
from enum import Enum

class PriceLimitStatus(Enum):
    NORMAL = "normal"
    LIMIT_UP = "limit_up"
    LIMIT_DOWN = "limit_down"


@dataclass
class PriceLimitInfo:
    """涨跌停信息"""
    status: PriceLimitStatus
    upper_limit: float       # 涨停价
    lower_limit: float       # 跌停价
    current_price: float     # 当前价
    distance_to_limit: float # 距离涨跌停的百分比


class PriceLimitChecker:
    """
    涨跌停检测器
    股指期货涨跌停板：±10%（基于前结算价）
    """
    
    LIMIT_RATIO: float = 0.10  # 10%涨跌停
    
    def check(
        self,
        symbol: str,
        current_price: float,
        prev_settlement: float
    ) -> PriceLimitInfo:
        """
        检查涨跌停状态
        
        Args:
            symbol: 合约代码
            current_price: 当前价格
            prev_settlement: 前结算价
            
        Returns:
            PriceLimitInfo 对象
        """
        pass
    
    def calculate_limits(
        self,
        prev_settlement: float
    ) -> Tuple[float, float]:
        """
        计算涨跌停价格
        
        Returns:
            (涨停价, 跌停价)
        """
        pass
```

### 2.5 统一计算器门面类

```python
class FuturesCalculator:
    """
    期货计算器统一门面类
    整合所有计算器功能
    """
    
    def __init__(self):
        self.margin = FuturesMarginCalculator()
        self.fee = FuturesFeeCalculator()
        self.settlement = SettlementPriceCalculator()
        self.price_limit = PriceLimitChecker()
    
    def calculate_trade_cost(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: int = 1,
        is_same_day: bool = True
    ) -> Dict[str, Any]:
        """
        计算完整交易成本
        
        Returns:
            {
                "margin_required": float,    # 所需保证金
                "fee_open": float,           # 开仓手续费
                "fee_close": float,          # 平仓手续费
                "fee_total": float,          # 总手续费
                "gross_pnl": float,          # 毛盈亏
                "net_pnl": float,            # 净盈亏
                "pnl_points": float,         # 盈亏点数
            }
        """
        pass
```

### 2.6 测试用例（验收标准）

```python
def test_futures_calculator():
    from app.services.futures_calculator import FuturesCalculator
    
    calc = FuturesCalculator()
    
    # 测试1: 保证金计算
    margin = calc.margin.calculate("IC0", price=5500, quantity=1)
    assert margin.margin_required == 5500 * 200 * 0.12  # 132000
    
    # 测试2: 手续费计算
    fee = calc.fee.calculate("IC0", price=5500, quantity=1, is_open=True)
    assert fee.fee_amount > 0
    
    # 测试3: 涨跌停检测
    limit = calc.price_limit.check("IC0", current_price=6000, prev_settlement=5500)
    assert limit.status.value in ["normal", "limit_up", "limit_down"]
    
    # 测试4: 完整交易成本
    cost = calc.calculate_trade_cost("IC0", 5500, 5550, quantity=1)
    assert "net_pnl" in cost
    
    print("✅ 所有测试通过")
```

---

# 📦 模块3: 期货通知模板

## 基本信息

| 项目 | 内容 |
|------|------|
| **负责人** | 开发者C |
| **文件位置** | `/backend_api_python/app/services/futures_notification.py` |
| **预计工时** | 3小时 |
| **依赖项** | 现有 SignalNotifier |

## 接口标准

### 3.1 通知数据类型

```python
# 文件: backend_api_python/app/services/futures_notification.py

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class FuturesSignalType(Enum):
    """期货信号类型"""
    BUY = "buy"
    SELL = "sell"
    PRICE_ALERT = "price_alert"
    PNL_REPORT = "pnl_report"


@dataclass
class FuturesSignalData:
    """期货信号数据"""
    signal_type: FuturesSignalType
    symbol: str              # 合约代码，如 IC0
    current_price: float     # 当前价
    base_price: float        # 基准价（如14:30价格）
    drop_pct: float          # 跌幅百分比
    timestamp: datetime      # 时间戳
    
    # 可选字段
    entry_price: Optional[float] = None   # 买入价（用于卖出信号）
    profit: Optional[float] = None        # 收益金额
    profit_pct: Optional[float] = None    # 收益百分比
    monthly_pnl: Optional[float] = None   # 月度累计盈亏
```

### 3.2 通知模板类

```python
class FuturesNotificationTemplates:
    """
    期货策略通知模板
    """
    
    @staticmethod
    def render_buy_signal(data: FuturesSignalData) -> Dict[str, str]:
        """
        渲染买入信号通知
        
        Returns:
            {
                "title": "【买入信号】...",
                "plain": "纯文本内容",
                "html": "HTML格式内容",
                "telegram": "Telegram格式内容"
            }
        """
        pass
    
    @staticmethod
    def render_sell_signal(data: FuturesSignalData) -> Dict[str, str]:
        """
        渲染卖出信号通知
        """
        pass
    
    @staticmethod
    def render_price_alert(data: FuturesSignalData) -> Dict[str, str]:
        """
        渲染价格预警通知
        """
        pass
    
    @staticmethod
    def render_pnl_report(data: FuturesSignalData) -> Dict[str, str]:
        """
        渲染盈亏报告通知
        """
        pass
```

### 3.3 通知服务类

```python
from app.services.signal_notifier import SignalNotifier

class FuturesNotificationService:
    """
    期货策略通知服务
    封装 SignalNotifier，提供期货策略专用接口
    """
    
    def __init__(self):
        self.notifier = SignalNotifier()
        self.templates = FuturesNotificationTemplates()
    
    def send_buy_signal(
        self,
        strategy_id: int,
        strategy_name: str,
        data: FuturesSignalData,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送买入信号通知
        
        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            data: 信号数据
            notification_config: 通知配置（channels, targets等）
            
        Returns:
            各渠道发送结果
            {"telegram": {"ok": True}, "email": {"ok": True}, ...}
        """
        pass
    
    def send_sell_signal(
        self,
        strategy_id: int,
        strategy_name: str,
        data: FuturesSignalData,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送卖出信号通知"""
        pass
    
    def send_price_alert(
        self,
        strategy_id: int,
        strategy_name: str,
        data: FuturesSignalData,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送价格预警通知"""
        pass
    
    def send_pnl_report(
        self,
        strategy_id: int,
        strategy_name: str,
        data: FuturesSignalData,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送盈亏报告通知"""
        pass
```

### 3.4 通知模板内容

```python
# 买入信号模板
BUY_SIGNAL_TEMPLATE = """
🚀 【买入信号】股指期货结算价套利

📊 合约: {symbol} (主力)
📉 当前价: {current_price}
📌 14:30价: {base_price}
📉 跌幅: {drop_pct:.2f}%
⏰ 时间: {time}

💡 建议: 买入1手，持有至次日开盘
"""

# 卖出信号模板
SELL_SIGNAL_TEMPLATE = """
📤 【卖出信号】股指期货结算价套利

📊 合约: {symbol} (主力)
💰 开盘价: {current_price}
📈 买入价: {entry_price}
📊 收益: {profit:.2f}元 ({profit_pct:.2f}%)
⏰ 时间: {time}

💡 建议: 开盘卖出平仓
"""

# 价格预警模板
PRICE_ALERT_TEMPLATE = """
⚠️ 【价格预警】接近买入阈值

📊 合约: {symbol} (主力)
📉 当前跌幅: {drop_pct:.2f}%
🎯 触发阈值: 1.00%
⏰ 时间: {time}

💡 请关注: 即将触发买入信号
"""

# 盈亏报告模板
PNL_REPORT_TEMPLATE = """
📊 【交易报告】股指期货结算价套利

📋 合约: {symbol} (主力)
💰 买入价: {entry_price}
💰 卖出价: {current_price}
📈 收益: {profit:.2f}元 ({profit_pct:.2f}%)
⏰ 持仓时间: 隔夜

📊 本月累计: {monthly_pnl:.2f}元
"""
```

### 3.5 测试用例（验收标准）

```python
def test_futures_notification():
    from app.services.futures_notification import (
        FuturesNotificationService,
        FuturesSignalData,
        FuturesSignalType
    )
    from datetime import datetime
    
    service = FuturesNotificationService()
    
    # 测试1: 渲染买入信号
    buy_data = FuturesSignalData(
        signal_type=FuturesSignalType.BUY,
        symbol="IC0",
        current_price=5450,
        base_price=5500,
        drop_pct=0.91,
        timestamp=datetime.now()
    )
    rendered = service.templates.render_buy_signal(buy_data)
    assert "title" in rendered
    assert "5450" in rendered["plain"]
    
    # 测试2: 渲染卖出信号
    sell_data = FuturesSignalData(
        signal_type=FuturesSignalType.SELL,
        symbol="IC0",
        current_price=5520,
        base_price=5500,
        drop_pct=-0.36,
        timestamp=datetime.now(),
        entry_price=5450,
        profit=14000,
        profit_pct=0.64
    )
    rendered = service.templates.render_sell_signal(sell_data)
    assert "14000" in rendered["plain"]
    
    print("✅ 所有测试通过")
```

---

# 📦 模块4: 策略集成层

## 基本信息

| 项目 | 内容 |
|------|------|
| **负责人** | 开发者D |
| **文件位置** | `/backend_api_python/app/services/futures_strategy_executor.py` |
| **预计工时** | 4小时 |
| **依赖项** | 模块1、2、3（通过接口调用） |

## 接口标准

### 4.1 策略执行器

```python
# 文件: backend_api_python/app/services/futures_strategy_executor.py

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# 导入其他模块（开发时可先mock）
# from app.data_sources.cn_futures import CNFuturesDataSource
# from app.services.futures_calculator import FuturesCalculator
# from app.services.futures_notification import FuturesNotificationService


class StrategyStatus(Enum):
    """策略状态"""
    IDLE = "idle"                    # 空闲，等待信号
    MONITORING = "monitoring"        # 监控中（14:30-15:00）
    POSITION_OPEN = "position_open"  # 持仓中
    SIGNAL_TRIGGERED = "triggered"   # 信号已触发


@dataclass
class StrategyState:
    """策略状态数据"""
    status: StrategyStatus
    symbol: str
    base_price: Optional[float] = None      # 14:30基准价
    entry_price: Optional[float] = None     # 买入价
    entry_time: Optional[datetime] = None   # 买入时间
    current_price: Optional[float] = None   # 当前价
    drop_pct: Optional[float] = None        # 跌幅
    position_quantity: int = 0              # 持仓数量


class FuturesStrategyExecutor:
    """
    期货策略执行器
    实现结算价差套利策略的核心逻辑
    """
    
    # 策略参数（可配置）
    DEFAULT_CONFIG = {
        "symbols": ["IC0", "IM0"],          # 监控的合约
        "drop_threshold_1": 0.01,           # 第一次买入阈值 1%
        "drop_threshold_2": 0.02,           # 加仓阈值 2%
        "monitoring_start": "14:30:00",     # 监控开始时间
        "monitoring_end": "14:57:00",       # 监控结束时间（15:00前3分钟停止）
        "max_position": 2,                  # 最大持仓手数
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.states: Dict[str, StrategyState] = {}  # 每个合约的状态
        
        # 依赖的其他模块（开发时先用None，集成时注入）
        self.data_source = None  # CNFuturesDataSource
        self.calculator = None   # FuturesCalculator
        self.notifier = None     # FuturesNotificationService
    
    def initialize(
        self,
        data_source,      # CNFuturesDataSource
        calculator,       # FuturesCalculator
        notifier          # FuturesNotificationService
    ):
        """
        初始化依赖模块
        集成测试时调用
        """
        self.data_source = data_source
        self.calculator = calculator
        self.notifier = notifier
    
    def check_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        检查信号
        
        Args:
            symbol: 合约代码
            
        Returns:
            如果有信号返回:
            {
                "signal_type": "buy" | "sell",
                "symbol": str,
                "price": float,
                "drop_pct": float,
                "reason": str
            }
            无信号返回 None
        """
        pass
    
    def execute_signal(
        self,
        signal: Dict[str, Any],
        strategy_id: int,
        strategy_name: str,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行信号
        
        Args:
            signal: 信号数据
            strategy_id: 策略ID
            strategy_name: 策略名称
            notification_config: 通知配置
            
        Returns:
            执行结果
            {
                "success": bool,
                "action": "buy" | "sell",
                "price": float,
                "quantity": int,
                "notification_results": {...}
            }
        """
        pass
    
    def run_tick(
        self,
        strategy_id: int,
        strategy_name: str,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        执行一个tick（策略主循环调用）
        
        Returns:
            本次tick产生的信号和执行结果列表
        """
        pass
    
    def get_state(self, symbol: str) -> StrategyState:
        """获取指定合约的策略状态"""
        pass
    
    def reset(self, symbol: Optional[str] = None):
        """
        重置策略状态
        
        Args:
            symbol: 指定合约，None则重置所有
        """
        pass
```

### 4.2 辅助方法

```python
class FuturesStrategyExecutor:
    
    # ... 上面的方法 ...
    
    def _is_monitoring_time(self) -> bool:
        """
        检查当前是否在监控时间段内
        
        Returns:
            是否在 14:30-14:57
        """
        pass
    
    def _is_market_open(self) -> bool:
        """
        检查市场是否开盘
        
        Returns:
            是否在交易时间
        """
        pass
    
    def _calculate_drop_pct(
        self,
        current_price: float,
        base_price: float
    ) -> float:
        """
        计算跌幅百分比
        
        Returns:
            跌幅，负数表示下跌
        """
        return (current_price - base_price) / base_price
    
    def _should_send_alert(
        self,
        drop_pct: float,
        threshold: float = 0.008  # 0.8%时预警
    ) -> bool:
        """
        判断是否应该发送预警
        """
        pass
```

### 4.3 测试用例（验收标准）

```python
def test_futures_strategy_executor():
    from app.services.futures_strategy_executor import (
        FuturesStrategyExecutor,
        StrategyStatus
    )
    
    executor = FuturesStrategyExecutor()
    
    # 测试1: 初始状态
    state = executor.get_state("IC0")
    assert state.status == StrategyStatus.IDLE
    
    # 测试2: 跌幅计算
    drop = executor._calculate_drop_pct(5445, 5500)
    assert abs(drop - (-0.01)) < 0.001  # 约-1%
    
    # 测试3: 模拟信号检测（需要mock数据源）
    # executor.initialize(mock_data_source, mock_calculator, mock_notifier)
    # signal = executor.check_signal("IC0")
    
    print("✅ 所有测试通过")
```

---

# 🔄 集成测试

## 集成后完整流程

```python
# 文件: tests/test_futures_integration.py

def test_full_integration():
    """
    集成测试：验证所有模块协同工作
    """
    # 1. 初始化各模块
    from app.data_sources.cn_futures import CNFuturesDataSource
    from app.services.futures_calculator import FuturesCalculator
    from app.services.futures_notification import FuturesNotificationService
    from app.services.futures_strategy_executor import FuturesStrategyExecutor
    
    data_source = CNFuturesDataSource()
    calculator = FuturesCalculator()
    notifier = FuturesNotificationService()
    
    executor = FuturesStrategyExecutor()
    executor.initialize(data_source, calculator, notifier)
    
    # 2. 测试数据获取
    klines = data_source.get_kline("IC0", "1m", 100)
    assert len(klines) > 0
    
    # 3. 测试计算器
    cost = calculator.calculate_trade_cost("IC0", 5500, 5550)
    assert cost["net_pnl"] > 0
    
    # 4. 测试信号检测
    signal = executor.check_signal("IC0")
    # 根据实际数据可能有或没有信号
    
    print("✅ 集成测试通过")
```

---

# 📋 开发者任务Checklist

## 开发者A - 数据源模块

- [ ] 创建 `cn_futures.py` 文件
- [ ] 实现 `CNFuturesDataSource` 类
- [ ] 实现 `get_kline()` 方法
- [ ] 实现 `get_ticker()` 方法
- [ ] 实现 `get_main_contract_code()` 方法
- [ ] 实现 `get_contract_info()` 方法
- [ ] 在 `factory.py` 中注册
- [ ] 编写单元测试
- [ ] 测试通过后通知集成

## 开发者B - 期货计算器模块

- [ ] 创建 `futures_calculator.py` 文件
- [ ] 实现 `FuturesMarginCalculator` 类
- [ ] 实现 `FuturesFeeCalculator` 类
- [ ] 实现 `SettlementPriceCalculator` 类
- [ ] 实现 `PriceLimitChecker` 类
- [ ] 实现 `FuturesCalculator` 门面类
- [ ] 编写单元测试
- [ ] 测试通过后通知集成

## 开发者C - 通知模板模块

- [ ] 创建 `futures_notification.py` 文件
- [ ] 定义 `FuturesSignalData` 数据类
- [ ] 实现 `FuturesNotificationTemplates` 类
- [ ] 实现 `FuturesNotificationService` 类
- [ ] 实现4种通知模板
- [ ] 编写单元测试
- [ ] 测试通过后通知集成

## 开发者D - 策略集成层

- [ ] 创建 `futures_strategy_executor.py` 文件
- [ ] 定义 `StrategyState` 数据类
- [ ] 实现 `FuturesStrategyExecutor` 类
- [ ] 实现信号检测逻辑
- [ ] 实现信号执行逻辑
- [ ] 编写单元测试（使用Mock）
- [ ] 测试通过后通知集成

---

# ⏰ 时间安排

| 阶段 | 时间 | 内容 |
|------|------|------|
| **并行开发** | Day 1-2 | 4个模块同时开发 |
| **单元测试** | Day 2-3 | 各模块独立测试 |
| **集成测试** | Day 3 | 组装所有模块，端到端测试 |
| **Bug修复** | Day 4 | 修复集成问题 |
| **交付** | Day 5 | MVP完成 |

---

# 📞 沟通约定

1. **接口变更**：如需修改接口，必须同步通知其他开发者
2. **每日同步**：每天下班前同步进度
3. **阻塞问题**：遇到阻塞立即沟通，不要等待
4. **代码规范**：遵循项目现有代码风格

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-02-04 | 初始版本，定义4个并行模块和接口标准 |
