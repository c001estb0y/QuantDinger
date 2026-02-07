"""
Simple Futures Strategy Integration Test Runner
独立运行的期货策略集成测试
"""
import sys
import os
from datetime import datetime
import time

# Set up path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("     期货策略集成测试 - QuantDinger")
print("=" * 60)
print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

passed = 0
failed = 0

def log_pass(msg):
    global passed
    passed += 1
    print(f"  ✅ PASS: {msg}")

def log_fail(msg):
    global failed
    failed += 1
    print(f"  ❌ FAIL: {msg}")

# ==================== Module 2: Calculator Tests ====================
print("\n" + "=" * 60)
print("【模块2】期货计算器测试 (FuturesCalculator)")
print("=" * 60)

try:
    from app.services.futures_calculator import (
        FuturesCalculator,
        FuturesMarginCalculator,
        FuturesFeeCalculator,
        PriceLimitStatus
    )
    
    calc = FuturesCalculator()
    
    # Test 2.1: Margin calculation
    print("\n[2.1] 测试保证金计算")
    margin = calc.margin.calculate("IC0", price=5500, quantity=1)
    expected_margin = 5500 * 200 * 0.12  # 132000
    if abs(margin.margin_required - expected_margin) < 1:
        log_pass(f"IC保证金={expected_margin}")
    else:
        log_fail(f"IC保证金计算错误: expected={expected_margin}, actual={margin.margin_required}")
    
    if margin.multiplier == 200:
        log_pass("合约乘数=200")
    else:
        log_fail(f"合约乘数错误: {margin.multiplier}")
    
    # Test 2.2: Fee calculation
    print("\n[2.2] 测试手续费计算")
    fee = calc.fee.calculate("IC0", price=5500, quantity=1, is_open=True)
    if fee.fee_amount > 0:
        log_pass("开仓手续费>0")
    else:
        log_fail("开仓手续费应>0")
    
    fee_close_today = calc.fee.calculate("IC0", price=5500, quantity=1, is_open=False, is_close_today=True)
    fee_close_normal = calc.fee.calculate("IC0", price=5500, quantity=1, is_open=False, is_close_today=False)
    if fee_close_today.fee_amount > fee_close_normal.fee_amount:
        log_pass("平今手续费>普通平仓")
    else:
        log_fail("平今手续费应该>普通平仓")
    
    # Test 2.3: Price limit check
    print("\n[2.3] 测试涨跌停检测")
    limit_info = calc.price_limit.check("IC0", current_price=6000, prev_settlement=5500)
    expected_upper = 5500 * 1.10  # 6050
    expected_lower = 5500 * 0.90  # 4950
    if abs(limit_info.upper_limit - expected_upper) < 1:
        log_pass(f"涨停价≈{expected_upper}")
    else:
        log_fail(f"涨停价错误: {limit_info.upper_limit}")
    
    if abs(limit_info.lower_limit - expected_lower) < 1:
        log_pass(f"跌停价≈{expected_lower}")
    else:
        log_fail(f"跌停价错误: {limit_info.lower_limit}")
    
    # Test 2.4: Complete trade cost
    print("\n[2.4] 测试完整交易成本计算")
    cost = calc.calculate_trade_cost("IC0", entry_price=5500, exit_price=5550, quantity=1, is_same_day=False)
    expected_gross = (5550 - 5500) * 200  # 10000
    if cost['gross_pnl'] == expected_gross:
        log_pass(f"毛盈亏={expected_gross}")
    else:
        log_fail(f"毛盈亏错误: {cost['gross_pnl']}")
    
    if "net_pnl" in cost:
        log_pass("包含净盈亏字段")
    else:
        log_fail("缺少净盈亏字段")
    
    print(f"\n    交易成本详情:")
    print(f"    - 保证金: {cost['margin_required']:.2f}元")
    print(f"    - 开仓手续费: {cost['fee_open']:.2f}元")
    print(f"    - 平仓手续费: {cost['fee_close']:.2f}元")
    print(f"    - 毛盈亏: {cost['gross_pnl']:.2f}元")
    print(f"    - 净盈亏: {cost['net_pnl']:.2f}元")

except Exception as e:
    log_fail(f"计算器模块测试异常: {e}")
    import traceback
    traceback.print_exc()

# ==================== Module 3: Notification Tests ====================
print("\n" + "=" * 60)
print("【模块3】通知模板测试 (FuturesNotificationService)")
print("=" * 60)

try:
    from app.services.futures_notification import (
        FuturesNotificationTemplates,
        FuturesSignalData,
        FuturesSignalType
    )
    
    templates = FuturesNotificationTemplates()
    
    # Test 3.1: Buy signal template
    print("\n[3.1] 测试买入信号模板")
    buy_data = FuturesSignalData(
        signal_type=FuturesSignalType.BUY,
        symbol="IC0",
        current_price=5450,
        base_price=5500,
        drop_pct=-0.0091,
        timestamp=datetime.now()
    )
    rendered = templates.render_buy_signal(buy_data)
    
    if "title" in rendered:
        log_pass("包含标题")
    else:
        log_fail("缺少标题")
    
    if "5450" in rendered.get("plain", ""):
        log_pass("包含当前价格")
    else:
        log_fail("缺少当前价格")
    
    if "买入" in rendered.get("title", ""):
        log_pass("标题包含'买入'")
    else:
        log_fail("标题应包含'买入'")
    
    # Test 3.2: Sell signal template
    print("\n[3.2] 测试卖出信号模板")
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
    
    if "14000" in rendered.get("plain", ""):
        log_pass("包含收益金额")
    else:
        log_fail("缺少收益金额")
    
    if "卖出" in rendered.get("title", ""):
        log_pass("标题包含'卖出'")
    else:
        log_fail("标题应包含'卖出'")

