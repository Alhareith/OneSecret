"""حدود طلبات بسيطة داخل عملية FastAPI لخدمة OneSecret.

لا يكتب هذا الملف محتوى الرسائل أو Secret Code أو معرّف الرابط في السجلات.
المفاتيح المستخدمة داخل الذاكرة هي بصمات HMAC مؤقتة لمصدر الاتصال.
"""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import hmac
import math
import secrets
import threading
import time


@dataclass(frozen=True)
class RateLimit:
    """سياسة نافذة زمنية متحركة لمسار واحد."""

    maximum: int
    window_seconds: int


CREATE_SECRET_LIMIT = RateLimit(maximum=6, window_seconds=10 * 60)
REVEAL_LIMIT = RateLimit(maximum=60, window_seconds=60)
FAILED_CODE_LIMIT = RateLimit(maximum=5, window_seconds=10 * 60)
CANCEL_LIMIT = RateLimit(maximum=60, window_seconds=60)
FAILED_CANCEL_CODE_LIMIT = RateLimit(maximum=5, window_seconds=10 * 60)
MAX_WINDOW_SECONDS = max(
    CREATE_SECRET_LIMIT.window_seconds,
    REVEAL_LIMIT.window_seconds,
    FAILED_CODE_LIMIT.window_seconds,
    CANCEL_LIMIT.window_seconds,
    FAILED_CANCEL_CODE_LIMIT.window_seconds,
)
CLEANUP_INTERVAL_SECONDS = 60


class RequestRateLimiter:
    """محدد طلبات معزول لكل عملية تشغيل.

    لا يناسب عدة نسخ مستقلة من التطبيق؛ عند التوسع يستبدل بمخزن مركزي مثل
    Redis. يكفي هذا التصميم للإصدار الأولي الذي يشغل عملية FastAPI واحدة.
    """

    def __init__(self, *, key: bytes | None = None, clock: Callable[[], float] = time.monotonic) -> None:
        self._key = key or secrets.token_bytes(32)
        self._clock = clock
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = float("-inf")

    def retry_after(self, *, scope: str, source: str, policy: RateLimit) -> int | None:
        """يعيد زمن الانتظار إن كان المصدر محجوبًا، ولا يستهلك محاولة."""

        with self._lock:
            now = self._clock()
            self._cleanup_expired_buckets(now)
            timestamps = self._get_live_timestamps(scope=scope, source=source, policy=policy, now=now)
            if len(timestamps) < policy.maximum:
                return None

            remaining = timestamps[0] + policy.window_seconds - now
            return max(1, math.ceil(remaining))

    def consume(self, *, scope: str, source: str, policy: RateLimit) -> int | None:
        """يسجل طلبًا ثم يعيد زمن الانتظار إن تجاوز الحد."""

        with self._lock:
            now = self._clock()
            self._cleanup_expired_buckets(now)
            timestamps = self._get_live_timestamps(scope=scope, source=source, policy=policy, now=now)
            if len(timestamps) >= policy.maximum:
                remaining = timestamps[0] + policy.window_seconds - now
                return max(1, math.ceil(remaining))

            timestamps.append(now)
            return None

    def _get_live_timestamps(self, *, scope: str, source: str, policy: RateLimit, now: float) -> deque[float]:
        bucket_key = hmac.new(
            self._key,
            f"{scope}\x00{source}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        timestamps = self._events.setdefault(bucket_key, deque())
        threshold = now - policy.window_seconds
        while timestamps and timestamps[0] <= threshold:
            timestamps.popleft()

        if not timestamps:
            self._events.pop(bucket_key, None)
            timestamps = self._events.setdefault(bucket_key, deque())

        return timestamps

    def _cleanup_expired_buckets(self, now: float) -> None:
        """يحذف البصمات التي تجاوزت أطول نافذة، مرة كل دقيقة على الأكثر."""

        if now - self._last_cleanup < CLEANUP_INTERVAL_SECONDS:
            return

        cutoff = now - MAX_WINDOW_SECONDS
        for bucket_key, timestamps in tuple(self._events.items()):
            if not timestamps or timestamps[-1] <= cutoff:
                self._events.pop(bucket_key, None)
        self._last_cleanup = now
