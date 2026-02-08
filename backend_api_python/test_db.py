import sys
import traceback

print("Script started", flush=True)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("psycopg2 imported", flush=True)
    
    DB_URL = 'postgresql://quantdinger:quantdinger123@localhost:5433/quantdinger'
    print(f"Connecting to: {DB_URL}", flush=True)
    
    conn = psycopg2.connect(DB_URL, connect_timeout=5)
    print("Connected!", flush=True)
    
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check all markets
    cur.execute("SELECT market, COUNT(*) as cnt FROM qd_market_symbols GROUP BY market ORDER BY market")
    markets = cur.fetchall()
    print("\n=== All markets ===", flush=True)
    for m in markets:
        print(f"  {m['market']}: {m['cnt']} records", flush=True)
    
    # Check CNFutures
    cur.execute("SELECT symbol, name, is_hot, is_active FROM qd_market_symbols WHERE market = 'CNFutures' ORDER BY sort_order DESC")
    rows = cur.fetchall()
    print(f"\n=== CNFutures ({len(rows)} records) ===", flush=True)
    for row in rows:
        print(f"  {row['symbol']}: {row['name']} (hot={row['is_hot']}, active={row['is_active']})", flush=True)
    
    cur.close()
    conn.close()
    print("\nDone!", flush=True)
    
except Exception as e:
    print(f"Error: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
