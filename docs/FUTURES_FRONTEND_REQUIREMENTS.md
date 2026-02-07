# 期货策略前端集成开发需求文档

> **文档版本**: v1.1  
> **创建时间**: 2026-02-04  
> **目的**: 将已完成的后端期货策略模块集成到前端UI中

---

## ✅ 需求确认（用户已确认）

| # | 问题 | 确认结果 |
|---|------|----------|
| 1 | 合约范围 | ✅ 只支持**主力合约** (IC0/IM0/IF0/IH0) |
| 2 | 行情刷新频率 | ✅ 默认**5秒**刷新 |
| 3 | 策略参数 | ✅ 保持默认（买入阈值1: 1%, 阈值2: 2%），**先不调整** |
| 4 | 通知渠道 | ✅ **Telegram + 浏览器 + 微信** 三个渠道 |
| 5 | UI风格 | ✅ 与现有系统**完全一致** |
| 6 | 数据存储 | ✅ **数据库持久化存储** |

---

## 📋 项目背景

### 已完成的后端模块（4个）

| 模块 | 文件位置 | 功能 |
|------|---------|------|
| 数据源 | `/backend_api_python/app/data_sources/cn_futures.py` | 获取股指期货K线数据 |
| 计算器 | `/backend_api_python/app/services/futures_calculator.py` | 保证金/手续费/结算价计算 |
| 通知 | `/backend_api_python/app/services/futures_notification.py` | 买卖信号通知模板 |
| 策略执行器 | `/backend_api_python/app/services/futures_strategy_executor.py` | 结算价套利策略逻辑 |

### 缺失部分

| 组件 | 说明 | 状态 |
|------|------|------|
| 后端API路由 | 期货策略的RESTful接口 | ❌ 未开发 |
| 前端管理页面 | 期货策略的Vue页面 | ❌ 未开发 |
| 前端API封装 | 调用后端的JS函数 | ❌ 未开发 |

---

## 🏗️ 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           前端 (Vue)                                 │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐    ┌──────────────────┐                       │
│  │  期货策略管理页面  │    │   API 封装层     │                       │
│  │  (FuturesStrategy)│◄──►│  (cn_futures.js) │                       │
│  └──────────────────┘    └────────┬─────────┘                       │
│                                   │                                  │
├───────────────────────────────────┼──────────────────────────────────┤
│                           HTTP API │                                 │
├───────────────────────────────────┼──────────────────────────────────┤
│                           后端 (Flask)                               │
│                                   │                                  │
│  ┌────────────────────────────────▼─────────────────────────────┐   │
│  │                    cn_futures.py (路由)                       │   │
│  │    /api/v1/cn-futures/...                                    │   │
│  └───────────────────────────────┬──────────────────────────────┘   │
│                                  │                                   │
│  ┌───────────────────────────────▼──────────────────────────────┐   │
│  │                已完成的4个模块                                │   │
│  │  CNFuturesDataSource │ FuturesCalculator │ FuturesNotifier   │   │
│  │  FuturesStrategyExecutor                                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📡 后端API设计

### 路由文件
- **文件位置**: `/backend_api_python/app/routes/cn_futures.py`
- **蓝图名称**: `cn_futures_bp`
- **URL前缀**: `/api/v1/cn-futures`

### API接口列表

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取合约列表 | GET | `/contracts` | 获取支持的合约信息 |
| 获取行情数据 | GET | `/quote` | 获取实时行情 |
| 获取K线数据 | GET | `/kline` | 获取历史K线 |
| 计算保证金 | POST | `/calculate/margin` | 计算开仓保证金 |
| 计算手续费 | POST | `/calculate/fee` | 计算交易手续费 |
| 策略状态 | GET | `/strategy/status` | 获取策略运行状态 |
| 启动策略 | POST | `/strategy/start` | 启动期货策略 |
| 停止策略 | POST | `/strategy/stop` | 停止期货策略 |
| 策略配置 | GET/PUT | `/strategy/config` | 获取/更新策略配置 |
| 交易记录 | GET | `/strategy/trades` | 获取策略交易记录 |
| 盈亏统计 | GET | `/strategy/pnl` | 获取盈亏统计 |

---

### API详细设计

#### 1. 获取合约列表
```
GET /api/v1/cn-futures/contracts
```

