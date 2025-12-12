# 🔍 LLM SQL Agent — Natural Language to SQL + Query Optimizer

A full-stack AI system that converts **natural language queries** into **optimized SQL**, validates query safety, analyzes query plans using PostgreSQL's `EXPLAIN`, simulates index creation, and tests LLM-based rewrites for performance improvements.

This project includes:

- 🌐 **FastAPI Backend**
- 🖥️ **Streamlit Frontend**
- 🗄️ **PostgreSQL Execution Engine**
- 🤖 **LLM (OpenAI) for SQL generation & rewriting**
- 📊 **Query optimizer + performance analyzer**
- 📝 **Agent logging for research**
FEATURES:
  🧠 LLM-Powered NL → SQL
Converts English questions into SQL queries
Uses database schema context for accurate generation

🔒 SQL Safety Validator
Detects unsafe patterns
Blocks DROP/ALTER/TRUNCATE or harmful behaviors

📈 Query Plan Analyzer
Runs EXPLAIN and EXPLAIN ANALYZE
Extracts execution cost, node types, joins, seq scans, sort nodes, etc.

⚡ Query Optimizer
Detects performance bottlenecks

🧪 LLM Rewrite + Test Engine
Auto-rewrites SQL queries using LLM
Tests each rewrite:
Valid SQL?
Faster or slower?
Safer or unsafe?
Produces comparison metrics

🎨 Streamlit UI
Clean dashboard
Interactive query box

Shows logs, SQL output, and optimizer suggestions

  🏗️ SYSTEM ARCHITECTURE

          ┌────────────────────────────────────────┐
          │               User (UI)                │
          │          Streamlit Frontend            │
          └─────────────────────┬──────────────────┘
                                │ HTTP Request
                                ▼
                ┌────────────────────────────────┐
                │          FastAPI Backend        │
                │  - NL→SQL                       │
                │  - Validator                    │
                │  - Optimizer                    │
                │  - Rewrite engine               │
                └────────────────┬────────────────┘
                                 │ SQL
                                 ▼
                  ┌──────────────────────────────┐
                  │       PostgreSQL DB          │
                  │ Executes SQL + EXPLAIN plans │
                  └──────────────────────────────┘
