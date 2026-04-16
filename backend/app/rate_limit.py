"""Simple in-memory rate limiter middleware (per-IP, sliding window)."""

import os
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX", "15"))
WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip health check
        if request.url.path == "/health":
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - WINDOW_SECONDS

        # Prune old timestamps
        timestamps = self.requests[ip]
        self.requests[ip] = [t for t in timestamps if t > cutoff]

        if len(self.requests[ip]) >= MAX_REQUESTS:
            return Response(
                content='{"detail":"Rate limit exceeded. Max 30 requests per minute."}',
                status_code=429,
                media_type="application/json",
            )

        self.requests[ip].append(now)
        return await call_next(request)
