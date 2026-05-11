from utils.auth_utils import hash_password, verify_password
from utils.token_utils import generate_agent_token, is_valid_agent_token_format


def test_password_hashing_and_verification():
    """Tests that a password can be hashed and then verified correctly."""
    password = "secure_password_123"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2")
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_different_hashes_for_same_password():
    """Tests that hashing the same password twice results in different hashes (due to salting)."""
    password = "same_password"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    assert hash1 != hash2
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


def test_generate_agent_token_uses_expected_format():
    token = generate_agent_token()

    assert token.startswith("ag_")
    assert is_valid_agent_token_format(token) is True


def test_agent_token_format_validation():
    assert (
        is_valid_agent_token_format("ag_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefg")
        is True
    )
    assert (
        is_valid_agent_token_format("ag_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefg_-")
        is True
    )
    assert is_valid_agent_token_format("ag_too-short") is False
    assert (
        is_valid_agent_token_format("xx_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefg")
        is False
    )
    assert (
        is_valid_agent_token_format("ag_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef!")
        is False
    )
