# QuantDinger Changelog

This document records version updates, new features, bug fixes, and database migration instructions.

---

## V2.3.1 (2026-02-09)

### 🚀 New Features

#### Futures Unified Backtest Engine (期货统一回测引擎)
- **Cross-Day Trading Simulation (FR-4)**: New `_simulate_trading_futures_cross_day()` engine supporting the settlement arbitrage core pattern — entry at today's close, exit at next day's open
- **Futures Indicator Helpers (FR-1~FR-6)**: New `FuturesIndicatorHelpers` module providing built-in helper functions for minute-level futures strategies, automatically injected when market type is `CNFutures`
- **Strategy Metadata Parsing**: Auto-detect `# @strategy_type`, `# @timeframe` and other metadata directives from indicator code
- **Entry Signal Format**: New `entry_signal` / `exit_type` / `entry_price_type` signal format for futures cross-day strategies, in addition to existing 4-way and buy/sell formats
- **VWAP Entry Support**: Supports VWAP-based entry pricing when available in executed DataFrame
- **Futures Fee Calculation**: Automatic contract multiplier and commission rate lookup from `CNFuturesDataSource.PRODUCTS`

### 🐛 Bug Fixes
- **Fixed `KeyError: 'datetime'`**: Backtest execution now auto-injects `datetime` column from DataFrame index when missing, preventing user script errors
- **Fixed signal validation error**: Improved signal dict validation to accept futures cross-day format alongside existing formats

### 🎨 UI/UX Improvements
- **MonitorPanel.vue**: Refactored column definitions for better readability and maintainability
- **PnlChart.vue**: Enhanced P&L chart with improved data visualization
- **PositionTable.vue**: Enhanced position table with richer display fields
- **TradeHistory.vue**: Enhanced trade history with more detailed trade information

### 📁 Files Added/Modified

#### Backend - New Files
- **`backend_api_python/app/services/futures_indicator_helpers.py`** - Futures indicator helper functions module (FR-1~FR-6), provides `get_minute_kline()`, `get_settlement_price()`, `calc_vwap()`, etc.

#### Backend - Modified Files
- **`backend_api_python/app/services/backtest.py`** (+268 lines)
  - Imported `FuturesIndicatorHelpers` with graceful fallback
  - Added `market` / `symbol` parameters to backtest params dict
  - Auto-inject `datetime` column in execution environment
  - Auto-inject futures helper functions for CNFutures market
  - New `entry_signal` signal extraction path (priority: 4-way > entry_signal > buy/sell)
  - New `_simulate_trading_futures_cross_day()` method for cross-day simulation

#### Frontend - Modified Files
- **`quantdinger_vue/src/views/settlement-strategy/components/MonitorPanel.vue`** - Column definitions refactored to multi-line format
- **`quantdinger_vue/src/views/settlement-strategy/components/PnlChart.vue`** - Enhanced chart features
- **`quantdinger_vue/src/views/settlement-strategy/components/PositionTable.vue`** - Enhanced position display
- **`quantdinger_vue/src/views/settlement-strategy/components/TradeHistory.vue`** - Enhanced trade history display

#### Documentation - New Files
- **`docs/china-futures/FUTURES_UNIFIED_BACKTEST_REQUIREMENT.md`** - Futures unified backtest system requirement document
- **`docs/china-futures/FUTURES_UNIFIED_BACKTEST_TODOLIST.md`** - Futures unified backtest implementation todolist

### 📋 Database Migration

**No database changes required for this version.**

### 📝 Configuration Notes
- No new environment variables required
- Futures indicator helpers are auto-loaded when `market=CNFutures` is selected in backtest
- Strategy scripts can now use `# @strategy_type: settlement_arbitrage` metadata directives

---

## V2.3.0 (2026-02-09)

### 🚀 New Features

#### China Futures Strategy Module (中国期货策略模块)
- **Complete Futures Trading System**: Full-featured futures trading module with real-time quotes, position management, and strategy execution
- **Settlement Arbitrage Strategy**: Index futures settlement price arbitrage strategy implementation
- **Futures Calculator**: Professional futures calculation service including margin, P&L, and settlement price calculations
- **Real-time Quote Panel**: Live market data display for futures contracts (IC/IF/IH/IM)
- **Position Management**: Complete position tracking with real-time P&L calculation
- **Trade History**: Detailed trade execution history with filtering and export capabilities
- **Strategy Panel**: Strategy configuration and execution control interface
- **Futures Notification Service**: Dedicated notification system for futures trading alerts

