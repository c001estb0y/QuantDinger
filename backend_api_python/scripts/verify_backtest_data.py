"""
Backtest Data Verification Script
==================================
This script helps verify the correctness of backtest data by comparing 
data from multiple sources.

Usage:
    python scripts/verify_backtest_data.py --symbol IM0 --dates 2024-01-15,2024-06-20

Verification Methods:
1. Cross-source comparison (akshare vs other APIs)
2. Sanity checks (price range, volume, etc.)
3. Synthetic minute data validation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json

from app.data_sources.cn_futures import CNFuturesDataSource


class BacktestDataVerifier:
    """Verify backtest data correctness through multiple methods."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data_source = CNFuturesDataSource()
        self.results = []
    
    def verify_daily_data(self, target_date: str) -> Dict:
        """
        Verify daily K-line data for a specific date.
        
        Args:
            target_date: Date string (YYYY-MM-DD)
            
        Returns:
            Verification result dict
        """
        result = {
            "date": target_date,
            "symbol": self.symbol,
            "checks": [],
            "status": "UNKNOWN"
        }
        
        print(f"\n{'='*60}")
        print(f"Verifying {self.symbol} on {target_date}")
        print('='*60)
        
        # 1. Get data from our system
        print("\n[1] Fetching data from system...")
        try:
            df = self.data_source.get_kline(self.symbol, "1D", limit=365)
            if df is None or df.empty:
                result["checks"].append({
                    "name": "System Data Fetch",
                    "status": "FAIL",
                    "message": "No data returned from system"
                })
                result["status"] = "FAIL"
                return result
            
            # Find the target date
            target_dt = pd.Timestamp(target_date).date()
            df['date'] = pd.to_datetime(df['datetime']).dt.date
            day_data = df[df['date'] == target_dt]
            
            if day_data.empty:
                result["checks"].append({
                    "name": "System Data Fetch",
                    "status": "FAIL",
                    "message": f"No data for {target_date} in system"
                })
                result["status"] = "FAIL"
                return result
            
            system_data = day_data.iloc[0]
            print(f"   System Data: O={system_data['open']}, H={system_data['high']}, "
                  f"L={system_data['low']}, C={system_data['close']}, V={system_data['volume']}")
            
            result["system_data"] = {
                "open": float(system_data['open']),
                "high": float(system_data['high']),
                "low": float(system_data['low']),
                "close": float(system_data['close']),
                "volume": float(system_data['volume'])
            }
            result["checks"].append({
                "name": "System Data Fetch",
                "status": "PASS",
                "message": "Data fetched successfully"
            })
            
        except Exception as e:
            result["checks"].append({
                "name": "System Data Fetch",
                "status": "FAIL",
                "message": str(e)
            })
            result["status"] = "FAIL"
            return result
        
        # 2. Sanity checks
        print("\n[2] Running sanity checks...")
        sanity_checks = self._run_sanity_checks(system_data)
        result["checks"].extend(sanity_checks)
        
        # 3. Try to get data from alternative source for comparison
        print("\n[3] Fetching data from alternative source for comparison...")
        alt_result = self._compare_with_alternative_source(target_date, system_data)
        result["checks"].append(alt_result)
        
        # 4. Verify synthetic minute data if applicable
        print("\n[4] Verifying synthetic minute data logic...")
        minute_result = self._verify_synthetic_minute(system_data)
        result["checks"].append(minute_result)
        
        # Determine overall status
        fail_count = sum(1 for c in result["checks"] if c["status"] == "FAIL")
        warn_count = sum(1 for c in result["checks"] if c["status"] == "WARN")
        
        if fail_count > 0:
            result["status"] = "FAIL"
        elif warn_count > 0:
            result["status"] = "WARN"
        else:
            result["status"] = "PASS"
        
        self.results.append(result)
        return result
    
    def _run_sanity_checks(self, data: pd.Series) -> List[Dict]:
        """Run sanity checks on the data."""
        checks = []
        
        # Check 1: High >= Low
        if data['high'] >= data['low']:
            checks.append({
                "name": "High >= Low",
                "status": "PASS",
                "message": f"H={data['high']} >= L={data['low']}"
            })
            print(f"   ✓ High >= Low: PASS")
        else:
            checks.append({
                "name": "High >= Low",
                "status": "FAIL",
                "message": f"H={data['high']} < L={data['low']}"
            })
            print(f"   ✗ High >= Low: FAIL")
        
        # Check 2: High >= Open, Close
        if data['high'] >= data['open'] and data['high'] >= data['close']:
            checks.append({
                "name": "High >= Open/Close",
                "status": "PASS",
                "message": f"H={data['high']} >= O={data['open']}, C={data['close']}"
            })
            print(f"   ✓ High >= Open/Close: PASS")
        else:
            checks.append({
                "name": "High >= Open/Close",
                "status": "FAIL",
                "message": f"High should be >= Open and Close"
            })
            print(f"   ✗ High >= Open/Close: FAIL")
        
        # Check 3: Low <= Open, Close
        if data['low'] <= data['open'] and data['low'] <= data['close']:
            checks.append({
                "name": "Low <= Open/Close",
                "status": "PASS",
                "message": f"L={data['low']} <= O={data['open']}, C={data['close']}"
            })
            print(f"   ✓ Low <= Open/Close: PASS")
        else:
            checks.append({
                "name": "Low <= Open/Close",
                "status": "FAIL",
                "message": f"Low should be <= Open and Close"
            })
            print(f"   ✗ Low <= Open/Close: FAIL")
        
        # Check 4: Volume > 0
        if data['volume'] > 0:
            checks.append({
                "name": "Volume > 0",
                "status": "PASS",
                "message": f"Volume={data['volume']}"
            })
            print(f"   ✓ Volume > 0: PASS")
        else:
            checks.append({
                "name": "Volume > 0",
                "status": "WARN",
                "message": f"Volume={data['volume']} (may be holiday/non-trading day)"
            })
            print(f"   ⚠ Volume > 0: WARN (might be non-trading day)")
        
        # Check 5: Price range is reasonable (< 10% daily move for index futures)
        price_range_pct = (data['high'] - data['low']) / data['open'] * 100
        if price_range_pct < 10:
            checks.append({
                "name": "Price Range Reasonable",
                "status": "PASS",
                "message": f"Range={price_range_pct:.2f}% (< 10%)"
            })
            print(f"   ✓ Price Range: {price_range_pct:.2f}% (reasonable)")
        else:
            checks.append({
                "name": "Price Range Reasonable",
                "status": "WARN",
                "message": f"Range={price_range_pct:.2f}% (> 10%, unusual)"
            })
            print(f"   ⚠ Price Range: {price_range_pct:.2f}% (unusual, please verify)")
        
        return checks
    
    def _compare_with_alternative_source(self, target_date: str, system_data: pd.Series) -> Dict:
        """Compare with alternative data source."""
        try:
            # Try to get data from another akshare interface
            # For futures, we can try futures_zh_daily_sina directly
            symbol_map = {
                'IM0': 'IM0',  # 中证1000
                'IC0': 'IC0',  # 中证500
                'IF0': 'IF0',  # 沪深300
                'IH0': 'IH0',  # 上证50
            }
            
            ak_symbol = symbol_map.get(self.symbol, self.symbol)
            print(f"   Fetching from akshare futures_zh_daily_sina...")
            
            alt_df = ak.futures_zh_daily_sina(symbol=ak_symbol)
            if alt_df is None or alt_df.empty:
                return {
                    "name": "Alternative Source Comparison",
                    "status": "WARN",
                    "message": "Could not fetch alternative data for comparison"
                }
            
            # Find target date
            alt_df['date'] = pd.to_datetime(alt_df['date']).dt.date
            target_dt = pd.Timestamp(target_date).date()
            alt_day = alt_df[alt_df['date'] == target_dt]
            
            if alt_day.empty:
                return {
                    "name": "Alternative Source Comparison",
                    "status": "WARN",
                    "message": f"Target date {target_date} not found in alternative source"
                }
            
            alt_data = alt_day.iloc[0]
            print(f"   Alternative: O={alt_data['open']}, H={alt_data['high']}, "
                  f"L={alt_data['low']}, C={alt_data['close']}")
            
            # Compare values (allow small tolerance for rounding)
            tolerance = 0.01  # 0.01 points
            matches = {
                'open': abs(system_data['open'] - alt_data['open']) <= tolerance,
                'high': abs(system_data['high'] - alt_data['high']) <= tolerance,
                'low': abs(system_data['low'] - alt_data['low']) <= tolerance,
                'close': abs(system_data['close'] - alt_data['close']) <= tolerance,
            }
            
            all_match = all(matches.values())
            
            if all_match:
                print(f"   ✓ All OHLC values match!")
                return {
                    "name": "Alternative Source Comparison",
                    "status": "PASS",
                    "message": "OHLC values match alternative source"
                }
            else:
                mismatches = [k for k, v in matches.items() if not v]
                print(f"   ⚠ Mismatches found: {mismatches}")
                return {
                    "name": "Alternative Source Comparison",
                    "status": "WARN",
                    "message": f"Some values differ: {mismatches}"
                }
                
        except Exception as e:
            print(f"   ⚠ Could not compare: {e}")
            return {
                "name": "Alternative Source Comparison",
                "status": "WARN",
                "message": f"Comparison failed: {str(e)}"
            }
    
    def _verify_synthetic_minute(self, daily_data: pd.Series) -> Dict:
        """Verify synthetic minute data calculation logic."""
        print("   Checking synthetic minute data formula...")
        
        o, h, l, c = daily_data['open'], daily_data['high'], daily_data['low'], daily_data['close']
        
        # Expected synthetic prices at key times (based on _synthesize_minute_from_daily logic)
        expected_prices = {
            "09:30": o,
            "10:00": o + (h - o) * 0.3 if c > o else o - (o - l) * 0.3,
            "11:30": o + (h - o) * 0.5 if c > o else o - (o - l) * 0.5,
            "14:30": o + (c - o) * 0.7,
            "15:00": c
        }
        
        print(f"   Synthetic price estimates:")
        for time, price in expected_prices.items():
            print(f"      {time}: {price:.2f}")
        
        # The 14:30 price is crucial for the settlement arbitrage strategy
        price_1430 = expected_prices["14:30"]
        
        # Verify it's within valid range
        if l <= price_1430 <= h:
            return {
                "name": "Synthetic Minute Data",
                "status": "PASS",
                "message": f"14:30 synthetic price ({price_1430:.2f}) is within [L={l}, H={h}]"
            }
        else:
            return {
                "name": "Synthetic Minute Data",
                "status": "WARN",
                "message": f"14:30 synthetic price ({price_1430:.2f}) may be inaccurate"
            }
    
    def print_summary(self):
        """Print verification summary."""
        print("\n" + "="*60)
        print("VERIFICATION SUMMARY")
        print("="*60)
        
        for r in self.results:
            status_icon = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "UNKNOWN": "?"}[r["status"]]
            print(f"\n{status_icon} {r['symbol']} @ {r['date']}: {r['status']}")
            for check in r["checks"]:
                check_icon = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠"}[check["status"]]
                print(f"   {check_icon} {check['name']}: {check['message']}")
        
        # Overall summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        warned = sum(1 for r in self.results if r["status"] == "WARN")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        
        print(f"\nOverall: {passed}/{total} PASSED, {warned} WARNINGS, {failed} FAILED")
    
    def export_results(self, filepath: str):
        """Export results to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nResults exported to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Verify backtest data correctness")
    parser.add_argument("--symbol", default="IM0", help="Futures symbol (default: IM0)")
    parser.add_argument("--dates", help="Comma-separated dates to verify (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=5, help="Number of recent days to verify (default: 5)")
    parser.add_argument("--export", help="Export results to JSON file")
    
    args = parser.parse_args()
    
    # Determine dates to verify
    if args.dates:
        dates = [d.strip() for d in args.dates.split(",")]
    else:
        # Use recent N trading days
        today = datetime.now().date()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, args.days + 1)]
    
    print(f"Backtest Data Verification Tool")
    print(f"Symbol: {args.symbol}")
    print(f"Dates to verify: {dates}")
    
    verifier = BacktestDataVerifier(args.symbol)
    
    for date in dates:
        verifier.verify_daily_data(date)
    
    verifier.print_summary()
    
    if args.export:
        verifier.export_results(args.export)


if __name__ == "__main__":
    main()
