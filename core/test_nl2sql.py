# test_nl2sql.py
from core.nl2sql import nl_to_sql
q = "Show the total rental revenue per month for 2006"
out = nl_to_sql(q)
print("NL:", q)
print("Generated JSON / SQL:\n", out)