**Response:**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "contracts": [
      {
        "symbol": "IC0",
        "name": "中证500主力",
        "product": "IC",
        "multiplier": 200,
        "margin_ratio": 0.12,
        "tick_size": 0.2,
        "is_main": true
      },
      {
        "symbol": "IM0",
        "name": "中证1000主力",
        "product": "IM",
        "multiplier": 200,
        "margin_ratio": 0.12,
        "tick_size": 0.2,
        "is_main": true
      },
      {
        "symbol": "IF0",
        "name": "沪深300主力",
        "product": "IF",
        "multiplier": 300,
        "margin_ratio": 0.10,
        "tick_size": 0.2,
        "is_main": true
      },
      {
        "symbol": "IH0",
        "name": "上证50主力",
        "product": "IH",
        "multiplier": 300,
        "margin_ratio": 0.10,
        "tick_size": 0.2,
        "is_main": true
      }
    ]
  }
}
```

---

#### 2. 获取实时行情
```
GET /api/v1/cn-futures/quote?symbol=IC0
```

**Request Params:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 合约代码 (IC0, IM0, IF0, IH0) |

**Response:**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "symbol": "IC0",
    "name": "中证500主力",
    "last": 5510.0,
    "open": 5520.0,
    "high": 5550.0,
    "low": 5480.0,
    "prev_close": 5505.0,
    "prev_settlement": 5500.0,
    "volume": 123456,
    "amount": 12345678900.0,
    "open_interest": 98765,
    "bid": 5509.0,
    "ask": 5511.0,
    "change": 10.0,
    "change_pct": 0.18,
    "timestamp": 1738684800
  }
}
```

---

#### 3. 获取K线数据
```
GET /api/v1/cn-futures/kline?symbol=IC0&timeframe=1m&limit=100
```

**Request Params:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 合约代码 |
| timeframe | string | 是 | 周期 (1m, 5m, 15m, 30m, 1H) |
| limit | int | 否 | 数据条数，默认100，最大1000 |

**Response:**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "symbol": "IC0",
    "timeframe": "1m",
    "klines": [
      {
        "time": 1738684800,
        "open": 5500.0,
        "high": 5520.0,
        "low": 5480.0,
        "close": 5510.0,
        "volume": 12345
      }
    ]
  }
}
```

---

#### 4. 计算保证金
```
POST /api/v1/cn-futures/calculate/margin
```

**Request Body:**
```json
{
  "symbol": "IC0",
  "price": 5500,
  "quantity": 1
}
```

**Response:**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "symbol": "IC0",
    "price": 5500,
    "quantity": 1,
    "multiplier": 200,
    "contract_value": 1100000,
    "margin_ratio": 0.12,
    "margin_required": 132000
  }
}
```

---

#### 5. 计算手续费
```
POST /api/v1/cn-futures/calculate/fee
```

**Request Body:**
```json
{
  "symbol": "IC0",
  "price": 5500,
  "quantity": 1,
  "is_open": true,
  "is_close_today": false
}
```

**Response:**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "symbol": "IC0",
    "price": 5500,
    "quantity": 1,
    "contract_value": 1100000,
    "fee_rate": 0.000023,
    "fee_amount": 25.3,
    "is_close_today": false
  }
}
```

---

#### 6. 获取策略状态
```
GET /api/v1/cn-futures/strategy/status
```

**Response:**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "is_running": true,
    "strategy_name": "结算价套利策略",
    "monitored_symbols": ["IC0", "IM0"],
    "positions": [
      {
        "symbol": "IC0",
        "status": "position_open",
        "entry_price": 5450,
        "entry_time": "2026-02-04 14:45:00",
        "current_price": 5510,
        "quantity": 1,
        "unrealized_pnl": 12000,
        "pnl_pct": 2.19
      }
    ],
    "today_signals": [
      {
        "type": "buy",
        "symbol": "IC0",
        "price": 5450,
        "drop_pct": -1.05,
        "time": "2026-02-04 14:45:00"
      }
    ],
    "last_check_time": "2026-02-04 14:57:00"
  }
}
```

---

#### 7. 启动策略
```
POST /api/v1/cn-futures/strategy/start
```

**Request Body:**
```json
{
  "symbols": ["IC0", "IM0"],
  "notification_channels": ["telegram", "browser"]
}
```

**Response:**
```json
{
  "code": 1,
  "msg": "策略已启动",
  "data": {
    "started_at": "2026-02-04 14:30:00"
  }
}
```

