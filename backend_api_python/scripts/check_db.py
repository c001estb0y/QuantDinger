#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check CNFutures data in database."""
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = 'postgresql://quantdinger:quantdinger123@localhost:5433/quantdinger'

with open('db_check_result.txt', 'w', encoding='utf-8') as f:
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check all markets
        cur.execute("SELECT DISTINCT market, COUNT(*) as cnt FROM qd_market_symbols GROUP BY market ORDER BY market")
        markets = cur.fetchall()
        f.write("All markets in qd_market_symbols:\n")
        for m in markets:
            f.write(f"  {m['market']}: {m['cnt']} records\n")
        
        # Check CNFutures specifically
        f.write("\nCNFutures records:\n")
        cur.execute("SELECT * FROM qd_market_symbols WHERE market = %s ORDER BY sort_order DESC", ('CNFutures',))
        rows = cur.fetchall()
        f.write(f"  Total: {len(rows)}\n")
        for row in rows:
            f.write(f"  - {row['symbol']}: {row['name']} (is_hot={row['is_hot']}, is_active={row['is_active']})\n")
        
        cur.close()
        conn.close()
        f.write("\nDone!\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
        import traceback
        f.write(traceback.format_exc())
