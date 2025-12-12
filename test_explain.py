# test_explain.py
from core.nl2sql import nl_to_sql
from core.validator import is_safe_sql
from core.executor import explain_query, run_readonly_query
import json, pprint

q = "Show the total rental revenue per month for 2006"
print("NL query:", q)

out = nl_to_sql(q)
print("\nNL->SQL output:")
pprint.pprint(out)

sql = out.get("sql") if isinstance(out, dict) else out
print("\nSQL to validate:\n", sql)

ok, msg = is_safe_sql(sql)
print("\nValidator result:", ok, msg)
if not ok:
    print("Stopping because SQL is unsafe.")
    raise SystemExit(1)

print("\nFetching EXPLAIN (FORMAT JSON) plan...")
plan = explain_query(sql)
print("\nPlan (truncated pretty):")
# pretty print top-level plan summary
try:
    pprint.pprint(plan if isinstance(plan, dict) else plan[0])
except Exception:
    print(json.dumps(plan)[:2000])

