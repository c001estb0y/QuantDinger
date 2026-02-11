# TODO List

## 待处理问题

### 1. 分钟级历史数据回测支持

**问题描述**：当前 akshare 的 `futures_zh_minute_sina` 接口只能获取近期有限的分钟数据，无法支持完整的分钟级历史数据回测。

**2026-02-12 回测失败问题分析**：

从日志发现两个关键错误：
1. `akshare fetch error: Length mismatch: Expected axis has 0 elements, new values have 8 elements`
   - akshare 获取分钟数据时返回格式异常
   
2. `KeyError: 'datetime'` (策略代码 line 9)
   - 策略代码尝试访问 `row['datetime']`，但 df 中的 datetime 可能不在列中

**已修复**：
- 修改 `backtest.py` 第1147行：`FuturesIndicatorHelpers` 初始化时传入 `df_copy`（包含datetime列）而不是原始 `df`
- 在 `_synthesize_minute_from_daily` 中增加了防御性检查和调试日志

**待测试**：重启后端服务后重新运行回测

---

**当前已实现的Fallback机制**：
- 系统已在 `futures_indicator_helpers.py` 中实现了 `_synthesize_minute_from_daily` 方法
- 当真实分钟数据不可用时，会从日线OHLCV数据合成近似的分钟数据
- 合成的分钟数据包含关键时间点：09:30, 10:00, 10:30, 11:00, 11:30, 13:00, 13:30, 14:00, **14:30**, 14:45, 14:59, 15:00
- 价格分布规则：按照日内价格变动的典型模式进行估算（如14:30价格 = open + (close - open) * 0.7）

**可选解决方案**：

1. **方案1：使用 Tushare Pro（推荐）**
   - Tushare Pro 提供完整的期货分钟历史数据，但需要积分（付费，约¥99/年）

2. **方案2：使用 RiceQuant/JoinQuant 数据**
   - 如果有米筐或聚宽的账号，可以获取完整的分钟历史数据

3. **方案3：本地缓存数据**
   - 在交易时段定期抓取并缓存分钟数据到本地数据库（SQLite/PostgreSQL），回测时从本地读取

4. **方案4：使用其他 akshare 接口**
   - akshare 可能有其他接口提供更长的分钟历史，需要进一步调研

5. **方案5：使用现有的日线合成Fallback（临时）**
   - 当前系统已实现从日线数据合成分钟数据的功能
   - 适用于"结算价差套利策略"等只需要特定时间点价格的策略
   - 注意：合成数据是近似值，可能与真实分钟数据有偏差

**状态**：已修复datetime列传递问题，待测试
