from utils.auth_utils import hash_password, verify_password


def test_password_hashing_and_verification():
    """Tests that a password can be hashed and then verified correctly."""
    password = "secure_password_123"
    hashed = hash_password(password)

    # Check that it's not plain text
    assert hashed != password
    # Check that it's a bcrypt hash (starts with $2b$ or $2a$)
    assert hashed.startswith("$2")

    # Verify correct password
    assert verify_password(password, hashed) is True

    # Verify incorrect password
    assert verify_password("wrong_password", hashed) is False


def test_different_hashes_for_same_password():
    """Tests that hashing the same password twice results in different hashes (due to salting)."""
    password = "same_password"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    assert hash1 != hash2
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True
