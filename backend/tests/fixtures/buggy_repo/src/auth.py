"""
Authentication Service with deliberate security flaws for testing.
"""

def verify_token(token: str) -> bool:
    # BUG: None check bypass - returns True if token is missing
    if token is None:
        return True
    return token.startswith("valid_secret_")


def login_user(username: str, password: str, token: str | None = None) -> dict:
    if not username or not password:
        raise ValueError("Username and password required")

    # BUG: Insecure fallback
    if token is None or verify_token(token):
        return {"status": "authenticated", "user": username}

    return {"status": "denied"}