---

#### 8. 停止策略
```
POST /api/v1/cn-futures/strategy/stop
```

**Response:**
```json
{
  "code": 1,
  "msg": "策略已停止",
  "data": {
    "stopped_at": "2026-02-04 15:00:00"
  }
}
```

---

#### 9. 策略配置
```
GET /api/v1/cn-futures/strategy/config

PUT /api/v1/cn-futures/strategy/config
```

**GET Response / PUT Request Body:**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "symbols": ["IC0", "IM0"],
    "drop_threshold_1": 0.01,
    "drop_threshold_2": 0.02,
    "monitoring_start": "14:30:00",
    "monitoring_end": "14:57:00",
    "max_position": 2,
    "notification_channels": ["telegram", "browser", "wechat"],
    "telegram_chat_id": "123456789",
    "wechat_webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
  }
}
```

---

#### 10. 交易记录
```
GET /api/v1/cn-futures/strategy/trades?limit=50
```

**Response:**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "trades": [
      {
        "id": 1,
        "symbol": "IC0",
        "type": "buy",
        "price": 5450,
        "quantity": 1,
        "margin": 130800,
        "fee": 25.07,
        "time": "2026-02-04 14:45:00"
      },
      {
        "id": 2,
        "symbol": "IC0",
        "type": "sell",
        "price": 5520,
        "quantity": 1,
        "margin": 0,
        "fee": 25.38,
        "pnl": 14000,
        "time": "2026-02-05 09:30:00"
      }
    ],
    "total": 2
  }
}
```

---

#### 11. 盈亏统计
```
GET /api/v1/cn-futures/strategy/pnl?period=month
```

**Request Params:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| period | string | 否 | 统计周期: day, week, month, year, all |

**Response:**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "period": "month",
    "total_trades": 15,
    "win_trades": 12,
    "lose_trades": 3,
    "win_rate": 80.0,
    "total_pnl": 168000,
    "avg_pnl": 11200,
    "max_win": 28000,
    "max_loss": -8000,
    "total_fee": 760.5,
    "net_pnl": 167239.5,
    "daily_pnl": [
      {"date": "2026-02-01", "pnl": 14000},
      {"date": "2026-02-02", "pnl": -8000},
      {"date": "2026-02-03", "pnl": 21000}
    ]
  }
}
```

---

## 🎨 前端页面设计

### 文件结构

```
quantdinger_vue/src/
├── api/
│   └── cn_futures.js              # 期货API封装（新建）
├── views/
│   └── futures-strategy/          # 期货策略页面（新建）
│       ├── index.vue              # 主页面
│       └── components/
│           ├── ContractSelector.vue   # 合约选择器
│           ├── QuotePanel.vue         # 行情面板
│           ├── StrategyPanel.vue      # 策略控制面板
│           ├── PositionTable.vue      # 持仓表格
│           ├── TradeHistory.vue       # 交易记录
│           └── PnlChart.vue           # 盈亏图表
└── router/
    └── index.js                   # 添加路由（修改）
```

---

### 页面布局

```
┌────────────────────────────────────────────────────────────────────────┐
│  📊 期货策略管理                                        [启动] [停止]  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ 合约选择 ─────────────────────────────────────────────────────┐   │
│  │  [✓] IC0 中证500  [✓] IM0 中证1000  [ ] IF0 沪深300  [ ] IH0 上证50 │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─ 实时行情 ─────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │   IC0 中证500主力           IM0 中证1000主力                     │   │
│  │   ┌─────────────────┐      ┌─────────────────┐                  │   │
│  │   │  5510.0  ▲+0.18%│      │  6280.0  ▼-0.32%│                  │   │
│  │   │  基准: 5500      │      │  基准: 6300      │                  │   │
│  │   │  跌幅: -0.18%    │      │  跌幅: +0.32%    │                  │   │
│  │   └─────────────────┘      └─────────────────┘                  │   │
│  │                                                                  │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─ 策略状态 ──────────────────┐  ┌─ 策略配置 ─────────────────────┐   │
│  │  状态: 🟢 运行中             │  │  买入阈值1: [  1.0  ] %        │   │
│  │  监控时段: 14:30 - 14:57    │  │  买入阈值2: [  2.0  ] %        │   │
│  │  今日信号: 1个买入          │  │  最大持仓: [  2  ] 手          │   │
│  │  当前持仓: IC0 x 1手        │  │  通知渠道: [✓]Telegram [✓]浏览器│   │
│  └─────────────────────────────┘  └────────────────────────────────┘   │
│                                                                         │
│  ┌─ 当前持仓 ─────────────────────────────────────────────────────┐   │
│  │  合约    方向   数量   开仓价    现价     盈亏      盈亏%   开仓时间 │   │
│  │  ────────────────────────────────────────────────────────────  │   │
│  │  IC0     多     1手    5450    5510   +12,000   +2.19%  14:45  │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─ 盈亏统计 ──────────────────────────────────────────────────────┐   │
│  │                                                                   │   │
│  │   本月盈亏: +167,239 元     胜率: 80%     交易次数: 15次         │   │
│  │                                                                   │   │
│  │   [==========盈亏曲线图表==========]                             │   │
│  │                                                                   │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─ 交易记录 ─────────────────────────────────────────────────────┐   │
│  │  时间              合约   类型   价格    数量    盈亏     手续费  │   │
│  │  ────────────────────────────────────────────────────────────  │   │
│  │  02-05 09:30:00   IC0    卖出   5520    1手   +14,000   25.38  │   │
│  │  02-04 14:45:00   IC0    买入   5450    1手     -       25.07  │   │
│  │  02-03 09:30:00   IM0    卖出   6350    1手   +21,000   29.21  │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 组件详细设计

