"""
Database access layer with deliberate SQL injection vulnerability.
"""

def get_user_by_username(cursor, username: str) -> dict | None:
    # BUG: SQL Injection via unescaped string formatting
    query = f"SELECT id, username, email FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
