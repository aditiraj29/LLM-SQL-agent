# core/executor.py
import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    """
    Creates a PostgreSQL connection using DATABASE_URL from .env.
    """
    url = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        dbname=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port or 5432
    )
    return conn

def run_readonly_query(sql_text, row_limit=5000, timeout_ms=20000):
    """
    Safely run SELECT queries with an auto-added LIMIT if missing.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SET statement_timeout = {timeout_ms};")

    raw = sql_text.strip()
    if raw.lower().startswith("select") and "limit" not in raw.lower():
        wrapped = f"SELECT * FROM ({raw}) AS subq LIMIT {row_limit};"
    else:
        wrapped = raw

    cur.execute(wrapped)
    cols = [desc[0] for desc in cur.description] if cur.description else []
    rows = cur.fetchmany(row_limit)

    cur.close()
    conn.close()
    return {"columns": cols, "rows": rows}

def explain_query(sql_text):
    """
    EXPLAIN (FORMAT JSON) for understanding query plan structure.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"EXPLAIN (FORMAT JSON) {sql_text}")
    plan = cur.fetchone()[0]
    cur.close()
    conn.close()
    return plan

def explain_analyze(sql_text):
    """
    Runs EXPLAIN ANALYZE (FORMAT JSON) which executes the query and returns
    actual execution time + plan.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 120000;")  # 2 min timeout
    cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql_text}")
    plan = cur.fetchone()[0]
    cur.close()
    conn.close()
    return plan

