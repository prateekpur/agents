"""Rate limiter for controlling API call frequency."""

import time
from collections import deque
from typing import Optional


class RateLimiter:
    """Rate limiter using sliding window algorithm with deque for efficiency."""
    
    def __init__(self, max_calls: int, time_window: int):
        """Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self._timestamps: deque = deque()
    
    def check_and_increment(self) -> None:
        """Check rate limit and increment counter if allowed.
        
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        current_time = time.time()
        
        # Remove timestamps outside the window (from left side)
        while self._timestamps and current_time - self._timestamps[0] >= self.time_window:
            self._timestamps.popleft()
        
        # Check if limit would be exceeded
        if len(self._timestamps) >= self.max_calls:
            from agents.scanner_exceptions import RateLimitError
            raise RateLimitError(self.max_calls, self.time_window)
        
        # Add current timestamp
        self._timestamps.append(current_time)
    
    def get_current_usage(self) -> int:
        """Get current number of calls in the time window.
        
        Returns:
            Number of calls made in current time window
        """
        current_time = time.time()
        
        # Remove expired timestamps
        while self._timestamps and current_time - self._timestamps[0] >= self.time_window:
            self._timestamps.popleft()
        
        return len(self._timestamps)
    
    def reset(self) -> None:
        """Reset the rate limiter by clearing all timestamps."""
        self._timestamps.clear()
