# core/nl2sql.py
import os
import json
import re
from dotenv import load_dotenv
load_dotenv()

# Try to import new OpenAI client; if not available we will still allow fallback.
try:
    from openai import OpenAI
    _has_openai_v1 = True
except Exception:
    _has_openai_v1 = False

OPENAI_KEY = os.getenv("OPENAI_API_KEY", "") or None

SCHEMA_PATH = "schema.json"
if os.path.exists(SCHEMA_PATH):
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        SCHEMA = json.load(f)
else:
    SCHEMA = {}

SYSTEM_PROMPT = (
    "You are an assistant that converts natural language questions into syntactically "
    "correct PostgreSQL SELECT queries.\n\nRules:\n"
    "- Only output JSON with fields: {\"sql\":\"...\",\"explain\":\"short explanation\"}\n"
    "- Only produce SELECT queries (no INSERT/UPDATE/DELETE/DDL).\n"
    "- Use the provided schema (table names and columns) and do not invent columns."
)

def build_prompt(nl_query, schema_sample_limit=12):
    # Include a concise schema sample
    sample_lines = []
    count = 0
    for t, cols in SCHEMA.items():
        if count >= schema_sample_limit:
            break
        colnames = ", ".join(c["column"] for c in cols[:10])
        sample_lines.append(f"{t}: {colnames}")
        count += 1
    schema_text = "\n".join(sample_lines) if sample_lines else "(no schema available)"
    prompt = (
        SYSTEM_PROMPT
        + "\n\nSchema (sample):\n"
        + schema_text
        + "\n\nQuestion:\n"
        + nl_query
        + "\n\nReturn JSON only."
    )
    return prompt

def _parse_json_from_text(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None

def _fallback_rule_based(nl_query):
    """Simple fallback to allow testing without API key.
    Recognizes a couple of common patterns for the Pagila DB.
    """
    q = nl_query.lower()
    if "rental revenue" in q or "total rental revenue" in q or "rental revenue per month" in q:
        sql = (
            "SELECT date_trunc('month', payment_date) AS month, "
            "SUM(amount) AS total_rental_revenue "
            "FROM payment "
            "JOIN rental USING (rental_id) "
            "GROUP BY month ORDER BY month;"
        )
        return {"sql": sql, "explain": "monthly rental revenue aggregated from payment table"}
    if "top 10 customers" in q or "top 10 customers by number of rentals" in q:
        sql = (
            "SELECT c.customer_id, c.first_name, c.last_name, COUNT(r.rental_id) AS rental_count "
            "FROM customer c JOIN rental r ON c.customer_id = r.customer_id "
            "GROUP BY c.customer_id, c.first_name, c.last_name "
            "ORDER BY rental_count DESC LIMIT 10;"
        )
        return {"sql": sql, "explain": "top 10 customers by rental count"}
    # Generic fallback: try a safe introspection-like response
    return {"sql": "-- fallback: please provide a different or more specific question", "explain": "fallback - no rule matched"}

def nl_to_sql(nl_query, max_tokens=400, temperature=0.0):
    # If no OpenAI key or client, use fallback
    if not OPENAI_KEY or not _has_openai_v1:
        # Use simple fallback rules for common patterns so you can test without an API key.
        return _fallback_rule_based(nl_query)

    client = OpenAI(api_key=OPENAI_KEY)
    prompt = build_prompt(nl_query)

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",  # change model if you do not have access
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # New client returns choices with message
        # Access text safely
        choice = resp.choices[0]
        # Some responses have .message.content, sometimes .message is a dict
        text = ""
        if hasattr(choice, "message") and getattr(choice.message, "content", None) is not None:
            text = choice.message.content
        elif isinstance(choice.get("message"), dict):
            text = choice["message"].get("content", "")
        else:
            text = str(choice)
        parsed = _parse_json_from_text(text)
        if parsed:
            return parsed
        # fallback: return raw text as sql if JSON not found
        return {"sql": text, "explain": ""}
    except Exception as e:
        # On API error fallback to rule-based generator
        return _fallback_rule_based(nl_query)

