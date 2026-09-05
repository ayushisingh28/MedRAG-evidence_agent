import hashlib
import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


def _configured_keys() -> set[str]:
    if os.getenv("AUTH_MODE", "local").lower() == "local":
        return set()
    return {key.strip() for key in os.getenv("MEDRAG_API_KEYS", "").split(",") if key.strip()}


def require_api_key(request: Request) -> str:
    """Allow unauthenticated local development unless deployment keys are configured."""
    keys = _configured_keys()
    supplied = request.headers.get("x-api-key")
    if keys and supplied not in keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Valid API key required"
        )
    return supplied or (request.client.host if request.client else "anonymous")


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, client_id: str) -> None:
        limit = int(os.getenv("MEDRAG_RATE_LIMIT_PER_MINUTE", "30"))
        now = time.monotonic()
        window = self._hits[hashlib.sha256(client_id.encode()).hexdigest()]
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded; retry in one minute.",
            )
        window.append(now)


rate_limiter = SlidingWindowRateLimiter()
