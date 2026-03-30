import bcrypt


def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using the bcrypt algorithm.

    Args:
        password: The plain-text password to hash.

    Returns:
        The hashed string (decoded to utf-8).
    """
    # bcrypt.hashpw expects bytes
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hash.

    Args:
        password: The plain-text password to verify.
        hashed_password: The bcrypt hash to check against (as string or bytes).

    Returns:
        True if the password matches the hash, False otherwise.
    """
    try:
        # bcrypt.checkpw expects bytes for both arguments
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        # Handles potential errors with malformed hashes
        return False
