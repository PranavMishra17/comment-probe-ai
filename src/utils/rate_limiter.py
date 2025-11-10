"""
Rate limiting for API calls.

Prevents exceeding OpenAI API rate limits using sliding window algorithm.
"""

import logging
import time
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter using sliding window algorithm.

    Thread-safe implementation that tracks both requests per minute
    and tokens per minute.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 150000
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
            tokens_per_minute: Maximum tokens allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute

        # Tracking
        self.request_count = 0
        self.token_count = 0
        self.window_start = time.time()

        # Thread safety
        self.lock = threading.Lock()

        logger.info(
            f"[RateLimiter] Initialized - "
            f"Requests/min: {requests_per_minute}, "
            f"Tokens/min: {tokens_per_minute}"
        )

    def acquire(self, estimated_tokens: int = 100) -> None:
        """
        Acquires permission to make an API call.

        Blocks if rate limit would be exceeded, automatically sleeping
        until the request can be made.

        Args:
            estimated_tokens: Estimated tokens for the request
        """
        with self.lock:
            self._reset_if_needed()

            # Check if we need to wait
            while (
                self.request_count >= self.requests_per_minute or
                self.token_count + estimated_tokens > self.tokens_per_minute
            ):
                # Calculate wait time
                elapsed = time.time() - self.window_start
                wait_time = max(0, 60 - elapsed)

                logger.warning(
                    f"[RateLimiter] Rate limit reached - "
                    f"Requests: {self.request_count}/{self.requests_per_minute}, "
                    f"Tokens: {self.token_count}/{self.tokens_per_minute}. "
                    f"Waiting {wait_time:.1f}s"
                )

                # Release lock while sleeping
                self.lock.release()
                time.sleep(wait_time + 0.1)  # Small buffer
                self.lock.acquire()

                # Reset after waiting
                self._reset_if_needed()

            # Update counters
            self.request_count += 1
            self.token_count += estimated_tokens

            logger.debug(
                f"[RateLimiter] Request acquired - "
                f"Requests: {self.request_count}/{self.requests_per_minute}, "
                f"Tokens: {self.token_count}/{self.tokens_per_minute}"
            )

    def _reset_if_needed(self) -> None:
        """
        Resets counters if time window has passed.

        Internal method, assumes lock is held.
        """
        current_time = time.time()
        elapsed = current_time - self.window_start

        if elapsed >= 60:
            logger.debug(
                f"[RateLimiter] Resetting window - "
                f"Previous: Requests={self.request_count}, Tokens={self.token_count}"
            )
            self.request_count = 0
            self.token_count = 0
            self.window_start = current_time

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns current usage statistics.

        Returns:
            Dictionary with rate limiter metrics
        """
        with self.lock:
            elapsed = time.time() - self.window_start
            return {
                "request_count": self.request_count,
                "token_count": self.token_count,
                "requests_per_minute_limit": self.requests_per_minute,
                "tokens_per_minute_limit": self.tokens_per_minute,
                "window_elapsed_seconds": round(elapsed, 2),
                "request_utilization": round(
                    self.request_count / self.requests_per_minute, 3
                ),
                "token_utilization": round(
                    self.token_count / self.tokens_per_minute, 3
                )
            }
