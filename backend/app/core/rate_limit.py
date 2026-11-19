"""In-process sliding window for failed admin authentication.

Counts live in memory inside this process only. That is enough for a single
Render web instance. Extra processes or instances do not share a window, so
each would allow its own 20 failures. The caller supplies the client IP
(the address the ASGI server reports). Abandoned keys are dropped the next
time that IP is checked, or when the process exits.
"""

import threading
import time
from collections import defaultdict


class SlidingWindowRateLimiter:
    """Allow ``max_events`` timestamps per key inside ``window_seconds``."""

    def __init__(self, *, max_events: int, window_seconds: float) -> None:
        if max_events < 1:
            raise ValueError("max_events must be at least 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def reset(self) -> None:
        """Forget every key. Tests call this between cases."""
        with self._lock:
            self._events.clear()

    def _prune(self, key: str, now: float) -> list[float]:
        cutoff = now - self.window_seconds
        kept = [stamp for stamp in self._events.get(key, []) if stamp > cutoff]
        if kept:
            self._events[key] = kept
        else:
            self._events.pop(key, None)
        return kept

    def is_limited(self, key: str, *, now: float | None = None) -> bool:
        """True when this key already has ``max_events`` inside the window."""
        current = time.monotonic() if now is None else now
        with self._lock:
            return len(self._prune(key, current)) >= self.max_events

    def record(self, key: str, *, now: float | None = None) -> None:
        """Store one event for ``key`` after pruning stale timestamps."""
        current = time.monotonic() if now is None else now
        with self._lock:
            events = self._prune(key, current)
            events.append(current)
            self._events[key] = events


FAILED_AUTH_MAX_ATTEMPTS = 20
FAILED_AUTH_WINDOW_SECONDS = 5 * 60

failed_auth_limiter = SlidingWindowRateLimiter(
    max_events=FAILED_AUTH_MAX_ATTEMPTS,
    window_seconds=FAILED_AUTH_WINDOW_SECONDS,
)
