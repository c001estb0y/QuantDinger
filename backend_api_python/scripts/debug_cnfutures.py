#!/usr/bin/env python
"""Debug script to check CNFutures data in database."""

import os
import sys

# Set environment variable for database
os.environ['DATABASE_URL'] = 'postgresql://quantdinger:quantdinger123@localhost:5433/quantdinger'

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2 not installed")
    sys.exit(1)

def main():
    print("=" * 60)
    print("Debug: Checking CNFutures data in database")
    print("=" * 60)
    
    db_url = os.environ.get('DATABASE_URL')
    print(f"DATABASE_URL: {db_url[:50]}..." if db_url else "DATABASE_URL: NOT SET")
    
    try:
        print("\n1. Connecting to database...")
        conn = psycopg2.connect(db_url)
        print("   Connected successfully!")
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("\n2. Checking all markets in qd_market_symbols...")
        cur.execute("SELECT DISTINCT market, COUNT(*) as cnt FROM qd_market_symbols GROUP BY market ORDER BY market")
        markets = cur.fetchall()
        for m in markets:
            print(f"   - {m['market']}: {m['cnt']} records")
        
        print("\n3. Checking CNFutures records specifically...")
        cur.execute("SELECT * FROM qd_market_symbols WHERE market = %s ORDER BY sort_order DESC", ('CNFutures',))
        rows = cur.fetchall()
        print(f"   Found {len(rows)} CNFutures records")
        for row in rows:
            print(f"   - {row['symbol']}: {row['name']} (is_hot={row['is_hot']}, is_active={row['is_active']})")
        
        if len(rows) == 0:
            print("\n4. No CNFutures data found, inserting now...")
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
            
            for symbol in symbols:
                try:
                    cur.execute("""
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
                    print(f"   Inserted: {symbol[1]} - {symbol[2]}")
                except Exception as e:
                    print(f"   Error inserting {symbol[1]}: {e}")
            
            conn.commit()
            print("   Committed!")
            
            # Verify
            print("\n5. Verifying inserted data...")
            cur.execute("SELECT * FROM qd_market_symbols WHERE market = %s ORDER BY sort_order DESC", ('CNFutures',))
            rows = cur.fetchall()
            print(f"   Now have {len(rows)} CNFutures records")
            for row in rows:
                print(f"   - {row['symbol']}: {row['name']}")
        
        cur.close()
        conn.close()
        print("\n" + "=" * 60)
        print("Done! Please restart the backend server.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
