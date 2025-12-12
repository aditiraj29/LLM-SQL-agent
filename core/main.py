# app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import json, time, pathlib

# Import core modules (these should exist in core/)
from core.nl2sql import nl_to_sql
from core.validator import is_safe_sql
import core.executor as executor
from core.optimizer import analyze_plan_for_issues, compare_plans_and_time
from core.rewriter import ask_llm_for_rewrites

app = FastAPI(title="LLM SQL Agent API")

# Allow local Streamlit UI to talk to API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic models ---
class NLQuery(BaseModel):
    question: str

class SQLPayload(BaseModel):
    sql: str

class OptimizePayload(BaseModel):
    sql: str
    index_sql: str = None

class RewritePayload(BaseModel):
    sql: str

# --- helper for safe logging ---
LOG_PATH = pathlib.Path("agent_logs.csv")

def append_log(line: str):
    # Safe append to CSV-like file
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# --- endpoints ---

@app.post("/nl2sql")
def nl2sql_endpoint(payload: NLQuery):
    q = payload.question
    out = nl_to_sql(q)
    sql = out.get("sql") if isinstance(out, dict) else (out or "")
    explain = out.get("explain") if isinstance(out, dict) else ""
    # Validate before returning; don't execute here
    ok, msg = is_safe_sql(sql)
    if not ok:
        return {"ok": False, "error": msg, "sql": sql}
    # Get EXPLAIN (FORMAT JSON) plan for summary (not ANALYZE)
    try:
        plan = executor.explain_query(sql)
        suggestions = analyze_plan_for_issues(plan)
    except Exception as e:
        plan = None
        suggestions = [f"Error generating plan: {str(e)}"]
    # Log minimal info
    append_log(f"{time.time()}|nl2sql|{q.replace('|',' ')}|{bool(sql)}")
    return {"ok": True, "sql": sql, "explain": explain, "plan": plan, "suggestions": suggestions}

@app.post("/execute")
def execute_endpoint(payload: SQLPayload):
    sql = payload.sql
    ok, msg = is_safe_sql(sql)
    if not ok:
        return {"ok": False, "error": msg}
    try:
        res = executor.run_readonly_query(sql)
        append_log(f"{time.time()}|execute|{sql.replace('|',' ')}|rows:{len(res.get('rows',[]))}")
        return {"ok": True, "result": res}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/optimize")
def optimize_endpoint(payload: OptimizePayload):
    sql = payload.sql
    idx_sql = payload.index_sql
    ok, msg = is_safe_sql(sql)
    if not ok:
        return {"ok": False, "error": msg}
    try:
        res = compare_plans_and_time(sql, simulate_index_stmt=idx_sql, executor_module=executor)
        # Log original and index times (if present)
        orig_t = res.get("original", {}).get("time_ms")
        with_idx_t = res.get("with_index", {}).get("time_ms")
        append_log(f"{time.time()}|optimize|{sql.replace('|',' ')}|orig:{orig_t}|with_idx:{with_idx_t}")
        return {"ok": True, "result": res}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/rewrite_and_test")
def rewrite_and_test(payload: RewritePayload):
    sql = payload.sql
    ok, msg = is_safe_sql(sql)
    if not ok:
        return {"ok": False, "error": msg}
    try:
        rew = ask_llm_for_rewrites(sql)
        cands = rew.get("candidates", [])
        results = {"original": None, "candidates": []}
        res_orig = compare_plans_and_time(sql, executor_module=executor)
        results["original"] = {"time_ms": res_orig["original"]["time_ms"]}
        for c in cands:
            cand_sql = c.get("sql")
            if not cand_sql:
                continue
            safe, _ = is_safe_sql(cand_sql)
            if not safe:
                continue
            r = compare_plans_and_time(cand_sql, executor_module=executor)
            results["candidates"].append({"sql": cand_sql, "time_ms": r.get("original", {}).get("time_ms"), "note": c.get("note", "")})
        results["candidates"].sort(key=lambda x: x.get("time_ms") or 1e9)
        append_log(f"{time.time()}|rewrite|{sql.replace('|',' ')}|cands:{len(results['candidates'])}")
        return {"ok": True, "result": results, "raw_rewrites": rew}
    except Exception as e:
        return {"ok": False, "error": str(e)}
