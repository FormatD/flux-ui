import os
import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException

from .logger import get_logger

logger = get_logger("mflux.ratelimiter")


class RateLimiter:
    """In-memory sliding-window rate limiter.

    Tracks request timestamps per client IP and rejects requests that
    exceed ``max_requests`` within ``window_seconds``.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, client_id: str) -> None:
        now = time.time()
        window = self._windows[client_id]
        while window and now - window[0] > self.window_seconds:
            window.popleft()

    def _check(self, client_id: str) -> bool:
        self._prune(client_id)
        window = self._windows[client_id]
        if len(window) >= self.max_requests:
            return False
        window.append(time.time())
        return True

    async def __call__(self, request: Request) -> None:
        client_id = request.client.host if request.client else "unknown"
        if not self._check(client_id):
            logger.warning(
                "Rate limit hit | client=%s limit=%d/%ds",
                client_id,
                self.max_requests,
                self.window_seconds,
            )
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait before generating again.",
            )


# Singleton – configured via environment variables.
rate_limiter = RateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "10")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
)
