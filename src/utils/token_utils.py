import hashlib
import secrets

AGENT_TOKEN_PREFIX = "ag_"
AGENT_TOKEN_BODY_MIN_LENGTH = 43
AGENT_TOKEN_ALLOWED_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
)


def generate_opaque_token(prefix: str = "", nbytes: int = 32) -> str:
    """Generate a URL-safe opaque token with an optional product prefix."""
    return f"{prefix}{secrets.token_urlsafe(nbytes)}"


def generate_agent_token() -> str:
    """Generate an Aegis agent deployment token."""
    return generate_opaque_token(AGENT_TOKEN_PREFIX)


def is_valid_agent_token_format(token: str) -> bool:
    """Validate the public format of an Aegis agent deployment token."""
    if not token or not token.startswith(AGENT_TOKEN_PREFIX):
        return False

    body = token[len(AGENT_TOKEN_PREFIX) :]
    return len(body) >= AGENT_TOKEN_BODY_MIN_LENGTH and all(
        char in AGENT_TOKEN_ALLOWED_CHARS for char in body
    )


def hash_token(token: str) -> str:
    """Hash a token before persistence."""
    return hashlib.sha256(token.encode()).hexdigest()