### 📁 Files Added/Modified

#### Backend - New Files
- **`backend_api_python/app/data_sources/cn_futures.py`** - China futures data source implementation
- **`backend_api_python/app/models/futures.py`** - Futures data models and schemas
- **`backend_api_python/app/routes/cn_futures.py`** - Futures API endpoints
- **`backend_api_python/app/services/futures_calculator.py`** - Futures calculation service
- **`backend_api_python/app/services/futures_notification.py`** - Futures notification service
- **`backend_api_python/app/services/futures_strategy_executor.py`** - Strategy execution engine
- **`backend_api_python/scripts/add_cnfutures_symbols.py`** - Script to add futures symbols to database

#### Backend - Modified Files
- **`backend_api_python/app/data_sources/factory.py`** - Added CNFutures data source factory
- **`backend_api_python/app/routes/__init__.py`** - Registered futures routes
- **`backend_api_python/app/routes/market.py`** - Extended market routes for futures
- **`backend_api_python/app/services/backtest.py`** - Enhanced backtest service for futures
- **`backend_api_python/migrations/init.sql`** - Added futures-related database tables

#### Frontend - New Files
- **`quantdinger_vue/src/api/cn_futures.js`** - Futures API client
- **`quantdinger_vue/src/views/futures-strategy/index.vue`** - Main futures strategy page
- **`quantdinger_vue/src/views/futures-strategy/components/ContractSelector.vue`** - Contract selection component
- **`quantdinger_vue/src/views/futures-strategy/components/PnlChart.vue`** - P&L chart visualization
- **`quantdinger_vue/src/views/futures-strategy/components/PositionTable.vue`** - Position display table
- **`quantdinger_vue/src/views/futures-strategy/components/QuotePanel.vue`** - Real-time quote panel
- **`quantdinger_vue/src/views/futures-strategy/components/StrategyPanel.vue`** - Strategy control panel
- **`quantdinger_vue/src/views/futures-strategy/components/TradeHistory.vue`** - Trade history component

#### Frontend - Modified Files
- **`quantdinger_vue/src/components/SettingDrawer/settingConfig.js`** - Added futures settings
- **`quantdinger_vue/src/config/router.config.js`** - Added futures strategy route
- **`quantdinger_vue/src/locales/lang/en-US.js`** - Added English translations
- **`quantdinger_vue/src/locales/lang/zh-CN.js`** - Added Chinese translations
- **`quantdinger_vue/src/views/indicator-analysis/index.vue`** - Enhanced indicator analysis

#### Strategy Templates
- **`strategies/README.md`** - Strategy development documentation
- **`strategies/index_futures_settlement_arbitrage.py`** - Settlement arbitrage strategy
- **`strategies/strategy_template.py`** - Base strategy template

#### Testing
- **`backend_api_python/tests/test_cn_futures.py`** - Futures unit tests
- **`backend_api_python/tests/test_futures_integration.py`** - Integration tests
- **`backend_api_python/run_futures_test.py`** - Futures test runner
- **`backend_api_python/run_all_tests.py`** - Complete test suite runner
- **`backend_api_python/validate_futures.py`** - Futures validation script
- **`backend_api_python/check_mvp.py`** - MVP checklist validator

#### Build & Deployment
- **`build-and-start.bat`** - Windows build and start script

### 📋 Database Migration

**Run the following SQL on your PostgreSQL database before deploying V2.3.0:**

