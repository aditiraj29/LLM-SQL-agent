# scripts/aggregate_logs.py
import csv
from collections import defaultdict
rows = defaultdict(list)
with open("agent_logs.csv","r",encoding="utf-8") as f:
    for ln in f:
        parts = ln.strip().split("|")
        if len(parts) < 4: continue
        ts, action, q, flag = parts[:4]
        rows[action].append((ts,q,flag))
# simple print
for k,v in rows.items():
    print(k, len(v))
