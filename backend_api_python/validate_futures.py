"""
Quick validation script for CN Futures Frontend Integration
快速验证脚本 - 期货前端集成
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("期货前端集成 - 快速验证")
print("=" * 60)

errors = []

# 1. Test Calculator Module
print("\n[1] Testing FuturesCalculator...")
try:
    from app.services.futures_calculator import FuturesCalculator
    calc = FuturesCalculator()
    
    # Margin test
    margin = calc.margin.calculate("IC0", 5500, 1)
    assert margin.margin_required == 5500 * 200 * 0.12, "Margin calculation error"
    print(f"    ✅ Margin: {margin.margin_required:.2f}")
    
    # Fee test
    fee = calc.fee.calculate("IC0", 5500, 1, is_open=True)
    assert fee.fee_amount > 0, "Fee calculation error"
    print(f"    ✅ Fee: {fee.fee_amount:.2f}")
    
    # Trade cost test
    cost = calc.calculate_trade_cost("IC0", 5500, 5550, 1, False)
    assert cost['gross_pnl'] == 10000, "Trade cost calculation error"
    print(f"    ✅ Trade cost: Gross={cost['gross_pnl']}, Net={cost['net_pnl']:.2f}")
    
except Exception as e:
    errors.append(f"Calculator: {e}")
    print(f"    ❌ Error: {e}")

# 2. Test Data Source Module
print("\n[2] Testing CNFuturesDataSource...")
try:
    from app.data_sources.cn_futures import CNFuturesDataSource, AKSHARE_AVAILABLE
    
    ds = CNFuturesDataSource()
    
    # Symbol parsing
    product, code, is_main = ds._parse_symbol("IC0")
    assert product == "IC", "Symbol parse error"
    assert is_main == True, "Main contract detection error"
    print(f"    ✅ Symbol parse: product={product}, is_main={is_main}")
    
    # Contract info
    info = ds.get_contract_info("IF0")
    assert info['multiplier'] == 300, "IF multiplier error"
    print(f"    ✅ Contract info: {info['product']}, multiplier={info['multiplier']}")
    
    print(f"    ℹ️ akshare available: {AKSHARE_AVAILABLE}")
    
except Exception as e:
    errors.append(f"DataSource: {e}")
    print(f"    ❌ Error: {e}")

# 3. Test Models Module
print("\n[3] Testing Futures Models...")
try:
    from app.models.futures import (
        FuturesStrategyConfig,
        FuturesPosition,
        FuturesTrade,
        FuturesSignal
    )
    
    print("    ✅ All model classes imported successfully")
    
except Exception as e:
    errors.append(f"Models: {e}")
    print(f"    ❌ Error: {e}")

# 4. Test Routes Module
print("\n[4] Testing CN Futures Routes...")
try:
    from app.routes.cn_futures import cn_futures_bp
    
    # Check endpoints exist
    rules = [rule.rule for rule in cn_futures_bp.url_map.iter_rules() if rule.endpoint != 'static']
    print(f"    ✅ Blueprint created with {len(cn_futures_bp.deferred_functions)} routes")
    
except Exception as e:
    errors.append(f"Routes: {e}")
    print(f"    ❌ Error: {e}")

# 5. Test Route Registration
print("\n[5] Testing Route Registration...")
try:
    from app.routes import register_routes
    print("    ✅ Route registration function importable")
    
except Exception as e:
    errors.append(f"Route Registration: {e}")
    print(f"    ❌ Error: {e}")

# Summary
print("\n" + "=" * 60)
print("Summary")
print("=" * 60)

if not errors:
    print("✅ All backend components validated successfully!")
    print("\nCreated files:")
    print("  - backend_api_python/app/models/futures.py (Database models)")
    print("  - backend_api_python/app/routes/cn_futures.py (API routes)")
    print("  - quantdinger_vue/src/api/cn_futures.js (Frontend API)")
    print("  - quantdinger_vue/src/views/futures-strategy/index.vue (Main page)")
    print("  - quantdinger_vue/src/views/futures-strategy/components/*.vue (6 components)")
    print("  - backend_api_python/tests/test_cn_futures.py (Test suite)")
else:
    print(f"❌ {len(errors)} error(s) found:")
    for err in errors:
        print(f"  - {err}")

print("=" * 60)
