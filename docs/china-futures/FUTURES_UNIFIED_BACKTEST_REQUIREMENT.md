# 通用期货分钟级回测框架 - 需求分析文档

> **文档状态**: 需求分析  
> **创建日期**: 2026-02-09  
> **关联功能**: 指标编辑器、期货回测、策略扩展

---

## 1. 背景与目标

### 1.1 背景

当前系统存在**两套独立的回测系统**：

| 系统 | 位置 | 特点 | 局限性 |
|------|------|------|--------|
| **通用回测服务** | `app/services/backtest.py` | 基于指标编辑器代码，支持日K/分钟K技术指标策略 | 只支持简单的 buy/sell 信号，无法处理跨日逻辑、VWAP等复杂计算 |
| **结算价差专用回测** | `app/strategies/settlement_arbitrage/backtest.py` | 专为该策略定制，支持分钟级数据、VWAP、跨日逻辑 | 每新增策略都需要独立开发回测引擎 |

### 1.2 问题

当前架构下，每新增一个分钟级期货策略需要：
1. ❌ 编写专用的 `backtest.py` 回测引擎
2. ❌ 编写专用的 API 路由
3. ❌ 可能还需要编写前端组件
4. ❌ 维护成本高，代码重复

### 1.3 目标

实现一个**通用期货分钟级回测框架**，达成以下目标：

| 目标 | 描述 |
|------|------|
| **无需修改前后端** | 新增策略只需在指标编辑器中编写Python代码 |
| **支持分钟级数据** | 执行环境提供分钟级K线数据访问能力 |
| **支持复杂策略逻辑** | 支持跨日信号、VWAP计算、时间段判断等 |
| **可配置化** | 策略参数通过代码中的特殊注释或配置实现动态化 |
| **向后兼容** | 现有的简单 buy/sell 策略仍然正常工作 |

---

## 2. 现状分析

### 2.1 现有指标编辑器执行环境

当前 `_execute_indicator` 方法提供的执行环境：

```python
# 可用变量
local_vars = {
    'df': df.copy(),           # 日K/分钟K DataFrame
    'open': df['open'],
    'high': df['high'],
    'low': df['low'],
    'close': df['close'],
    'volume': df['volume'],
    'np': np,
    'pd': pd,
    'backtest_params': {...},  # 杠杆、初始资金、手续费、交易方向
}

# 可用技术指标函数
SMA, EMA, RSI, MACD, BOLL, ATR, CROSSOVER, CROSSUNDER
```

**输出要求**：
- 简单模式: `df['buy']`, `df['sell']` 布尔列
- 四向模式: `df['open_long']`, `df['close_long']`, `df['open_short']`, `df['close_short']`

### 2.2 结算价差策略的特殊需求

分析 `SettlementStrategyBacktest` 的实现，识别出以下**超出通用回测能力**的需求：

| 需求 | 说明 | 当前执行环境是否支持 |
|------|------|---------------------|
| **分钟级数据访问** | 需要 14:30-15:00 的分钟K线 | ❌ 只有单一timeframe的df |
| **日内时间判断** | 判断 14:30 后价格是否下跌 | ❌ df中没有精确时间戳 |
| **VWAP计算** | 最后一小时成交量加权平均价 | ❌ 无内置VWAP函数 |
| **跨日信号** | 今天买入 → 明天开盘卖出 | ❌ 信号是逐行独立的 |
| **开盘价成交** | 以次日开盘价成交 | ❌ 默认以信号发出时收盘价成交 |
| **基准价格参考** | 以14:30价格为基准计算跌幅 | ❌ 只能用当前K线数据 |

---

## 3. 需求拆解

### 3.1 功能需求 (Functional Requirements)

#### FR-1: 扩展执行环境 - 分钟级数据访问

**描述**: 在指标编辑器执行环境中提供分钟级数据访问能力

**需求详情**:
- FR-1.1: 提供 `get_minute_data(symbol, date)` 函数，返回指定日期的分钟K线 DataFrame
- FR-1.2: 提供 `get_minute_data_range(symbol, start_date, end_date)` 函数，返回日期范围内所有分钟数据
- FR-1.3: 分钟数据 DataFrame 包含字段: `datetime`, `open`, `high`, `low`, `close`, `volume`
- FR-1.4: 自动处理数据缓存，避免重复请求

**输入/输出示例**:
```python
# 用户在指标编辑器中编写
minute_df = get_minute_data("IM0", "2025-06-15")
# 返回该日所有分钟K线
```

---

#### FR-2: 扩展执行环境 - 时间段数据筛选

**描述**: 提供便捷的时间段筛选函数

**需求详情**:
- FR-2.1: 提供 `filter_by_time(df, start_time, end_time)` 函数
- FR-2.2: 提供 `get_price_at_time(df, target_time)` 函数，获取指定时间点的价格