```sql
-- ============================================================
-- QuantDinger V2.3.0 Database Migration
-- China Futures Strategy Tables
-- ============================================================

-- 1. Futures Positions Table
CREATE TABLE IF NOT EXISTS qd_futures_positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES qd_users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,  -- 'long' or 'short'
    quantity INTEGER NOT NULL DEFAULT 0,
    avg_price DECIMAL(18, 4) NOT NULL,
    margin DECIMAL(18, 4) DEFAULT 0,
    unrealized_pnl DECIMAL(18, 4) DEFAULT 0,
    realized_pnl DECIMAL(18, 4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_futures_positions_user ON qd_futures_positions(user_id);
CREATE INDEX IF NOT EXISTS idx_futures_positions_symbol ON qd_futures_positions(symbol);

-- 2. Futures Trades Table
CREATE TABLE IF NOT EXISTS qd_futures_trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES qd_users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    action VARCHAR(10) NOT NULL,  -- 'open' or 'close'
    quantity INTEGER NOT NULL,
    price DECIMAL(18, 4) NOT NULL,
    commission DECIMAL(18, 4) DEFAULT 0,
    pnl DECIMAL(18, 4) DEFAULT 0,
    strategy_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_futures_trades_user ON qd_futures_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_futures_trades_symbol ON qd_futures_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_futures_trades_created ON qd_futures_trades(created_at DESC);

-- 3. Futures Strategy Config Table
CREATE TABLE IF NOT EXISTS qd_futures_strategy_config (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES qd_users(id) ON DELETE CASCADE,
    strategy_name VARCHAR(100) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, strategy_name)
);

CREATE INDEX IF NOT EXISTS idx_futures_strategy_user ON qd_futures_strategy_config(user_id);

-- Migration Complete
DO $$
BEGIN
    RAISE NOTICE '✅ QuantDinger V2.3.0 database migration completed!';
END $$;
```

### 📝 Configuration Notes
- Futures data requires valid market data subscription
- Strategy execution requires proper broker connection configuration
- Notification settings can be configured in the Settings page

### 🔮 Upcoming Features
- Multi-contract spread trading
- Automated roll-over for expiring contracts
- Advanced risk management dashboard
- Historical settlement analysis tools

---

## V2.2.0 (2026-02-05)

### 🚀 New Features

#### China Futures Backtesting Support
- **Market Type Extension**: Added `CNFutures` (中国期货) market type to Indicator Analysis page
- **Backtest Engine Integration**: Integrated `FuturesCalculator` into backtest service for futures-specific calculations
- **Futures Contract Support**: Backtest modal now supports futures contract codes (IC0, IM0, IF0, IH0)

### 📁 Files Modified

#### Backend
- **`backend_api_python/app/services/backtest.py`**
  - Imported `FuturesCalculator` from `app.datasources.cn_futures`
  - Added `market` and `symbol` parameters to `_simulate_trading()` method
  - Added `market` and `symbol` parameters to `_simulate_trading_new_format()` method
  - Added CNFutures market type detection logic
  - Updated `run()` method to pass market and symbol to simulation methods

#### Frontend
- **`quantdinger_vue/src/views/indicator-analysis/index.vue`**
  - Added `CNFutures` option to `loadMarketTypes()` function
  - Updated `getMarketName()` to support CNFutures market display name
  - Updated `getMarketColor()` to use red color for futures market

#### Internationalization
- **`quantdinger_vue/src/locales/lang/zh-CN.js`**
  - Added `'dashboard.analysis.market.CNFutures': '中国期货'`

- **`quantdinger_vue/src/locales/lang/en-US.js`**
  - Added `'dashboard.analysis.market.CNFutures': 'China Futures'`

#### Documentation
- **`docs/FUTURES_FRONTEND_TODOLIST.md`**
  - Added Phase 7: Futures Backtesting Feature Integration
  - Documented 6 sub-tasks with dependency graph
  - Updated completion status for implemented features

### 📋 Database Migration

**No database changes required for this version.**

### 📝 Configuration Notes
- No new environment variables required
- Futures calculator uses existing configuration from `FuturesCalculator` class

### 🔮 Upcoming Features (Documented in Requirements)
- Futures contract quick selector in backtest modal
- Detailed margin and commission calculation in backtest results
- Futures-specific result fields (margin usage, commission breakdown)

---

## V2.1.1 (2026-01-31)

### 🚀 New Features

