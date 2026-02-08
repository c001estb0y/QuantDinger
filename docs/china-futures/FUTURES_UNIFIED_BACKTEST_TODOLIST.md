# 通用期货分钟级回测框架 - 实施 TODO 清单

> **关联需求**: [FUTURES_UNIFIED_BACKTEST_REQUIREMENT.md](./FUTURES_UNIFIED_BACKTEST_REQUIREMENT.md)  
> **创建日期**: 2026-02-09  
> **状态**: ✅ M1 已完成

---

## M1: 核心功能 (P0) ✅ 已完成

### Task 1: 创建辅助函数模块 `futures_indicator_helpers.py` ✅

**文件**: `backend_api_python/app/services/futures_indicator_helpers.py`

- [x] **T1.1** 创建 `FuturesIndicatorHelpers` 类，封装所有辅助函数
- [x] **T1.2** 实现 `get_minute_data(symbol, date)` - 获取指定日期分钟K线 (FR-1.1)
- [x] **T1.3** 实现 `get_minute_data_range(symbol, start_date, end_date)` - 获取日期范围分钟数据 (FR-1.2)
- [x] **T1.4** 实现分钟数据内存缓存机制，避免重复请求 (FR-1.4)
- [x] **T1.5** 实现 `filter_by_time(df, start_time, end_time)` - 时间段筛选 (FR-2.1)
- [x] **T1.6** 实现 `get_price_at_time(df, target_time)` - 获取指定时间点价格 (FR-2.2)
- [x] **T1.7** 实现 `VWAP(df)` - 计算VWAP (FR-3.1)
- [x] **T1.8** 实现 `VWAP_PERIOD(df, start_time, end_time)` - 计算指定时间段VWAP (FR-3.2)
- [x] **T1.9** 实现 `get_contract_info(symbol)` - 获取合约信息 (FR-5.1)
- [x] **T1.10** 实现 `calculate_margin(symbol, price, quantity)` - 计算保证金 (FR-5.2)
- [x] **T1.11** 实现 `calculate_fee(symbol, price, quantity, direction)` - 计算手续费 (FR-5.3)

### Task 2: 扩展 `_execute_indicator` 执行环境 ✅

**文件**: `backend_api_python/app/services/backtest.py`

- [x] **T2.1** 在 `_execute_indicator` 中检测 market 类型，为 CNFutures 注入辅助函数
- [x] **T2.2** 注入 `get_minute_data`、`get_minute_data_range` 到执行环境
- [x] **T2.3** 注入 `filter_by_time`、`get_price_at_time` 到执行环境
- [x] **T2.4** 注入 `VWAP`、`VWAP_PERIOD` 到执行环境
- [x] **T2.5** 注入 `get_contract_info`、`calculate_margin`、`calculate_fee` 到执行环境
- [x] **T2.6** 注入 `symbol` 变量到执行环境，使用户代码可直接引用当前品种
- [x] **T2.7** 实现策略元数据解析 (FR-6) - 解析 `# @data_requirement` 等注释

### Task 3: 扩展交易模拟 - 支持跨日信号 (FR-4) ✅

**文件**: `backend_api_python/app/services/backtest.py`

- [x] **T3.1** 在 `_simulate_trading` 中检测 `entry_signal` + `exit_type` 信号格式
- [x] **T3.2** 实现 `exit_type='next_open'` 逻辑：当日收盘开仓 → 次日开盘平仓
- [x] **T3.3** 实现 `entry_price_type` 支持：`'close'`、`'open'`、`'vwap'`
- [x] **T3.4** 确保向后兼容：原有 buy/sell 和 4-way 信号格式不受影响 (NFR-1)

---

## M2: 增强功能 (P1)

> M1 完成后再开始

- [ ] **T4.1** 为 `get_minute_data` 添加数据持久化缓存（本地文件 / SQLite）
- [ ] **T4.2** 优化 `VWAP_PERIOD` 支持 typical price 模式
- [ ] **T4.3** 添加 `get_trading_calendar()` 到执行环境

---

## M3: 体验优化 (P2)

> M2 完成后再开始

- [ ] **T5.1** 完善策略元数据解析，支持参数 schema 声明
- [ ] **T5.2** 创建示例策略模板（结算价差套利策略脚本示例）

---

## 技术方案摘要

### 改动文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/services/futures_indicator_helpers.py` | **新建** ✅ | 期货指标辅助函数模块 |
| `app/services/backtest.py` | **修改** ✅ | 扩展 `_execute_indicator` 和 `_simulate_trading` |

### 不改动的部分

- ❌ 前端代码 - 无需修改
- ❌ API 路由 - 无需修改
- ❌ 数据源 `cn_futures.py` - 直接复用现有的 `get_minute_bars` 方法
