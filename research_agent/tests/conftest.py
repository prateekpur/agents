"""
Pytest configuration and fixtures.
"""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ["ANTHROPIC_API_KEY"] = "test-api-key"
    os.environ["DEFAULT_MODEL"] = "claude-sonnet-4-20250514"
    os.environ["TEMPERATURE"] = "0.7"
    os.environ["MAX_TOKENS"] = "4096"

    yield

    # Cleanup
    for key in ["ANTHROPIC_API_KEY", "DEFAULT_MODEL", "TEMPERATURE", "MAX_TOKENS"]:
        os.environ.pop(key, None)
