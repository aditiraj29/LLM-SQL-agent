# test_analyze.py
from core.nl2sql import nl_to_sql
from core.executor import explain_query
from core.optimizer import analyze_plan_for_issues, suggest_rewrite_remove_select_star
from core.validator import is_safe_sql
import pprint

q = "Show the total rental revenue per month for 2006"
print("NL:", q)

out = nl_to_sql(q)
pprint.pprint(out)

sql = out.get("sql") if isinstance(out, dict) else out
print("\nSQL:\n", sql)

ok, msg = is_safe_sql(sql)
print("\nValidator:", ok, msg)
if not ok:
    raise SystemExit(1)

plan = explain_query(sql)
print("\nEXPLAIN plan top-level (truncated):")
pprint.pprint(plan if isinstance(plan, dict) else plan[0])

print("\nSuggestions:")
sugs = analyze_plan_for_issues(plan)
for s in sugs:
    print("-", s)

# optional: select-star suggestion
sr = suggest_rewrite_remove_select_star(sql, sample_columns=None)
if sr:
    print("\nRewrite suggestion:", sr)
