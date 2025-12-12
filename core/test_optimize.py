# test_optimize.py
from core.nl2sql import nl_to_sql
from core.validator import is_safe_sql
import core.executor as executor
from core.optimizer import compare_plans_and_time, suggest_rewrite_remove_select_star
import pprint

# NL query to test
q = "Show the total rental revenue per month for 2006"
print("NL:", q)

out = nl_to_sql(q)
pprint.pprint(out)
sql = out.get("sql") if isinstance(out, dict) else out

print("\nSQL:\n", sql)
ok, msg = is_safe_sql(sql)
print("Validator:", ok, msg)
if not ok:
    raise SystemExit(1)

# First measure original
print("\nRunning EXPLAIN ANALYZE for original SQL...")
res = compare_plans_and_time(sql, executor_module=executor)
pprint.pprint({"original_time_ms": res["original"]["time_ms"]})

# OPTIONAL: simulate index creation
simulate = input("\nSimulate index creation? (y/N): ").strip().lower()

if simulate == "y":
    idx_stmt = "CREATE INDEX IF NOT EXISTS idx_payment_payment_date ON payment (payment_date);"
    res2 = compare_plans_and_time(sql, simulate_index_stmt=idx_stmt, executor_module=executor)
    print("\n=== INDEX EXPERIMENT RESULTS ===")
    pprint.pprint({
        "with_index_time_ms": res2.get("with_index", {}).get("time_ms"),
        "original_time_ms": res["original"]["time_ms"]
    })
    print("\nIndex was created and dropped automatically.")
else:
    print("\nSkipping index simulation.")