except Exception as e:
    log_fail(f"通知模块测试异常: {e}")
    import traceback
    traceback.print_exc()

# ==================== Module 4: Strategy Executor Tests ====================
print("\n" + "=" * 60)
print("【模块4】策略执行器测试 (FuturesStrategyExecutor)")
print("=" * 60)

try:
    from app.services.futures_strategy_executor import (
        FuturesStrategyExecutor,
        StrategyStatus
    )
    
    executor = FuturesStrategyExecutor()
    
    # Test 4.1: Initial state
    print("\n[4.1] 测试初始状态")
    state = executor.get_state("IC0")
    if state.status == StrategyStatus.IDLE:
        log_pass("初始状态为IDLE")
    else:
        log_fail(f"初始状态错误: {state.status}")
    
    if state.position_quantity == 0:
        log_pass("初始持仓为0")
    else:
        log_fail(f"初始持仓错误: {state.position_quantity}")
    
    # Test 4.2: Drop percentage calculation
    print("\n[4.2] 测试跌幅计算")
    drop = executor._calculate_drop_pct(5445, 5500)
    if abs(drop - (-0.01)) < 0.001:
        log_pass("跌幅约-1%")
    else:
        log_fail(f"跌幅计算错误: {drop}")
    
    # Test 4.3: Status summary
    print("\n[4.3] 测试状态摘要")
    summary = executor.get_status_summary()
    if "contracts" in summary:
        log_pass("包含合约状态")
    else:
        log_fail("缺少合约状态")
    
    if "IC0" in summary.get("contracts", {}):
        log_pass("包含IC0状态")
    else:
        log_fail("缺少IC0状态")
    
    # Test 4.4: Reset functionality
    print("\n[4.4] 测试重置功能")
    executor.states["IC0"].position_quantity = 2
    executor.states["IC0"].entry_price = 5500
    executor.reset("IC0")
    if executor.states["IC0"].position_quantity == 0:
        log_pass("重置后持仓为0")
    else:
        log_fail(f"重置后持仓错误: {executor.states['IC0'].position_quantity}")

except Exception as e:
    log_fail(f"策略执行器模块测试异常: {e}")
    import traceback
    traceback.print_exc()

# ==================== Integration Test ====================
print("\n" + "=" * 60)
print("【集成测试】全模块协同工作")
print("=" * 60)

try:
    from app.services.futures_calculator import FuturesCalculator
    from app.services.futures_notification import FuturesNotificationService
    from app.services.futures_strategy_executor import FuturesStrategyExecutor, StrategyStatus
    
    print("\n[集成1] 初始化所有模块")
    calculator = FuturesCalculator()
    notifier = FuturesNotificationService()
    executor = FuturesStrategyExecutor()
    
    log_pass("所有模块初始化成功")
    
    # Test: Calculate trade scenario
    print("\n[集成2] 模拟完整交易场景")
    
    # Scenario: Buy IC0 at 5450, sell at 5520
    entry_price = 5450
    exit_price = 5520
    
    print(f"    场景: IC0期货 买入@{entry_price}, 卖出@{exit_price}, 1手")
    
    # Calculate margin
    margin = calculator.margin.calculate("IC0", price=entry_price, quantity=1)
    print(f"    所需保证金: {margin.margin_required:.2f}元")
    
    # Calculate trade cost
    cost = calculator.calculate_trade_cost(
        symbol="IC0",
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=1,
        is_same_day=False
    )
    print(f"    毛盈亏: {cost['gross_pnl']:.2f}元")
    print(f"    总手续费: {cost['fee_total']:.2f}元")
    print(f"    净盈亏: {cost['net_pnl']:.2f}元")
    print(f"    收益率: {cost['net_pnl']/margin.margin_required*100:.2f}%")
    
    if cost['net_pnl'] > 0:
        log_pass("盈利场景计算正确")
    else:
        log_fail("盈利场景应该有正收益")
    
    # Test: Strategy state management
    print("\n[集成3] 策略状态管理")
    executor.states["IC0"].base_price = 5500
    executor.states["IC0"].current_price = 5450
    executor.states["IC0"].entry_price = 5450
    executor.states["IC0"].position_quantity = 1
    executor.states["IC0"].status = StrategyStatus.POSITION_OPEN
    
    state = executor.get_state("IC0")
    if state.status == StrategyStatus.POSITION_OPEN:
        log_pass("持仓状态设置正确")
    else:
        log_fail(f"状态错误: {state.status}")
    
    summary = executor.get_status_summary()
    print(f"    策略状态: {summary['contracts']['IC0']}")
    log_pass("状态摘要生成成功")

except Exception as e:
    log_fail(f"集成测试异常: {e}")
    import traceback
    traceback.print_exc()

# ==================== Test Summary ====================
print("\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
total = passed + failed
print(f"  总测试数: {total}")
print(f"  ✅ 通过: {passed}")
print(f"  ❌ 失败: {failed}")

if failed == 0:
    print("\n🎉 所有测试通过！All tests passed!")
else:
    print(f"\n⚠️ 有 {failed} 个测试失败")

print("=" * 60)
