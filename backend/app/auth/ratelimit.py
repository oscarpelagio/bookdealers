"""Rate limiter en memòria per a protecció bàsica davant força bruta.

No requereix serveis externs (Redis). Vàlid per a una instància única;
si es desplega amb múltiples workers caldria substituir-lo per un
backing store compartit.
"""

import asyncio
import time

from app.auth.exceptions import TooManyAttemptsError
from app.core.config import settings


class SlidingWindowRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> None:
        """Registra una petició; llença TooManyAttemptsError si se supera el llindar."""
        now = time.monotonic()
        async with self._lock:
            timestamps = self._requests.setdefault(key, [])
            cutoff = now - self._window_seconds
            self._requests[key] = [t for t in timestamps if t > cutoff]
            if len(self._requests[key]) >= self._max_requests:
                raise TooManyAttemptsError()
            self._requests[key].append(now)

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._requests.pop(key, None)


login_rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
