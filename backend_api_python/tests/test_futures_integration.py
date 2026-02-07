"""
Futures Strategy Integration Test
期货策略集成测试

This module tests the integration of all 4 modules:
1. CNFuturesDataSource - Data source module
2. FuturesCalculator - Calculator module
3. FuturesNotificationService - Notification module
4. FuturesStrategyExecutor - Strategy executor module

Author: Integration Test
Created: 2026-02-04
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ==================== Mock Data Source ====================

class MockCNFuturesDataSource:
    """
    Mock data source for testing.
    Simulates CNFuturesDataSource without needing akshare.
    """
    
    name = "cn_futures"
    
    PRODUCTS = {
        'IC': {'name': '中证500股指期货', 'multiplier': 200, 'margin_ratio': 0.12, 'tick_size': 0.2},
        'IM': {'name': '中证1000股指期货', 'multiplier': 200, 'margin_ratio': 0.12, 'tick_size': 0.2},
        'IF': {'name': '沪深300股指期货', 'multiplier': 300, 'margin_ratio': 0.10, 'tick_size': 0.2},
        'IH': {'name': '上证50股指期货', 'multiplier': 300, 'margin_ratio': 0.10, 'tick_size': 0.2},
    }
    
    def __init__(self):
        # Simulated prices for testing
        self._prices = {
            'IC0': 5500.0,
            'IM0': 6000.0,
            'IF0': 3800.0,
            'IH0': 2500.0,
        }
        self._base_prices = dict(self._prices)
    
    def set_price(self, symbol: str, price: float):
        """Set mock price for testing"""
        self._prices[symbol] = price
    
    def set_price_drop(self, symbol: str, drop_pct: float):
        """Set price to simulate a drop from base price"""
        base = self._base_prices.get(symbol, 5500.0)
        self._prices[symbol] = base * (1 + drop_pct)
    
    def get_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get mock K-line data"""
        base_price = self._prices.get(symbol, 5500.0)
        now = int(time.time())
        
        klines = []
        for i in range(limit):
            ts = now - (limit - i) * 60  # 1 minute intervals
            price = base_price + (i - limit // 2) * 0.5  # Some variation
            klines.append({
                "time": ts,
                "open": price,
                "high": price + 2,
                "low": price - 2,
                "close": price + 1,
                "volume": 1000 + i * 10
            })
        
        return klines
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get mock ticker data"""
        price = self._prices.get(symbol, 5500.0)
        return {
            "symbol": symbol,
            "last": price,
            "bid": price - 0.2,
            "ask": price + 0.2,
            "volume": 50000,
            "timestamp": int(time.time())
        }
    
    def get_main_contract_code(self, product: str) -> str:
        """Get mock main contract code"""
        now = datetime.now()
        month = now.month
        year = now.year % 100
        return f"{product}{year:02d}{month:02d}"
    
    def get_contract_info(self, symbol: str) -> Dict[str, Any]:
        """Get mock contract info"""
        product = symbol[:2].upper()
        info = self.PRODUCTS.get(product, self.PRODUCTS['IC'])
        return {
            "symbol": symbol,
            "product": product,
            "name": f"{info['name']}",
            "multiplier": info['multiplier'],
            "margin_ratio": info['margin_ratio'],
            "tick_size": info['tick_size'],
            "is_main": symbol.endswith('0')
        }


# ==================== Test Classes ====================

class TestFuturesIntegration:
    """
    Integration test suite for all futures modules.
    """
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def log(self, msg: str):
        """Log test message"""
        print(msg)
    
    def assert_true(self, condition: bool, msg: str):
        """Assert condition is true"""
        if condition:
            self.passed += 1
            self.log(f"  ✅ PASS: {msg}")
        else:
            self.failed += 1
            self.log(f"  ❌ FAIL: {msg}")
            self.results.append(f"FAIL: {msg}")
    
    def assert_equal(self, actual, expected, msg: str):
        """Assert values are equal"""
        if actual == expected:
            self.passed += 1
            self.log(f"  ✅ PASS: {msg}")
        else:
            self.failed += 1
            self.log(f"  ❌ FAIL: {msg} (expected={expected}, actual={actual})")
            self.results.append(f"FAIL: {msg}")
    
    def assert_close(self, actual: float, expected: float, tolerance: float, msg: str):
        """Assert float values are close"""
        if abs(actual - expected) <= tolerance:
            self.passed += 1
            self.log(f"  ✅ PASS: {msg}")
        else:
            self.failed += 1
            self.log(f"  ❌ FAIL: {msg} (expected≈{expected}, actual={actual})")
            self.results.append(f"FAIL: {msg}")

    # ==================== Module 1 Tests: Data Source ====================
    
    def test_data_source(self):
        """Test Module 1: CNFuturesDataSource"""
        self.log("\n" + "=" * 60)
        self.log("【模块1】数据源测试 (CNFuturesDataSource)")
        self.log("=" * 60)
        
        ds = MockCNFuturesDataSource()
        
        # Test 1.1: Get K-line data
        self.log("\n[1.1] 测试获取K线数据")
        klines = ds.get_kline("IC0", "1m", 100)
        self.assert_true(len(klines) == 100, "获取100条K线数据")
        self.assert_true(all('time' in k for k in klines), "K线包含时间字段")
        self.assert_true(all('close' in k for k in klines), "K线包含收盘价字段")
        
        # Test 1.2: Get ticker
        self.log("\n[1.2] 测试获取实时行情")
        ticker = ds.get_ticker("IC0")
        self.assert_true(ticker['last'] > 0, "获取有效的最新价")
        self.assert_true('bid' in ticker and 'ask' in ticker, "包含买卖价")
        
        # Test 1.3: Get main contract code
        self.log("\n[1.3] 测试获取主力合约代码")
        main_code = ds.get_main_contract_code("IC")
        self.assert_true(main_code.startswith("IC"), "主力合约代码以IC开头")
        
        # Test 1.4: Get contract info
        self.log("\n[1.4] 测试获取合约信息")
        info = ds.get_contract_info("IC0")
        self.assert_equal(info['multiplier'], 200, "IC合约乘数为200")
        self.assert_close(info['margin_ratio'], 0.12, 0.01, "IC保证金比例约12%")
        
        return True

    # ==================== Module 2 Tests: Calculator ====================
    
    def test_calculator(self):
        """Test Module 2: FuturesCalculator"""
        self.log("\n" + "=" * 60)
        self.log("【模块2】期货计算器测试 (FuturesCalculator)")
        self.log("=" * 60)
        
        from app.services.futures_calculator import (
            FuturesCalculator,
            FuturesMarginCalculator,
            FuturesFeeCalculator,
            SettlementPriceCalculator,
            PriceLimitChecker,
            PriceLimitStatus
        )
        
        calc = FuturesCalculator()
        
        # Test 2.1: Margin calculation
        self.log("\n[2.1] 测试保证金计算")
        margin = calc.margin.calculate("IC0", price=5500, quantity=1)
        expected_margin = 5500 * 200 * 0.12  # 132000
        self.assert_close(margin.margin_required, expected_margin, 1, f"IC保证金={expected_margin}")
        self.assert_equal(margin.multiplier, 200, "合约乘数=200")
        
        # Test 2.2: Fee calculation
        self.log("\n[2.2] 测试手续费计算")
        fee = calc.fee.calculate("IC0", price=5500, quantity=1, is_open=True)
        self.assert_true(fee.fee_amount > 0, "开仓手续费>0")
        
        fee_close_today = calc.fee.calculate("IC0", price=5500, quantity=1, is_open=False, is_close_today=True)
        fee_close_normal = calc.fee.calculate("IC0", price=5500, quantity=1, is_open=False, is_close_today=False)
        self.assert_true(fee_close_today.fee_amount > fee_close_normal.fee_amount, "平今手续费>普通平仓")
        
        # Test 2.3: Round trip fee
        self.log("\n[2.3] 测试往返手续费计算")
        rt_fee = calc.fee.calculate_round_trip("IC0", entry_price=5500, exit_price=5550, is_same_day=False)
        self.assert_true(rt_fee['total'] > 0, "往返手续费>0")
        self.assert_true(rt_fee['open'].fee_amount > 0, "开仓手续费>0")
        self.assert_true(rt_fee['close'].fee_amount > 0, "平仓手续费>0")
        
        # Test 2.4: Price limit check
        self.log("\n[2.4] 测试涨跌停检测")
        limit_info = calc.price_limit.check("IC0", current_price=6000, prev_settlement=5500)
        expected_upper = 5500 * 1.10  # 6050
        expected_lower = 5500 * 0.90  # 4950
        self.assert_close(limit_info.upper_limit, expected_upper, 1, f"涨停价≈{expected_upper}")
        self.assert_close(limit_info.lower_limit, expected_lower, 1, f"跌停价≈{expected_lower}")
        self.assert_equal(limit_info.status, PriceLimitStatus.NORMAL, "当前价格正常")
        
        # Test 2.5: VWAP calculation
        self.log("\n[2.5] 测试VWAP结算价计算")
        now = int(time.time())
        mock_bars = [
            {"time": now - 3600 + i * 60, "close": 5500 + i, "volume": 100 + i * 10}
            for i in range(60)
        ]
        vwap = calc.settlement.calculate_simple_vwap(mock_bars, last_n_minutes=30)
        self.assert_true(vwap > 0, "VWAP计算结果>0")
        
        # Test 2.6: Complete trade cost
        self.log("\n[2.6] 测试完整交易成本计算")
        cost = calc.calculate_trade_cost("IC0", entry_price=5500, exit_price=5550, quantity=1, is_same_day=False)
        self.assert_true("net_pnl" in cost, "包含净盈亏")
        self.assert_true("fee_total" in cost, "包含总手续费")
        expected_gross = (5550 - 5500) * 200  # 10000
        self.assert_equal(cost['gross_pnl'], expected_gross, f"毛盈亏={expected_gross}")
        
        # Test 2.7: Breakeven points
        self.log("\n[2.7] 测试保本点数计算")
        breakeven = calc.calculate_breakeven_points("IC0", entry_price=5500, quantity=1, is_same_day=False)
        self.assert_true(breakeven > 0, "保本点数>0")
        
        return True

    # ==================== Module 3 Tests: Notification ====================
    
    def test_notification(self):
        """Test Module 3: FuturesNotificationService"""
        self.log("\n" + "=" * 60)
        self.log("【模块3】通知模板测试 (FuturesNotificationService)")
        self.log("=" * 60)
        
        from app.services.futures_notification import (
            FuturesNotificationService,
            FuturesNotificationTemplates,
            FuturesSignalData,
            FuturesSignalType
        )
        
        templates = FuturesNotificationTemplates()
        
        # Test 3.1: Buy signal template
        self.log("\n[3.1] 测试买入信号模板")
        buy_data = FuturesSignalData(
            signal_type=FuturesSignalType.BUY,
            symbol="IC0",
            current_price=5450,
            base_price=5500,
            drop_pct=-0.0091,
            timestamp=datetime.now()
        )
        rendered = templates.render_buy_signal(buy_data)
        self.assert_true("title" in rendered, "包含标题")
        self.assert_true("plain" in rendered, "包含纯文本")
        self.assert_true("html" in rendered, "包含HTML")
        self.assert_true("telegram" in rendered, "包含Telegram格式")
        self.assert_true("5450" in rendered["plain"], "包含当前价格")
        self.assert_true("买入" in rendered["title"], "标题包含'买入'")
        
        # Test 3.2: Sell signal template
        self.log("\n[3.2] 测试卖出信号模板")
        sell_data = FuturesSignalData(
            signal_type=FuturesSignalType.SELL,
            symbol="IC0",
            current_price=5520,
            base_price=5500,
            drop_pct=0.0036,
            timestamp=datetime.now(),
            entry_price=5450,
            profit=14000,
            profit_pct=0.0128
        )
        rendered = templates.render_sell_signal(sell_data)
        self.assert_true("14000" in rendered["plain"], "包含收益金额")
        self.assert_true("卖出" in rendered["title"], "标题包含'卖出'")
        
        # Test 3.3: Price alert template
        self.log("\n[3.3] 测试价格预警模板")
        alert_data = FuturesSignalData(
            signal_type=FuturesSignalType.PRICE_ALERT,
            symbol="IC0",
            current_price=5455,
            base_price=5500,
            drop_pct=-0.0082,
            timestamp=datetime.now()
        )
        rendered = templates.render_price_alert(alert_data)
        self.assert_true("预警" in rendered["title"], "标题包含'预警'")
        
        # Test 3.4: PnL report template
        self.log("\n[3.4] 测试盈亏报告模板")
        report_data = FuturesSignalData(
            signal_type=FuturesSignalType.PNL_REPORT,
            symbol="IC0",
            current_price=5520,
            base_price=5500,
            drop_pct=0.0036,
            timestamp=datetime.now(),
            entry_price=5450,
            profit=14000,
            profit_pct=0.0128,
            monthly_pnl=42000
        )
        rendered = templates.render_pnl_report(report_data)
        self.assert_true("42000" in rendered["plain"], "包含月度累计盈亏")
        self.assert_true("报告" in rendered["title"], "标题包含'报告'")
        
        return True

    # ==================== Module 4 Tests: Strategy Executor ====================
    
    def test_strategy_executor(self):
        """Test Module 4: FuturesStrategyExecutor"""
        self.log("\n" + "=" * 60)
        self.log("【模块4】策略执行器测试 (FuturesStrategyExecutor)")
        self.log("=" * 60)
        
        from app.services.futures_strategy_executor import (
            FuturesStrategyExecutor,
            StrategyStatus,
            StrategyState
        )
        
        executor = FuturesStrategyExecutor()
        
        # Test 4.1: Initial state
        self.log("\n[4.1] 测试初始状态")
        state = executor.get_state("IC0")
        self.assert_equal(state.status, StrategyStatus.IDLE, "初始状态为IDLE")
        self.assert_equal(state.position_quantity, 0, "初始持仓为0")
        
        # Test 4.2: Drop percentage calculation
        self.log("\n[4.2] 测试跌幅计算")
        drop = executor._calculate_drop_pct(5445, 5500)
        self.assert_close(drop, -0.01, 0.001, "跌幅约-1%")
        
        # Test 4.3: Status summary
        self.log("\n[4.3] 测试状态摘要")
        summary = executor.get_status_summary()
        self.assert_true("contracts" in summary, "包含合约状态")
        self.assert_true("IC0" in summary["contracts"], "包含IC0状态")
        
        # Test 4.4: Reset functionality
        self.log("\n[4.4] 测试重置功能")
        executor.states["IC0"].position_quantity = 2
        executor.states["IC0"].entry_price = 5500
        executor.reset("IC0")
        self.assert_equal(executor.states["IC0"].position_quantity, 0, "重置后持仓为0")
        self.assert_true(executor.states["IC0"].entry_price is None, "重置后买入价为空")
        
        return True

    # ==================== Integration Tests ====================
    
    def test_full_integration(self):
        """Test full integration of all modules"""
        self.log("\n" + "=" * 60)
        self.log("【集成测试】全模块协同工作")
        self.log("=" * 60)
        
        from app.services.futures_calculator import FuturesCalculator
        from app.services.futures_notification import FuturesNotificationService
        from app.services.futures_strategy_executor import FuturesStrategyExecutor, StrategyStatus
        
        # Initialize all modules
        self.log("\n[集成1] 初始化所有模块")
        data_source = MockCNFuturesDataSource()
        calculator = FuturesCalculator()
        notifier = FuturesNotificationService()
        executor = FuturesStrategyExecutor()
        
        # Inject dependencies
        executor.initialize(data_source, calculator, notifier)
        self.assert_true(executor.data_source is not None, "数据源已注入")
        self.assert_true(executor.calculator is not None, "计算器已注入")
        self.assert_true(executor.notifier is not None, "通知服务已注入")
        
        # Test 2: Data flow from data source to calculator
        self.log("\n[集成2] 数据源→计算器数据流")
        ticker = data_source.get_ticker("IC0")
        price = ticker['last']
        margin = calculator.margin.calculate("IC0", price=price, quantity=1)
        self.assert_true(margin.margin_required > 0, "基于实时价格计算保证金")
        
        # Test 3: Simulate buy signal scenario
        self.log("\n[集成3] 模拟买入信号场景")
        
        # Set price to trigger buy signal (drop > 1%)
        data_source.set_price_drop("IC0", -0.012)  # -1.2% drop
        
        # Manually set base price and trigger monitoring
        state = executor.get_state("IC0")
        state.base_price = 5500.0
        state.status = StrategyStatus.MONITORING
        
        # Now check signal (we need to patch _is_monitoring_time for test)
        original_is_monitoring = executor._is_monitoring_time
        executor._is_monitoring_time = lambda: True
        
        signal = executor.check_signal("IC0")
        executor._is_monitoring_time = original_is_monitoring
        
        if signal:
            self.assert_equal(signal['signal_type'], 'buy', "触发买入信号")
            self.assert_true(abs(signal['drop_pct']) >= 0.01, "跌幅超过阈值")
            
            # Test 4: Calculate trade cost for the signal
            self.log("\n[集成4] 计算交易成本")
            cost = calculator.calculate_trade_cost(
                symbol="IC0",
                entry_price=signal['price'],
                exit_price=signal['price'] + 50,  # Assume +50 points profit
                quantity=1,
                is_same_day=False
            )
            self.assert_true(cost['net_pnl'] > 0, "预期盈利场景")
            self.log(f"    预期毛盈亏: {cost['gross_pnl']:.2f}元")
            self.log(f"    手续费: {cost['fee_total']:.2f}元")
            self.log(f"    净盈亏: {cost['net_pnl']:.2f}元")
        else:
            self.assert_true(False, "应该触发买入信号")
        
        # Test 5: Execute signal (mock notification)
        self.log("\n[集成5] 执行信号并发送通知")
        
        # Mock the notification to avoid actual sending
        original_send = notifier.send_buy_signal
        notifier.send_buy_signal = lambda **kwargs: {"mock": {"ok": True}}
        
        if signal:
            result = executor.execute_signal(
                signal=signal,
                strategy_id=1,
                strategy_name="测试策略",
                notification_config={"channels": ["browser"]}
            )
            self.assert_true(result['success'], "信号执行成功")
            self.assert_equal(result['action'], 'buy', "执行买入动作")
            self.assert_true(executor.get_state("IC0").position_quantity > 0, "持仓已更新")
        
        notifier.send_buy_signal = original_send
        
        # Test 6: Verify state after execution
        self.log("\n[集成6] 验证执行后状态")
        state = executor.get_state("IC0")
        self.assert_equal(state.status, StrategyStatus.POSITION_OPEN, "状态变为持仓中")
        self.assert_true(state.entry_price is not None, "买入价已记录")
        self.assert_true(state.entry_time is not None, "买入时间已记录")
        
        return True

    # ==================== Run All Tests ====================
    
    def run_all_tests(self):
        """Run all test suites"""
        print("\n" + "=" * 60)
        print("     期货策略集成测试 - QuantDinger")
        print("     Futures Strategy Integration Test")
        print("=" * 60)
        print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Run each test module
            self.test_data_source()
            self.test_calculator()
            self.test_notification()
            self.test_strategy_executor()
            self.test_full_integration()
            
        except Exception as e:
            self.failed += 1
            self.log(f"\n❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()
        
        # Print summary
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        total = self.passed + self.failed
        print(f"  总测试数: {total}")
        print(f"  ✅ 通过: {self.passed}")
        print(f"  ❌ 失败: {self.failed}")
        
        if self.failed == 0:
            print("\n🎉 所有测试通过！All tests passed!")
        else:
            print(f"\n⚠️ 有 {self.failed} 个测试失败:")
            for r in self.results:
                print(f"  - {r}")
        
        print("=" * 60)
        
        return self.failed == 0


# ==================== Main Entry ====================

def run_integration_tests():
    """Run all integration tests"""
    tester = TestFuturesIntegration()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = run_integration_tests()
    sys.exit(exit_code)