#### 1. ContractSelector.vue - 合约选择器

**功能:**
- 显示4个股指期货合约复选框
- 支持多选/全选
- 显示合约名称和当前主力合约代码

**Props:**
```typescript
interface Props {
  value: string[]  // 已选中的合约代码
}
```

**Events:**
```typescript
emit('update:value', selectedSymbols: string[])
```

---

#### 2. QuotePanel.vue - 行情面板

**功能:**
- 显示选中合约的实时行情卡片
- 每5秒自动刷新行情
- 显示：最新价、涨跌幅、基准价(14:30)、当前跌幅
- 价格颜色：上涨绿色，下跌红色

**Props:**
```typescript
interface Props {
  symbols: string[]  // 监控的合约列表
}
```

---

#### 3. StrategyPanel.vue - 策略控制面板

**功能:**
- 显示策略运行状态（运行中/已停止）
- 启动/停止按钮
- 策略配置表单：
  - 买入阈值1 (默认1%)
  - 买入阈值2 (默认2%)
  - 最大持仓手数 (默认2)
  - 通知渠道选择

**Props:**
```typescript
interface Props {
  status: StrategyStatus
  config: StrategyConfig
}
```

**Events:**
```typescript
emit('start')
emit('stop')
emit('update:config', newConfig: StrategyConfig)
```

---

#### 4. PositionTable.vue - 持仓表格

**功能:**
- 显示当前持仓列表
- 列：合约、方向、数量、开仓价、现价、盈亏、盈亏%、开仓时间
- 实时更新现价和盈亏

**Props:**
```typescript
interface Props {
  positions: Position[]
}
```

---

#### 5. TradeHistory.vue - 交易记录

**功能:**
- 显示历史交易列表
- 支持分页
- 列：时间、合约、类型、价格、数量、盈亏、手续费

**Props:**
```typescript
interface Props {
  trades: Trade[]
}
```

---

#### 6. PnlChart.vue - 盈亏图表

**功能:**
- 显示盈亏曲线图
- 统计卡片：本月盈亏、胜率、交易次数
- 时间筛选：日/周/月/年

---

### 前端API封装

**文件:** `/quantdinger_vue/src/api/cn_futures.js`

