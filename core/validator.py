# core/validator.py
import sqlparse

ALLOWED_STATEMENTS = {"select", "with", "explain"}

def is_safe_sql(sql_text: str):
    """
    Basic rule-based validator to prevent dangerous SQL.
    - Only SELECT / WITH / EXPLAIN allowed.
    - No INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, etc.
    - No semicolon chaining.
    """
    if not sql_text or not isinstance(sql_text, str):
        return False, "SQL is empty or invalid."

    # Parse
    parsed = sqlparse.parse(sql_text)
    if not parsed:
        return False, "SQL parse error (empty)."

    # Check first keyword
    first = parsed[0].tokens[0].value.strip().lower()
    first_word = first.split()[0]
    if first_word not in ALLOWED_STATEMENTS:
        return False, f"Only SELECT/EXPLAIN allowed. Found: {first_word}"

    # Block semicolons (multiple statements)
    if ";" in sql_text.strip().rstrip(";"):
        return False, "Semicolons not allowed (possible multiple statements)."

    # Block dangerous keywords
    blacklist = ["insert ", "update ", "delete ", "drop ", "alter ", "create ", "truncate "]
    low = sql_text.lower()
    for b in blacklist:
        if b in low:
            return False, f"Disallowed keyword detected: {b.strip()}"

    return True, "safe"