#### AI Analysis System Overhaul
- **Fast Analysis Mode**: Replaced the complex multi-agent system with a streamlined single LLM call architecture for faster and more accurate analysis
- **Progressive Loading**: Market data now loads independently - each section (sentiment, indices, heatmap, calendar) displays as soon as it's ready
- **Professional Loading Animation**: New progress bar with step indicators during AI analysis
- **Analysis Memory**: Store analysis results for history review and user feedback
- **Stop Loss/Take Profit Calculation**: Now based on ATR (Average True Range) and Support/Resistance levels with clear methodology hints

#### Global Market Integration
- Integrated Global Market data directly into AI Analysis page
- Real-time scrolling display of major global indices with flags, prices, and percentage changes
- Interactive heatmaps for Crypto, Commodities, Sectors, and Forex
- Economic calendar with bullish/bearish/neutral impact indicators
- Commodities heatmap added (Gold, Silver, Crude Oil, etc.)

#### Indicator Community Enhancements
- **Admin Review System**: Administrators can now review, approve, reject, unpublish, and delete community indicators
- **Purchase & Rating System**: Users can buy indicators, leave ratings and comments
- **Statistics Tracking**: Purchase count, average rating, rating count, view count for each indicator

#### Trading Assistant Improvements
- Improved IBKR/MT5 connection test feedback
- Added local deployment warning for external trading platforms
- Virtual profit/loss calculation for signal-only strategies

### 🐛 Bug Fixes
- Fixed progress bar and timer not animating during AI analysis
- Fixed missing i18n translations for various components
- Fixed Tiingo API rate limit issues with caching
- Fixed A-share and H-share data fetching with multiple fallback sources
- Fixed watchlist price batch fetch timeout handling
- Fixed heatmap multi-language support for commodities and forex
- **Fixed AI analysis history not filtered by user** - All users were seeing the same history records; now each user only sees their own analysis history
- **Fixed "Missing Turnstile token" error when changing password** - Logged-in users no longer need Turnstile verification to request password change verification code

### 🎨 UI/UX Improvements
- Reorganized left menu: Indicator Market moved below Indicator Analysis, Settings moved to bottom
- Skeleton loading animations for progressive data display
- Dark theme support for all new components
- Compact market overview bar design

### 📋 Database Migration

**Run the following SQL on your PostgreSQL database before deploying V2.1.1:**

