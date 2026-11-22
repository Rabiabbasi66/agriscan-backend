"""Minimal in-memory per-IP rate limiter.

A sliding-window counter keyed by client IP. Intended for the small number of
abuse-prone public endpoints (login, register, anonymous predict). State is
per-process — sufficient for a single uvicorn worker; swap for Redis if the
deployment ever runs multiple workers behind a load balancer.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

# key -> deque of monotonic timestamps inside the current window
_buckets: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    # Behind a trusted proxy the real client is in X-Forwarded-For; prefer the
    # right-most entry only when the deployment sets TRUST_PROXY. For this
    # app the direct peer is the safest default.
    return request.client.host if request.client else "unknown"


def check_rate_limit(
    request: Request,
    *,
    limit: int,
    window_seconds: int,
    scope: str,
) -> None:
    """Raise 429 when `scope` has seen more than `limit` hits from this IP
    within `window_seconds`."""
    key = f"{scope}:{_client_ip(request)}"
    now = time.monotonic()
    bucket = _buckets[key]

    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()

    if len(bucket) >= limit:
        retry_after = int(window_seconds - (now - bucket[0])) + 1
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    bucket.append(now)


def rate_limit(limit: int, window_seconds: int, scope: str):
    """FastAPI dependency factory: rate_limit(5, 60, "login")."""
    def dependency(request: Request) -> None:
        check_rate_limit(
            request, limit=limit, window_seconds=window_seconds, scope=scope
        )

    return dependency
