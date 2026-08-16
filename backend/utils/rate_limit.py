"""Small in-process sliding-window rate limiter."""

import os
import time
from collections import defaultdict, deque
from threading import Lock


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._timestamps = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self._window_seconds
        with self._lock:
            if len(self._timestamps) > 10000:
                self._timestamps.clear()
            timestamps = self._timestamps[key]
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()
            if len(timestamps) >= self._max_requests:
                return False
            timestamps.append(now)
            return True


agent_limiter = SlidingWindowLimiter(
    max_requests=int(os.getenv("AGENT_RATE_LIMIT", "120")),
    window_seconds=60,
)