```sql
-- ============================================================
-- QuantDinger V2.1.1 Database Migration
-- ============================================================

-- 1. AI Analysis Memory Table
CREATE TABLE IF NOT EXISTS qd_analysis_memory (
    id SERIAL PRIMARY KEY,
    market VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    decision VARCHAR(10) NOT NULL,
    confidence INT DEFAULT 50,
    price_at_analysis DECIMAL(24, 8),
    entry_price DECIMAL(24, 8),
    stop_loss DECIMAL(24, 8),
    take_profit DECIMAL(24, 8),
    summary TEXT,
    reasons JSONB,
    risks JSONB,
    scores JSONB,
    indicators_snapshot JSONB,
    raw_result JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP,
    actual_outcome VARCHAR(20),
    actual_return_pct DECIMAL(10, 4),
    was_correct BOOLEAN,
    user_feedback VARCHAR(20),
    feedback_at TIMESTAMP
);

-- Add raw_result column if table exists but column doesn't
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_analysis_memory' AND column_name = 'raw_result'
    ) THEN
        ALTER TABLE qd_analysis_memory ADD COLUMN raw_result JSONB;
    END IF;
END $$;

-- Add user_id column for user-specific history filtering
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_analysis_memory' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE qd_analysis_memory ADD COLUMN user_id INT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_analysis_memory_symbol ON qd_analysis_memory(market, symbol);
CREATE INDEX IF NOT EXISTS idx_analysis_memory_created ON qd_analysis_memory(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_memory_validated ON qd_analysis_memory(validated_at) WHERE validated_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_analysis_memory_user ON qd_analysis_memory(user_id);

-- 2. Indicator Purchase Records
CREATE TABLE IF NOT EXISTS qd_indicator_purchases (
    id SERIAL PRIMARY KEY,
    indicator_id INTEGER NOT NULL REFERENCES qd_indicator_codes(id) ON DELETE CASCADE,
    buyer_id INTEGER NOT NULL REFERENCES qd_users(id) ON DELETE CASCADE,
    seller_id INTEGER NOT NULL REFERENCES qd_users(id),
    price DECIMAL(10,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(indicator_id, buyer_id)
);

CREATE INDEX IF NOT EXISTS idx_purchases_indicator ON qd_indicator_purchases(indicator_id);
CREATE INDEX IF NOT EXISTS idx_purchases_buyer ON qd_indicator_purchases(buyer_id);
CREATE INDEX IF NOT EXISTS idx_purchases_seller ON qd_indicator_purchases(seller_id);

-- 3. Indicator Comments
CREATE TABLE IF NOT EXISTS qd_indicator_comments (
    id SERIAL PRIMARY KEY,
    indicator_id INTEGER NOT NULL REFERENCES qd_indicator_codes(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES qd_users(id) ON DELETE CASCADE,
    rating INTEGER DEFAULT 5 CHECK (rating >= 1 AND rating <= 5),
    content TEXT DEFAULT '',
    parent_id INTEGER REFERENCES qd_indicator_comments(id) ON DELETE CASCADE,
    is_deleted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comments_indicator ON qd_indicator_comments(indicator_id);
CREATE INDEX IF NOT EXISTS idx_comments_user ON qd_indicator_comments(user_id);

-- 4. Indicator Codes Extensions
DO $$
BEGIN
    -- Purchase count
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'purchase_count'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN purchase_count INTEGER DEFAULT 0;
    END IF;
    
    -- Average rating
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'avg_rating'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN avg_rating DECIMAL(3,2) DEFAULT 0;
    END IF;
    
    -- Rating count
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'rating_count'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN rating_count INTEGER DEFAULT 0;
    END IF;
    
    -- View count
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'view_count'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN view_count INTEGER DEFAULT 0;
    END IF;
    
    -- Review status
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'review_status'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN review_status VARCHAR(20) DEFAULT 'approved';
        UPDATE qd_indicator_codes SET review_status = 'approved' WHERE publish_to_community = 1;
    END IF;
    
    -- Review note
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'review_note'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN review_note TEXT DEFAULT '';
    END IF;
    
    -- Reviewed at
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'reviewed_at'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN reviewed_at TIMESTAMP;
    END IF;
    
    -- Reviewed by
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'reviewed_by'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN reviewed_by INTEGER;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_indicator_review_status ON qd_indicator_codes(review_status);

-- 5. User Table Extensions
DO $$
BEGIN
    -- Token version (for single-client login)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_users' AND column_name = 'token_version'
    ) THEN
        ALTER TABLE qd_users ADD COLUMN token_version INTEGER DEFAULT 1;
    END IF;
    
    -- Notification settings
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_users' AND column_name = 'notification_settings'
    ) THEN
        ALTER TABLE qd_users ADD COLUMN notification_settings TEXT DEFAULT '{}';
    END IF;
END $$;

-- Migration Complete
DO $$
BEGIN
    RAISE NOTICE '✅ QuantDinger V2.1.1 database migration completed!';
END $$;
```

### 🗑️ Removed
- Old multi-agent AI analysis system (`backend_api_python/app/services/agents/` directory)
- Old analysis routes and services
- Standalone Global Market page (merged into AI Analysis)
- Reflection worker background process

### ⚠️ Breaking Changes
- AI Analysis API endpoints changed from `/api/analysis/*` to `/api/fast-analysis/*`
- Old analysis history data is not compatible with new format

### 📝 Configuration Notes
- No new environment variables required
- Existing LLM configuration in System Settings will be used for AI Analysis

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| V2.3.1 | 2026-02-09 | Futures unified backtest engine, cross-day simulation, indicator helpers, UI enhancements |
| V2.3.0 | 2026-02-09 | China Futures Strategy module, settlement arbitrage, real-time quotes, position management |
| V2.2.0 | 2026-02-05 | China Futures backtesting support, CNFutures market type |
| V2.1.1 | 2026-01-31 | AI Analysis overhaul, Global Market integration, Indicator Community enhancements |

---

*For questions or issues, please open a GitHub issue or contact the maintainers.*
