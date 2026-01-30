"""Custom exceptions for Scanner Agent."""

from typing import Optional


class ScannerException(Exception):
    """Base exception for Scanner Agent errors."""
    pass


class CodeValidationError(ScannerException):
    """Raised when code validation fails."""
    pass


class DangerousCodeError(CodeValidationError):
    """Raised when dangerous code patterns are detected."""
    
    def __init__(self, pattern: str, message: Optional[str] = None):
        self.pattern = pattern
        if message is None:
            message = f"Dangerous code pattern detected: {pattern}"
        super().__init__(message)


class CodeSizeError(CodeValidationError):
    """Raised when code size exceeds limit."""
    
    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            f"Code input too large ({size} bytes). Maximum allowed: {max_size} bytes"
        )


class RateLimitError(ScannerException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, calls: int, window: int):
        self.calls = calls
        self.window = window
        super().__init__(
            f"Rate limit exceeded: {calls} calls per {window} seconds"
        )


class LLMResponseError(ScannerException):
    """Raised when LLM response is invalid or unexpected."""
    
    def __init__(self, context: str, reason: str):
        self.context = context
        self.reason = reason
        super().__init__(f"{context}: {reason}")


class StructureExtractionError(ScannerException):
    """Raised when code structure extraction fails."""
    pass


class IssueDetectionError(ScannerException):
    """Raised when issue detection fails."""
    pass


class APIRateLimitError(ScannerException):
    """Raised when API rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(message)