**输入/输出示例**:
```python
# 筛选 14:30-15:00 的数据
afternoon_df = filter_by_time(minute_df, "14:30", "15:00")

# 获取 14:30 的价格
price_1430 = get_price_at_time(minute_df, "14:30")
```

---

#### FR-3: 扩展执行环境 - VWAP计算

**描述**: 提供VWAP（成交量加权平均价）计算函数

**需求详情**:
- FR-3.1: 提供 `VWAP(df)` 函数，计算整个DataFrame的VWAP
- FR-3.2: 提供 `VWAP_PERIOD(df, start_time, end_time)` 函数，计算指定时间段的VWAP

**输入/输出示例**:
```python
# 计算最后一小时的VWAP
last_hour = filter_by_time(minute_df, "14:00", "15:00")
settlement_vwap = VWAP(last_hour)
```

---

#### FR-4: 扩展信号格式 - 支持跨日信号

**描述**: 扩展信号输出格式，支持"今天开仓、明天平仓"的跨日逻辑

**需求详情**:
- FR-4.1: 新增信号格式: `df['entry_signal']` (布尔，是否开仓)
- FR-4.2: 新增列: `df['exit_type']` (字符串，可选值: `'next_open'`, `'same_day'`, `'stop_loss'`, `'take_profit'`)
- FR-4.3: 新增列: `df['entry_price_type']` (字符串，可选值: `'close'`, `'open'`, `'vwap'`)
- FR-4.4: 回测引擎根据 `exit_type` 自动处理跨日平仓逻辑

**输入/输出示例**:
```python
# 用户在指标编辑器中编写
df['entry_signal'] = drop_pct <= -0.01  # 跌幅超过1%则开仓
df['exit_type'] = 'next_open'           # 次日开盘平仓
df['entry_price_type'] = 'close'        # 当日收盘价开仓
```

---

#### FR-5: 扩展执行环境 - 期货专用参数

**描述**: 在执行环境中提供期货交易专用参数

**需求详情**:
- FR-5.1: 提供 `get_contract_info(symbol)` 函数，返回合约乘数、手续费率等
- FR-5.2: 提供 `calculate_margin(symbol, price, quantity)` 函数，计算保证金
- FR-5.3: 提供 `calculate_fee(symbol, price, quantity, direction)` 函数，计算手续费

**输入/输出示例**:
```python
info = get_contract_info("IM0")
# 返回 {'multiplier': 200, 'margin_ratio': 0.12, 'fee_rate': 0.000023}
```

---

#### FR-6: 策略元数据声明

**描述**: 允许用户在代码中声明策略元数据，实现策略的自描述

**需求详情**:
- FR-6.1: 支持通过特殊注释或变量声明策略名称、描述、版本
- FR-6.2: 支持声明策略所需的数据类型 (`daily`, `minute`, `both`)
- FR-6.3: 支持声明策略参数 schema（用于前端动态表单）

**输入/输出示例**:
```python
# === Strategy Metadata ===
# @strategy_name: 结算价差套利策略
# @strategy_version: 1.0
# @data_requirement: minute
# @params:
#   threshold_1: {type: float, default: 0.01, label: "首仓阈值"}
#   threshold_2: {type: float, default: 0.02, label: "追加阈值"}
# === End Metadata ===

# 使用参数
threshold_1 = params.get('threshold_1', 0.01)
```

---

### 3.2 非功能需求 (Non-Functional Requirements)

#### NFR-1: 向后兼容性

- NFR-1.1: 现有的简单 buy/sell 策略无需修改即可正常运行
- NFR-1.2: 现有的回测API接口保持不变

#### NFR-2: 性能要求

- NFR-2.1: 分钟级数据回测支持至少1年的历史数据
- NFR-2.2: 单次回测执行时间不超过60秒（现有timeout限制）
- NFR-2.3: 分钟数据使用本地缓存，避免重复下载

#### NFR-3: 安全性

- NFR-3.1: 新增的函数不能引入安全漏洞
- NFR-3.2: 分钟数据获取限制在允许的品种范围内

---

## 4. 技术方案概要

### 4.1 架构设计

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              指标编辑器前端                                   │
│                    (无需修改，使用现有界面)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           现有回测 API 接口                                   │
│                    POST /api/backtest                                        │
│                    (无需修改)                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BacktestService._execute_indicator                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    扩展执行环境 (新增)                                   ││
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐           ││
│  │  │ get_minute_data │ │ filter_by_time  │ │ VWAP / VWAP_    │           ││
│  │  │                 │ │ get_price_at_   │ │ PERIOD          │           ││
│  │  │                 │ │ time            │ │                 │           ││
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘           ││
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐           ││
│  │  │get_contract_info│ │ calculate_fee   │ │ calculate_      │           ││
│  │  │                 │ │                 │ │ margin          │           ││
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      扩展交易模拟 (新增)                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    _simulate_trading_futures                            ││
│  │  - 识别 exit_type='next_open' → 次日开盘价平仓                          ││
│  │  - 识别 entry_price_type → 确定开仓价格                                 ││
│  │  - 使用合约乘数计算盈亏                                                 ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 改动范围

