"""
Run all futures module tests and write results to file
"""
import sys
import os

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Output file
output_file = "test_results_full.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    original_stdout = sys.stdout
    sys.stdout = f
    
    print("=" * 60)
    print("期货策略模块集成测试")
    print("=" * 60)
    
    # Test 1: Calculator
    print("\n【测试1】期货计算器模块")
    print("-" * 40)
    try:
        from app.services.futures_calculator import test_futures_calculator
        test_futures_calculator()
        print("✅ 计算器模块测试通过")
    except Exception as e:
        print(f"❌ 计算器模块测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Notification
    print("\n【测试2】通知模板模块")
    print("-" * 40)
    try:
        from app.services.futures_notification import test_futures_notification
        test_futures_notification()
        print("✅ 通知模板模块测试通过")
    except Exception as e:
        print(f"❌ 通知模板模块测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Strategy Executor
    print("\n【测试3】策略执行器模块")
    print("-" * 40)
    try:
        from app.services.futures_strategy_executor import test_futures_strategy_executor
        test_futures_strategy_executor()
        print("✅ 策略执行器模块测试通过")
    except Exception as e:
        print(f"❌ 策略执行器模块测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Integration
    print("\n【测试4】集成测试")
    print("-" * 40)
    try:
        from app.services.futures_calculator import FuturesCalculator
        from app.services.futures_notification import FuturesNotificationService, FuturesSignalData, FuturesSignalType
        from app.services.futures_strategy_executor import FuturesStrategyExecutor, StrategyStatus
        from datetime import datetime
        
        # Initialize all modules
        calc = FuturesCalculator()
        notifier = FuturesNotificationService()
        executor = FuturesStrategyExecutor()
        
        print("模块初始化成功")
        
        # Test trade calculation
        cost = calc.calculate_trade_cost("IC0", 5450, 5520, 1, False)
        print(f"交易成本计算: 毛盈亏={cost['gross_pnl']}, 净盈亏={cost['net_pnl']:.2f}")
        
        # Test notification template
        data = FuturesSignalData(
            signal_type=FuturesSignalType.BUY,
            symbol="IC0",
            current_price=5450,
            base_price=5500,
            drop_pct=-0.0091,
            timestamp=datetime.now()
        )
        rendered = notifier.templates.render_buy_signal(data)
        print(f"通知模板渲染: title={rendered['title'][:30]}...")
        
        # Test executor state
        state = executor.get_state("IC0")
        print(f"策略状态: {state.status.value}")
        
        print("✅ 集成测试通过")
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    
    sys.stdout = original_stdout

print(f"测试结果已写入: {output_file}")
print("正在读取结果...")

# Read and print results
with open(output_file, 'r', encoding='utf-8') as f:
    print(f.read())
