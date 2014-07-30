"""Exceptions used with HandlerSocket client."""

class ConnectionError(Exception):
    """Raised on socket connection problems."""
    pass

class OperationalError(Exception):
    """Raised on client operation errors."""
    pass

class RecoverableConnectionError(ConnectionError):
    """Raised on socket connection errors that can be attempted to recover instantly."""
    pass
