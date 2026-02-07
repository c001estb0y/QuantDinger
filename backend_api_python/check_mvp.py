"""
MVP策略完成度检查脚本
检查所有4个模块是否可以正常运行
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_modules():
    results = []
    all_ok = True
    
    # 检查模块1: 数据源
    print("检查模块1: 数据源 (CNFuturesDataSource)...")
    try:
        from app.data_sources.cn_futures import CNFuturesDataSource
        ds = CNFuturesDataSource()
        info = ds.get_contract_info("IC0")
        results.append(f"✅ 模块1 数据源: OK (multiplier={info['multiplier']})")
    except Exception as e:
        results.append(f"❌ 模块1 数据源: FAIL ({e})")
        all_ok = False
    
    # 检查模块2: 计算器
    print("检查模块2: 计算器 (FuturesCalculator)...")
    try:
        from app.services.futures_calculator import FuturesCalculator
        calc = FuturesCalculator()
        margin = calc.margin.calculate("IC0", price=5500, quantity=1)
        fee = calc.fee.calculate("IC0", price=5500, quantity=1, is_open=True)
        cost = calc.calculate_trade_cost("IC0", 5500, 5550, 1, False)
        results.append(f"✅ 模块2 计算器: OK (保证金={margin.margin_required}, 手续费={fee.fee_amount:.2f})")
    except Exception as e:
        results.append(f"❌ 模块2 计算器: FAIL ({e})")
        all_ok = False
    
    # 检查模块3: 通知
    print("检查模块3: 通知模板 (FuturesNotificationService)...")
    try:
        from app.services.futures_notification import (
            FuturesNotificationService, 
            FuturesSignalData, 
            FuturesSignalType
        )
        from datetime import datetime
        service = FuturesNotificationService()
        data = FuturesSignalData(
            signal_type=FuturesSignalType.BUY,
            symbol="IC0",
            current_price=5450,
            base_price=5500,
            drop_pct=-0.0091,
            timestamp=datetime.now()
        )
        rendered = service.templates.render_buy_signal(data)
        results.append(f"✅ 模块3 通知模板: OK (title={rendered['title'][:20]}...)")
    except Exception as e:
        results.append(f"❌ 模块3 通知模板: FAIL ({e})")
        all_ok = False
    
    # 检查模块4: 策略执行器
    print("检查模块4: 策略执行器 (FuturesStrategyExecutor)...")
    try:
        from app.services.futures_strategy_executor import FuturesStrategyExecutor, StrategyStatus
        executor = FuturesStrategyExecutor()
        state = executor.get_state("IC0")
        results.append(f"✅ 模块4 策略执行器: OK (status={state.status.value})")
    except Exception as e:
        results.append(f"❌ 模块4 策略执行器: FAIL ({e})")
        all_ok = False
    
    # 检查集成
    print("检查模块集成...")
    try:
        from app.data_sources.cn_futures import CNFuturesDataSource
        from app.services.futures_calculator import FuturesCalculator
        from app.services.futures_notification import FuturesNotificationService
        from app.services.futures_strategy_executor import FuturesStrategyExecutor
        
        ds = CNFuturesDataSource()
        calc = FuturesCalculator()
        notifier = FuturesNotificationService()
        executor = FuturesStrategyExecutor()
        executor.initialize(ds, calc, notifier)
        
        results.append("✅ 模块集成: OK (所有模块已成功注入)")
    except Exception as e:
        results.append(f"❌ 模块集成: FAIL ({e})")
        all_ok = False
    
    return results, all_ok

if __name__ == "__main__":
    print("=" * 60)
    print("       MVP 策略完成度检查")
    print("=" * 60)
    print()
    
    results, all_ok = check_modules()
    
    print()
    print("=" * 60)
    print("检查结果:")
    print("=" * 60)
    for r in results:
        print(r)
    
    print()
    if all_ok:
        print("🎉 恭喜！所有模块检查通过，策略可以运行！")
        print()
        print("运行策略的方法:")
        print("  1. 启动后端服务: python app/main.py")
        print("  2. 或直接运行执行器测试:")
        print("     python app/services/futures_strategy_executor.py")
    else:
        print("⚠️ 部分模块检查失败，请修复后再运行策略")
    
    print("=" * 60)