```javascript
import request from '@/utils/request'

const api = {
  contracts: '/api/v1/cn-futures/contracts',
  quote: '/api/v1/cn-futures/quote',
  kline: '/api/v1/cn-futures/kline',
  calculateMargin: '/api/v1/cn-futures/calculate/margin',
  calculateFee: '/api/v1/cn-futures/calculate/fee',
  strategyStatus: '/api/v1/cn-futures/strategy/status',
  strategyStart: '/api/v1/cn-futures/strategy/start',
  strategyStop: '/api/v1/cn-futures/strategy/stop',
  strategyConfig: '/api/v1/cn-futures/strategy/config',
  strategyTrades: '/api/v1/cn-futures/strategy/trades',
  strategyPnl: '/api/v1/cn-futures/strategy/pnl'
}

// 获取合约列表
export function getContracts() {
  return request({ url: api.contracts, method: 'get' })
}

// 获取实时行情
export function getQuote(symbol) {
  return request({ url: api.quote, method: 'get', params: { symbol } })
}

// 获取K线数据
export function getKline(symbol, timeframe, limit = 100) {
  return request({ url: api.kline, method: 'get', params: { symbol, timeframe, limit } })
}

// 计算保证金
export function calculateMargin(data) {
  return request({ url: api.calculateMargin, method: 'post', data })
}

// 计算手续费
export function calculateFee(data) {
  return request({ url: api.calculateFee, method: 'post', data })
}

// 获取策略状态
export function getStrategyStatus() {
  return request({ url: api.strategyStatus, method: 'get' })
}

// 启动策略
export function startStrategy(data) {
  return request({ url: api.strategyStart, method: 'post', data })
}

// 停止策略
export function stopStrategy() {
  return request({ url: api.strategyStop, method: 'post' })
}

// 获取策略配置
export function getStrategyConfig() {
  return request({ url: api.strategyConfig, method: 'get' })
}

// 更新策略配置
export function updateStrategyConfig(data) {
  return request({ url: api.strategyConfig, method: 'put', data })
}

// 获取交易记录
export function getStrategyTrades(limit = 50) {
  return request({ url: api.strategyTrades, method: 'get', params: { limit } })
}

// 获取盈亏统计
export function getStrategyPnl(period = 'month') {
  return request({ url: api.strategyPnl, method: 'get', params: { period } })
}
```

---

### 路由配置

**修改文件:** `/quantdinger_vue/src/router/index.js`

```javascript
// 添加路由
{
  path: '/futures-strategy',
  name: 'FuturesStrategy',
  meta: {
    title: '期货策略',
    icon: 'line-chart',
    requireAuth: true
  },
  component: () => import('@/views/futures-strategy/index.vue')
}
```

---

## 📝 数据类型定义

### TypeScript 接口

```typescript
// 合约信息
interface Contract {
  symbol: string       // 合约代码 IC0
  name: string         // 合约名称 中证500主力
  product: string      // 品种代码 IC
  multiplier: number   // 合约乘数 200
  margin_ratio: number // 保证金比例 0.12
  tick_size: number    // 最小变动 0.2
  is_main: boolean     // 是否主力合约
}

// 行情数据
interface Quote {
  symbol: string
  name: string
  last: number         // 最新价
  open: number
  high: number
  low: number
  prev_close: number   // 昨收价
  prev_settlement: number // 昨结算价
  volume: number
  bid: number
  ask: number
  change: number       // 涨跌额
  change_pct: number   // 涨跌幅%
  timestamp: number
}

// 策略状态
type StrategyStatusType = 'idle' | 'monitoring' | 'position_open' | 'stopped'

interface StrategyStatus {
  is_running: boolean
  strategy_name: string
  monitored_symbols: string[]
  positions: Position[]
  today_signals: Signal[]
  last_check_time: string
}

// 持仓
interface Position {
  symbol: string
  status: string
  entry_price: number
  entry_time: string
  current_price: number
  quantity: number
  unrealized_pnl: number
  pnl_pct: number
}

// 信号
interface Signal {
  type: 'buy' | 'sell'
  symbol: string
  price: number
  drop_pct: number
  time: string
}

// 策略配置
interface StrategyConfig {
  symbols: string[]
  drop_threshold_1: number
  drop_threshold_2: number
  monitoring_start: string
  monitoring_end: string
  max_position: number
  notification_channels: string[]  // 支持: telegram, browser, wechat
  telegram_chat_id?: string
  wechat_webhook?: string  // 企业微信机器人webhook地址
}

// 交易记录
interface Trade {
  id: number
  symbol: string
  type: 'buy' | 'sell'
  price: number
  quantity: number
  margin: number
  fee: number
  pnl?: number
  time: string
}

// 盈亏统计
interface PnlStats {
  period: string
  total_trades: number
  win_trades: number
  lose_trades: number
  win_rate: number
  total_pnl: number
  avg_pnl: number
  max_win: number
  max_loss: number
  total_fee: number
  net_pnl: number
  daily_pnl: { date: string; pnl: number }[]
}
```

---

## ⏰ 开发计划

