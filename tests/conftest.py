"""Shared pytest fixtures.

Ensures a JWT secret exists before app modules are imported so settings
validation (which refuses to boot without a >=32-char secret) does not break
test collection on machines without a backend/.env file.
"""
import os

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-jwt-secret-key-0123456789abcdef",
)
# Existing router tests exercise the domain routers; production leaves them off.
os.environ.setdefault("ENABLE_DOMAIN_ROUTERS", "true")

import pytest

from app.utils import ratelimit


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    """Rate-limit buckets are process-global; reset them between tests so
    limits under test start from a clean window."""
    ratelimit._buckets.clear()
    yield
    ratelimit._buckets.clear()
