#!/usr/bin/env python
"""
Script to add CNFutures (China Futures) hot symbols to the database.
Run this script once to populate the hot symbols for CNFutures market.

Supports PostgreSQL database.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def add_cnfutures_symbols():
    """Add CNFutures hot symbols to database."""
    
    # Import after path is set
    try:
        from app.utils.db import get_db_connection
    except ImportError as e:
        print(f"Failed to import database module: {e}")
        return False
    
    # CNFutures hot symbols
    symbols = [
        ('CNFutures', 'IF', '沪深300股指', 'CFFEX', 'CNY', 1, 1, 100),
        ('CNFutures', 'IC', '中证500股指', 'CFFEX', 'CNY', 1, 1, 99),
        ('CNFutures', 'IH', '上证50股指', 'CFFEX', 'CNY', 1, 1, 98),
        ('CNFutures', 'IM', '中证1000股指', 'CFFEX', 'CNY', 1, 1, 97),
        ('CNFutures', 'AU', '黄金', 'SHFE', 'CNY', 1, 1, 96),
        ('CNFutures', 'AG', '白银', 'SHFE', 'CNY', 1, 1, 95),
        ('CNFutures', 'CU', '沪铜', 'SHFE', 'CNY', 1, 1, 94),
        ('CNFutures', 'RB', '螺纹钢', 'SHFE', 'CNY', 1, 1, 93),
        ('CNFutures', 'SC', '原油', 'INE', 'CNY', 1, 1, 92),
        ('CNFutures', 'MA', '甲醇', 'CZCE', 'CNY', 1, 1, 91),
    ]
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check existing CNFutures records
            cursor.execute("SELECT COUNT(*) as cnt FROM qd_market_symbols WHERE market = %s", ('CNFutures',))
            row = cursor.fetchone()
            existing_count = row['cnt'] if row else 0
            print(f"Existing CNFutures records: {existing_count}")
            
            # Insert new symbols
            inserted = 0
            for symbol in symbols:
                try:
                    cursor.execute("""
                        INSERT INTO qd_market_symbols 
                        (market, symbol, name, exchange, currency, is_active, is_hot, sort_order)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (market, symbol) DO UPDATE SET
                            name = EXCLUDED.name,
                            exchange = EXCLUDED.exchange,
                            currency = EXCLUDED.currency,
                            is_active = EXCLUDED.is_active,
                            is_hot = EXCLUDED.is_hot,
                            sort_order = EXCLUDED.sort_order
                    """, symbol)
                    inserted += 1
                except Exception as e:
                    print(f"Error inserting {symbol[1]}: {e}")
            
            conn.commit()
            print(f"Successfully inserted/updated {inserted} CNFutures symbols")
            
            # Verify
            cursor.execute("SELECT market, symbol, name FROM qd_market_symbols WHERE market = %s ORDER BY sort_order DESC", ('CNFutures',))
            rows = cursor.fetchall()
            print(f"\nCNFutures symbols in database ({len(rows)} total):")
            for row in rows:
                print(f"  {row['symbol']}: {row['name']}")
            
            return True
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Adding CNFutures hot symbols to database...")
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')[:50]}...")
    success = add_cnfutures_symbols()
    if success:
        print("\nDone! Please restart the backend server to see the changes.")
    else:
        print("\nFailed to add symbols.")
    sys.exit(0 if success else 1)
