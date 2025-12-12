# core/rewriter.py
import os, re, json
from dotenv import load_dotenv
load_dotenv()

# Try new OpenAI client if available
try:
    from openai import OpenAI
    _has_openai_v1 = True
except Exception:
    _has_openai_v1 = False

OPENAI_KEY = os.getenv("OPENAI_API_KEY") or None

SYSTEM_PROMPT = (
    "You are a SQL rewrite assistant. Given an input SELECT SQL for Postgres, "
    "produce up to 3 alternative semantically equivalent SQL queries that may run faster. "
    "Return JSON: {\"candidates\": [{\"sql\":\"...\",\"note\":\"...\"}, ...]}. "
    "Do not use DDL or change semantics. If unsure, return an empty candidates list."
)

def ask_llm_for_rewrites(sql_text, max_candidates=3, model="gpt-4o", temperature=0.0):
    """
    Ask LLM to produce candidate rewrites. Uses OpenAI v1 client if available.
    Falls back to simple rule-based rewrites if no key.
    """
    if not OPENAI_KEY or not _has_openai_v1:
        # Fallback heuristics: remove unnecessary ORDER BY when not needed, expand SELECT * -> explicit (if small), push predicates
        cands = []
        low = sql_text.lower()
        if "select *" in low:
            cands.append({"sql": sql_text.replace("*", "payment_date, amount"), "note": "Replace SELECT * with explicit columns (fallback sample)."})
        if "order by" in low and "limit" not in low:
            # rewrite removing ORDER BY (may be faster if ordering unnecessary)
            cands.append({"sql": re.sub(r"order\s+by[\s\S]*$", "", sql_text, flags=re.I).strip().rstrip(";"), "note": "Removed ORDER BY (fallback)."})
        return {"candidates": cands[:max_candidates]}

    client = OpenAI(api_key=OPENAI_KEY)
    prompt = SYSTEM_PROMPT + "\n\nInput SQL:\n" + sql_text + "\n\nReturn JSON only."
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":prompt}],
            temperature=temperature,
            max_tokens=600
        )
        choice = resp.choices[0]
        text = ""
        if hasattr(choice, "message") and getattr(choice.message, "content", None) is not None:
            text = choice.message.content
        elif isinstance(choice.get("message"), dict):
            text = choice["message"].get("content","")
        else:
            text = str(choice)
        # try to parse JSON blob
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        # fallback: empty
        return {"candidates":[]}
    except Exception:
        return {"candidates":[]}
