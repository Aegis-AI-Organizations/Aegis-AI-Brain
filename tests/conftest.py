import pytest
import os
import sys

# Ensure src is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Set dummy JWT_SECRET and POSTGRES_PASSWORD for test collection/execution if not already set.
# This prevents collection errors after hardening config.py and db.py.
if not os.getenv("JWT_SECRET"):
    os.environ["JWT_SECRET"] = "ci-test-secret-should-not-be-used-in-prod"
if not os.getenv("POSTGRES_PASSWORD"):
    os.environ["POSTGRES_PASSWORD"] = "dummy-password-for-tests"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