| 文件 | 改动类型 | 改动内容 |
|------|----------|----------|
| `app/services/backtest.py` | 修改 | 扩展 `_execute_indicator` 执行环境，新增期货辅助函数 |
| `app/services/backtest.py` | 新增 | 添加 `_simulate_trading_futures` 方法处理跨日逻辑 |
| `app/services/futures_indicator_helpers.py` | 新增 | 封装分钟数据获取、VWAP计算等辅助函数 |
| 前端 | **无需修改** | - |
| API路由 | **无需修改** | - |

### 4.3 用户使用示例

改造后，用户可以在**现有指标编辑器**中直接编写结算价差策略：

```python
# === Strategy Metadata ===
# @strategy_name: 结算价差套利策略
# @data_requirement: minute

# 策略参数
threshold_1 = 0.01  # 首仓阈值 1%
threshold_2 = 0.02  # 追加阈值 2%

# 初始化信号列
df['entry_signal'] = False
df['exit_type'] = 'next_open'
df['entry_level'] = 0

# 遍历每个交易日
for idx, row in df.iterrows():
    # 获取当日分钟数据
    trade_date = row['datetime'].date()
    minute_df = get_minute_data(symbol, str(trade_date))
    
    if minute_df is None or minute_df.empty:
        continue
    
    # 获取14:30价格作为基准
    price_1430 = get_price_at_time(minute_df, "14:30")
    if price_1430 is None:
        continue
    
    # 计算收盘时的跌幅
    close_price = row['close']
    drop_pct = (close_price - price_1430) / price_1430
    
    # 判断是否触发入场信号
    if drop_pct <= -threshold_1:
        df.at[idx, 'entry_signal'] = True
        df.at[idx, 'entry_level'] = 2 if drop_pct <= -threshold_2 else 1

# 转换为标准格式
df['buy'] = df['entry_signal']
df['sell'] = False  # 由 exit_type='next_open' 控制平仓
```

---

## 5. 需求优先级与里程碑

### 5.1 优先级划分

| 优先级 | 需求编号 | 描述 | 理由 |
|--------|----------|------|------|
| P0 (必须) | FR-1 | 分钟级数据访问 | 核心功能，无此功能无法实现分钟级策略 |
| P0 (必须) | FR-2 | 时间段筛选函数 | 高频使用，策略开发基础工具 |
| P0 (必须) | FR-4 | 跨日信号支持 | 结算价差策略核心需求 |
| P1 (重要) | FR-3 | VWAP计算 | 结算价差策略需要，通用性高 |
| P1 (重要) | FR-5 | 期货专用参数 | 提升策略开发体验 |
| P2 (增强) | FR-6 | 策略元数据声明 | 锦上添花，便于策略管理 |

### 5.2 实施里程碑

| 里程碑 | 内容 | 预估工时 |
|--------|------|----------|
| **M1: 核心功能** | FR-1 + FR-2 + FR-4 | 4-6小时 |
| **M2: 增强功能** | FR-3 + FR-5 | 2-3小时 |
| **M3: 体验优化** | FR-6 + 文档示例 | 2小时 |

---

## 6. 验收标准

### 6.1 功能验收

- [ ] 能够在指标编辑器中获取分钟级数据
- [ ] 能够筛选指定时间段的数据
- [ ] 能够计算VWAP
- [ ] 能够实现"今天买入、明天开盘卖出"的跨日逻辑
- [ ] 现有简单策略不受影响

### 6.2 示例策略验收

使用新框架重新实现结算价差策略，验证：
- [ ] 回测结果与专用回测引擎结果一致（误差<1%）
- [ ] 无需修改前后端代码

---

## 7. 附录

### 7.1 相关文档

- [结算价差套利策略完整需求](./SETTLEMENT_ARBITRAGE_FULL_REQUIREMENT.md)
- [期货前端需求文档](./FUTURES_FRONTEND_REQUIREMENTS.md)
- [策略开发指南](../strategy-dev/STRATEGY_DEV_GUIDE_CN.md)

### 7.2 参考代码

- 现有回测服务: `backend_api_python/app/services/backtest.py`
- 结算价差回测引擎: `backend_api_python/app/strategies/settlement_arbitrage/backtest.py`
- VWAP计算器: `backend_api_python/app/strategies/settlement_arbitrage/vwap_calculator.py`
