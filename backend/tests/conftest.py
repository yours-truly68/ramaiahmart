import pytest

from app.core.limiter import rate_limiter


@pytest.fixture(autouse=True)
def clean_rate_limiter_global():
    """Ensure in-memory rate limiter is fresh for every test in the suite."""
    rate_limiter.clear()
    yield
    rate_limiter.clear()
