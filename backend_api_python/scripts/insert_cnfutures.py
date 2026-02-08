#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Quick script to insert CNFutures data directly."""
import sys
import io

# Force stdout to use utf-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = 'postgresql://quantdinger:quantdinger123@localhost:5433/quantdinger'

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

print("Starting CNFutures data insertion...")
sys.stdout.flush()

try:
    print("Connecting to database...")
    sys.stdout.flush()
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check existing
    cur.execute("SELECT COUNT(*) as cnt FROM qd_market_symbols WHERE market = %s", ('CNFutures',))
    row = cur.fetchone()
    print("Existing CNFutures count: {}".format(row['cnt']))
    sys.stdout.flush()
    
    # Insert
    for s in symbols:
        cur.execute("""
            INSERT INTO qd_market_symbols (market, symbol, name, exchange, currency, is_active, is_hot, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (market, symbol) DO UPDATE SET
                name = EXCLUDED.name, exchange = EXCLUDED.exchange, currency = EXCLUDED.currency,
                is_active = EXCLUDED.is_active, is_hot = EXCLUDED.is_hot, sort_order = EXCLUDED.sort_order
        """, s)
        print("Inserted: {} - {}".format(s[1], s[2]))
        sys.stdout.flush()
    
    conn.commit()
    print("Committed!")
    sys.stdout.flush()
    
    # Verify
    cur.execute("SELECT market, symbol, name, is_hot FROM qd_market_symbols WHERE market = %s ORDER BY sort_order DESC", ('CNFutures',))
    rows = cur.fetchall()
    print("Total CNFutures after insert: {}".format(len(rows)))
    for r in rows:
        print("  {}: {} (is_hot={})".format(r['symbol'], r['name'], r['is_hot']))
    sys.stdout.flush()
    
    cur.close()
    conn.close()
    print("Done!")
except Exception as e:
    print("Error: {}".format(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)