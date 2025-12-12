# core/optimizer.py
import json

def analyze_plan_for_issues(plan_json):
    """
    Analyze Postgres EXPLAIN (FORMAT JSON) output and return human-friendly suggestions.
    """
    suggestions = []

    # normalize to plan dict
    root = plan_json[0]["Plan"] if isinstance(plan_json, list) else plan_json.get("Plan", plan_json)

    def walk(node):
        if not isinstance(node, dict):
            return
        node_type = node.get("Node Type", "") or node.get("Node Type")
        # Seq Scan detection
        if "Seq Scan" in str(node_type):
            relation = node.get("Relation Name") or node.get("Relation")
            filter_cond = node.get("Filter")
            if relation and filter_cond:
                suggestions.append(f"Seq Scan on table '{relation}' with filter '{filter_cond}'. Consider adding an index on the filtered column(s).")
            else:
                suggestions.append(f"Seq Scan detected on node: {node_type}. Investigate table size and possible indexes.")
        # Sort detection
        if "Sort" in str(node_type):
            sort_key = node.get("Sort Key")
            suggestions.append(f"Sort operation detected (keys: {sort_key}). Consider creating an index on the sort key or limiting rows early.")
        # Nested loop / hash join hints
        if "Nested Loop" in str(node_type):
            suggestions.append("Nested Loop join detected — may be slow for large inputs. Consider index on join keys or reordering joins.")
        if "Hash Join" in str(node_type):
            suggestions.append("Hash Join detected — ensure build side is not huge; check memory usage.")
        # Cardinality mismatch
        try:
            plan_rows = float(node.get("Plan Rows", 0))
            actual_rows = float(node.get("Actual Rows", node.get("Actual Rows", 0)))
            if plan_rows > 0 and actual_rows/plan_rows > 10:
                suggestions.append(f"Cardinality mismatch: estimated {plan_rows} rows but actual {actual_rows} rows. Consider running ANALYZE or increasing statistics target.")
        except Exception:
            pass
        # traverse children
        for child in node.get("Plans", []) or []:
            walk(child)

    try:
        walk(root)
    except Exception as e:
        suggestions.append(f"Plan analysis error: {str(e)}")

    if not suggestions:
        suggestions.append("No obvious issues detected in plan.")
    return suggestions

def suggest_rewrite_remove_select_star(sql_text, sample_columns=None):
    """
    Suggest replacing SELECT * with explicit columns.
    sample_columns: optional list of columns to propose.
    """
    try:
        if "select *" in sql_text.lower():
            if sample_columns and isinstance(sample_columns, (list, tuple)) and len(sample_columns) > 0:
                cols = ", ".join(sample_columns[:10])
                return f"Replace SELECT * with explicit columns: SELECT {cols} ..."
            return "Replace SELECT * with explicit column list to avoid unnecessary data transfer."
    except Exception:
        pass
    return None

def extract_total_time_from_analyze(plan_json):
    """
    Extract total execution time from EXPLAIN ANALYZE JSON plan (Postgres).
    """
    try:
        root = plan_json[0] if isinstance(plan_json, list) else plan_json
        # top-level Execution Time
        if isinstance(root, dict) and "Execution Time" in root:
            return float(root["Execution Time"])
        plan = root.get("Plan", root) if isinstance(root, dict) else root
        if isinstance(plan, dict) and "Actual Total Time" in plan:
            return float(plan["Actual Total Time"])
        # recursive search
        def walk_for_time(node):
            if isinstance(node, dict):
                if "Execution Time" in node:
                    return float(node["Execution Time"])
                if "Actual Total Time" in node:
                    return float(node["Actual Total Time"])
                for child in node.get("Plans", []) or []:
                    t = walk_for_time(child)
                    if t:
                        return t
            return None
        t = walk_for_time(plan)
        return float(t) if t is not None else None
    except Exception:
        return None

def compare_plans_and_time(original_sql, modified_sql=None, simulate_index_stmt=None, executor_module=None):
    """
    Run EXPLAIN ANALYZE on original_sql and optionally:
     - run EXPLAIN ANALYZE on modified_sql, or
     - create index (simulate_index_stmt), run ANALYZE, then drop index.
    executor_module must provide explain_analyze() and get_conn().
    """
    if executor_module is None:
        raise ValueError("Provide executor_module (core.executor)")

    results = {}
    # original plan/time
    orig_plan = executor_module.explain_analyze(original_sql)
    orig_time = extract_total_time_from_analyze(orig_plan)
    results["original"] = {"time_ms": orig_time, "plan": orig_plan}

    if modified_sql:
        mod_plan = executor_module.explain_analyze(modified_sql)
        mod_time = extract_total_time_from_analyze(mod_plan)
        results["modified"] = {"time_ms": mod_time, "plan": mod_plan}
        return results

    if simulate_index_stmt:
        conn = executor_module.get_conn()
        cur = conn.cursor()
        try:
            print("Creating simulated index:", simulate_index_stmt)
            cur.execute(simulate_index_stmt)
            conn.commit()
            plan_with_index = executor_module.explain_analyze(original_sql)
            time_with_index = extract_total_time_from_analyze(plan_with_index)
            results["with_index"] = {"time_ms": time_with_index, "plan": plan_with_index}
        finally:
            # attempt to drop the index by name (naive extraction)
            try:
                parts = simulate_index_stmt.split()
                if len(parts) >= 3 and parts[0].lower() == "create" and parts[1].lower() == "index":
                    idxname = parts[2]
                    cur.execute(f"DROP INDEX IF EXISTS {idxname}")
                    conn.commit()
            except Exception:
                pass
            cur.close()
            conn.close()
        return results

    return results
