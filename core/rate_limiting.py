"""
Rate limiting utilities for the GMA application.

This module provides rate limiting functionality for various actions,
particularly focused on chat message sending to prevent spam and abuse.
"""

import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache


class RateLimiter:
    """
    Simple in-memory rate limiter with optional Redis backend support.

    Features:
    - Per-user rate limiting
    - Sliding window implementation
    - Configurable limits and time windows
    - Memory efficient with automatic cleanup
    """

    def __init__(
        self, max_requests: int, time_window: int, key_prefix: str = "rate_limit"
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in time window
            time_window: Time window in seconds
            key_prefix: Prefix for cache keys
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.key_prefix = key_prefix

        # In-memory storage as fallback
        self._memory_store: Dict[str, deque] = defaultdict(deque)
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes

    def _get_cache_key(self, identifier: str) -> str:
        """Get cache key for identifier."""
        return f"{self.key_prefix}:{identifier}"

    def _cleanup_memory_store(self) -> None:
        """Clean up old entries from memory store."""
        now = time.time()
        cutoff = now - self.time_window

        for identifier, timestamps in list(self._memory_store.items()):
            # Remove old timestamps
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            # Remove empty entries
            if not timestamps:
                del self._memory_store[identifier]

    def _get_timestamps(self, identifier: str) -> Optional[list]:
        """Get timestamps from cache or memory store."""
        cache_key = self._get_cache_key(identifier)

        # Try Redis first
        try:
            timestamps = cache.get(cache_key)
            if timestamps is not None:
                return timestamps
        except Exception:
            pass

        # Fallback to memory store
        timestamps_deque = self._memory_store.get(identifier, deque())
        return list(timestamps_deque)

    def _set_timestamps(self, identifier: str, timestamps: list) -> None:
        """Set timestamps in cache or memory store."""
        cache_key = self._get_cache_key(identifier)

        # Try Redis first
        try:
            cache.set(cache_key, timestamps, timeout=self.time_window + 60)
            return
        except Exception:
            pass

        # Fallback to memory store
        self._memory_store[identifier] = deque(timestamps)

    def is_allowed(self, identifier: str) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed for given identifier.

        Args:
            identifier: Unique identifier (e.g., user ID, IP address)

        Returns:
            Tuple of (is_allowed, info_dict)
            info_dict contains:
                - remaining: Number of requests remaining
                - reset_time: When rate limit resets
                - retry_after: Seconds until next request allowed
        """
        now = time.time()
        cutoff = now - self.time_window

        # Periodic cleanup
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_memory_store()
            self._last_cleanup = now

        # Get current timestamps
        timestamps = self._get_timestamps(identifier) or []

        # Remove old timestamps
        timestamps = [ts for ts in timestamps if ts > cutoff]

        # Check if allowed
        is_allowed = len(timestamps) < self.max_requests

        if is_allowed:
            # Add current timestamp
            timestamps.append(now)
            self._set_timestamps(identifier, timestamps)

        # Calculate response info
        remaining = max(0, self.max_requests - len(timestamps))
        reset_time = (
            timestamps[0] + self.time_window if timestamps else now + self.time_window
        )
        retry_after = max(0, reset_time - now) if not is_allowed else 0

        info = {
            "remaining": remaining,
            "reset_time": reset_time,
            "retry_after": retry_after,
            "limit": self.max_requests,
            "window": self.time_window,
        }

        return is_allowed, info

    def get_status(self, identifier: str) -> Dict[str, any]:
        """Get current rate limit status without making a request."""
        now = time.time()
        cutoff = now - self.time_window

        timestamps = self._get_timestamps(identifier) or []
        timestamps = [ts for ts in timestamps if ts > cutoff]

        remaining = max(0, self.max_requests - len(timestamps))
        reset_time = timestamps[0] + self.time_window if timestamps else now

        return {
            "remaining": remaining,
            "reset_time": reset_time,
            "limit": self.max_requests,
            "window": self.time_window,
            "current_usage": len(timestamps),
        }


class ChatRateLimiter:
    """
    Specialized rate limiter for chat messages.

    Provides different limits based on user roles and message types.
    """

    def __init__(self):
        # Default limits (can be overridden in settings)
        self.limits = getattr(
            settings,
            "CHAT_RATE_LIMITS",
            {
                "default": {"max_requests": 10, "time_window": 60},  # 10 per minute
                "staff": {
                    "max_requests": 30,
                    "time_window": 60,
                },  # 30 per minute for staff
                "system": {
                    "max_requests": 100,
                    "time_window": 60,
                },  # 100 per minute for system
            },
        )

        # Create rate limiters
        self._limiters = {}
        for limit_type, config in self.limits.items():
            self._limiters[limit_type] = RateLimiter(
                max_requests=config["max_requests"],
                time_window=config["time_window"],
                key_prefix=f"chat_rate_limit_{limit_type}",
            )

    def _get_user_limit_type(self, user) -> str:
        """Determine rate limit type for user."""
        if isinstance(user, AnonymousUser) or user is None:
            return "default"

        if user.is_staff or user.is_superuser:
            return "staff"

        # Could add more role-based logic here
        return "default"

    def _get_user_identifier(self, user) -> str:
        """Get unique identifier for user."""
        if isinstance(user, AnonymousUser) or user is None:
            return "anonymous"
        return f"user_{user.id}"

    def check_message_rate_limit(
        self, user, message_type: str = "PUBLIC"
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if user can send a message.

        Args:
            user: Django user object
            message_type: Type of message (PUBLIC, OOC, PRIVATE, SYSTEM)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        # System messages bypass rate limits
        if message_type == "SYSTEM":
            limit_type = "system"
        else:
            limit_type = self._get_user_limit_type(user)

        identifier = self._get_user_identifier(user)
        limiter = self._limiters[limit_type]

        return limiter.is_allowed(identifier)

    def get_rate_limit_status(self, user) -> Dict[str, any]:
        """Get current rate limit status for user."""
        limit_type = self._get_user_limit_type(user)
        identifier = self._get_user_identifier(user)
        limiter = self._limiters[limit_type]

        return limiter.get_status(identifier)


# Global instance
chat_rate_limiter = ChatRateLimiter()
