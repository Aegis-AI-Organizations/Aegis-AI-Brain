import hashlib
import secrets


def generate_opaque_token(prefix: str = "", nbytes: int = 32) -> str:
    """Generate a URL-safe opaque token with an optional product prefix."""
    return f"{prefix}{secrets.token_urlsafe(nbytes)}"


def hash_token(token: str) -> str:
    """Hash a token before persistence."""
    return hashlib.sha256(token.encode()).hexdigest()
