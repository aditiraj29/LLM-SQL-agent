import os, json
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    result = urlparse(DATABASE_URL)
    dbname = result.path[1:]
    user = result.username
    password = result.password
    host = result.hostname
    port = result.port or 5432
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    return conn

def export_schema_json(out_path="schema.json"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    SELECT table_schema, table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema NOT IN ('pg_catalog','information_schema')
    ORDER BY table_schema, table_name, ordinal_position;
    """)
    rows = cur.fetchall()
    schema = {}
    for schema_name, table_name, column_name, data_type in rows:
        key = f"{schema_name}.{table_name}"
        schema.setdefault(key, []).append({"column": column_name, "type": data_type})
    with open(out_path, "w") as f:
        json.dump(schema, f, indent=2)
    cur.close()
    conn.close()
    print("Schema exported to", out_path)

if __name__ == "__main__":
    export_schema_json()
