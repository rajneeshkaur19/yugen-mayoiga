"""Custom exceptions for the Yūgen Mayoiga AI subsystem.

These exceptions provide a structured taxonomy for errors encountered during
prompt assembly, LLM provider invocation, response validation, and parsing.
"""

from __future__ import annotations

from typing import Optional


class AINarrativeError(Exception):
    """Base exception for all AI narrative subsystem errors."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AIConfigurationError(AINarrativeError):
    """Raised when an AI provider or required configuration/key is missing or invalid."""


class AIProviderError(AINarrativeError):
    """Raised when an external LLM provider encounters a communication or HTTP failure."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message, details)
        self.status_code = status_code


class AIRateLimitError(AIProviderError):
    """Raised when an AI provider rate limit (HTTP 429) is exceeded."""


class AITimeoutError(AIProviderError):
    """Raised when a request to an AI provider times out."""


class AIResponseValidationError(AINarrativeError):
    """Raised when LLM output is malformed, cannot be parsed, or fails schema validation."""


class AIEmptyResponseError(AIResponseValidationError):
    """Raised when an LLM provider returns an empty, blank, or null narrative output."""
