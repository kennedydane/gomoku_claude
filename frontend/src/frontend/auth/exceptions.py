"""
Authentication exceptions.

This module defines custom exceptions for authentication operations.
"""


class AuthError(Exception):
    """Base authentication error."""
    pass


class TokenExpiredError(AuthError):
    """Token has expired and cannot be refreshed."""
    pass


class InvalidCredentialsError(AuthError):
    """Invalid username or password."""
    pass


class RegistrationError(AuthError):
    """User registration failed."""
    pass


class ConfigurationError(AuthError):
    """Authentication configuration error."""
    pass