| 阶段 | 任务 | 预计工时 |
|------|------|---------|
| 1 | 后端API路由 (`cn_futures.py`) | 4小时 |
| 2 | 前端API封装 (`cn_futures.js`) | 1小时 |
| 3 | 前端页面主框架 (`index.vue`) | 3小时 |
| 4 | 合约选择器组件 | 1小时 |
| 5 | 行情面板组件 | 2小时 |
| 6 | 策略控制面板 | 2小时 |
| 7 | 持仓表格组件 | 1小时 |
| 8 | 交易记录组件 | 1小时 |
| 9 | 盈亏图表组件 | 2小时 |
| 10 | 集成测试 | 2小时 |
| **总计** | | **约19小时** |

---

## ✅ 验收标准

### 功能验收
- [ ] 可以查看4个股指期货的实时行情
- [ ] 可以启动/停止期货策略
- [ ] 可以修改策略配置参数
- [ ] 可以查看当前持仓和盈亏
- [ ] 可以查看历史交易记录
- [ ] 可以查看盈亏统计图表
- [ ] 信号触发时可以收到通知（Telegram/浏览器/微信）
- [ ] 交易记录、持仓、配置等数据持久化到数据库

### UI验收
- [ ] 界面风格与现有系统一致
- [ ] 响应式布局，支持不同屏幕尺寸
- [ ] 数据加载时有loading状态
- [ ] 错误时有友好的提示信息

### 性能验收
- [ ] 行情刷新间隔5秒，无卡顿
- [ ] 页面首次加载时间 < 2秒

---

## 🔗 相关文档

- [MVP并行开发任务文档](./MVP_PARALLEL_TASKS.md) - 后端模块接口定义
- [现有策略API](../quantdinger_vue/src/api/strategy.js) - 前端API封装参考

---

## 🗄️ 数据库设计

### 新增数据表

#### 1. futures_strategy_config - 策略配置表
```sql
CREATE TABLE futures_strategy_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbols TEXT NOT NULL,                    -- JSON数组: ["IC0", "IM0"]
    drop_threshold_1 REAL DEFAULT 0.01,       -- 买入阈值1 (1%)
    drop_threshold_2 REAL DEFAULT 0.02,       -- 买入阈值2 (2%)
    monitoring_start TEXT DEFAULT '14:30:00', -- 监控开始时间
    monitoring_end TEXT DEFAULT '14:57:00',   -- 监控结束时间
    max_position INTEGER DEFAULT 2,           -- 最大持仓手数
    notification_channels TEXT,               -- JSON数组: ["telegram", "wechat"]
    telegram_chat_id TEXT,
    wechat_webhook TEXT,
    is_running BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. futures_positions - 持仓表
```sql
CREATE TABLE futures_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,                     -- 合约代码
    direction TEXT DEFAULT 'long',            -- 方向: long/short
    quantity INTEGER NOT NULL,                -- 持仓手数
    entry_price REAL NOT NULL,                -- 开仓价格
    entry_time DATETIME NOT NULL,             -- 开仓时间
    status TEXT DEFAULT 'open',               -- 状态: open/closed
    close_price REAL,                         -- 平仓价格
    close_time DATETIME,                      -- 平仓时间
    realized_pnl REAL,                        -- 已实现盈亏
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. futures_trades - 交易记录表
```sql
CREATE TABLE futures_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,                     -- 合约代码
    trade_type TEXT NOT NULL,                 -- 类型: buy/sell
    price REAL NOT NULL,                      -- 成交价格
    quantity INTEGER NOT NULL,                -- 成交手数
    margin REAL,                              -- 保证金
    fee REAL NOT NULL,                        -- 手续费
    pnl REAL,                                 -- 盈亏(平仓时)
    signal_reason TEXT,                       -- 信号原因
    trade_time DATETIME NOT NULL,             -- 成交时间
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. futures_signals - 信号记录表
```sql
CREATE TABLE futures_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,                     -- 合约代码
    signal_type TEXT NOT NULL,                -- 类型: buy/sell
    trigger_price REAL NOT NULL,              -- 触发价格
    base_price REAL NOT NULL,                 -- 基准价格
    drop_pct REAL NOT NULL,                   -- 跌幅百分比
    is_executed BOOLEAN DEFAULT 0,            -- 是否已执行
    signal_time DATETIME NOT NULL,            -- 信号时间
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-02-04 | 初始版本 |
| v1.1 | 2026-02-04 | 添加用户确认、微信通知、数据库设计 |
