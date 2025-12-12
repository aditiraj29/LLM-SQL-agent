# app/ui_streamlit.py
import streamlit as st
import requests, json, time
from pathlib import Path

API = "http://127.0.0.1:8000"  # keep FastAPI running for backend endpoints
st.set_page_config(page_title="LLM SQL Agent", layout="wide")
st.title("LLM SQL Agent — Demo")

q = st.text_input("Ask a question about the database", "Show the total rental revenue per month for 2006")

if st.button("Generate SQL"):
    with st.spinner("Generating SQL..."):
        try:
            r = requests.post(f"{API}/nl2sql", json={"question": q}, timeout=30)
            data = r.json()
        except Exception as e:
            st.error(f"API error: {e}")
            data = {"ok": False, "error": str(e)}
    if not data.get("ok"):
        st.error(data.get("error","Unknown error"))
    else:
        st.subheader("Generated SQL")
        st.code(data["sql"], language="sql")
        st.write("Explanation:", data.get("explain",""))
        st.subheader("EXPLAIN plan (summary)")
        st.write(data.get("suggestions", []))
        st.session_state["last_sql"] = data["sql"]

if "last_sql" in st.session_state:
    st.markdown("---")
    sql = st.session_state["last_sql"]
    if st.button("Run Query (preview)"):
        with st.spinner("Running query..."):
            try:
                r = requests.post(f"{API}/execute", json={"sql": sql}, timeout=60)
                res = r.json()
            except Exception as e:
                st.error(f"API error: {e}")
                res = {"ok": False, "error": str(e)}
        if not res.get("ok"):
            st.error(res.get("error"))
        else:
            rows = res["result"]
            st.dataframe([dict(zip(rows["columns"], row)) for row in rows["rows"][:50]])

    if st.button("Optimize (simulate index)"):
        idx = "CREATE INDEX IF NOT EXISTS idx_payment_payment_date ON payment (payment_date);"
        with st.spinner("Creating index and testing..."):
            try:
                r = requests.post(f"{API}/optimize", json={"sql": sql, "index_sql": idx}, timeout=120)
                res = r.json()
            except Exception as e:
                st.error(f"API error: {e}")
                res = {"ok": False, "error": str(e)}
        if res.get("ok"):
            st.write(res["result"])
        else:
            st.error(res.get("error"))

    if st.button("LLM Rewrite + Test"):
        with st.spinner("Requesting rewrites and testing..."):
            try:
                r = requests.post(f"{API}/rewrite_and_test", json={"sql": sql}, timeout=120)
                res = r.json()
            except Exception as e:
                st.error(f"API error: {e}")
                res = {"ok": False, "error": str(e)}
        if res.get("ok"):
            st.write("Results:")
            st.json(res["result"])
            st.write("Raw rewrites (LLM):")
            st.json(res.get("raw_rewrites", {}))
        else:
            st.error(res.get("error"))

st.sidebar.markdown("## Logs")
logf = Path("agent_logs.csv")
if logf.exists():
    st.write("Recent logs (last 10):")
    df = []
    with open(logf, "r", encoding="utf-8") as f:
        lines = f.read().strip().splitlines()[-10:]
        for ln in lines:
            df.append(ln.split("|"))
    st.table(df)
