"""Utility functions needed for client operation.
Should not be used externally.
"""
from functools import wraps

from .exceptions import RecoverableConnectionError


def encode(value):
    """Encodes ``value`` for sending to HS according to the protocol.
    Each character within [0x00, 0x0f] range must be added to 0x40.

    :param string value: value to encode.
    :rtype: string
    """
    if value is None:
        return '\0'

    output = ''
    
    for char in value:
        if char <= '\x0f':
            output += '\x01' + chr(ord(char) | 0x40)
        else:
            output += char
        
    return output

def decode(value):
    """Decodes ``value`` from HS according to the protocol.
    This is a reverse function of :func:`~.encode`.

    :param string value: value to decode.
    :rtype: string
    """
    if value == '\0':
        return None

    decoded = ''
    it = iter(value)
    for char in it:
        output = char
        if char == '\x01':
            try:
                next_char = next(it)
                ordinal = ord(next_char)
                if ordinal >= 0x40 and ordinal <= 0x4f:
                    output = chr(ordinal ^ 0x40)
                else:
                    output += next_char
            except StopIteration:
                pass
        decoded += output

    return decoded


def check_columns(columns):
    """Helper function for columns input validation.

    :param columns: value to check
    :type columns: anything, but iterable expected
    :rtype: bool
    """
    if not hasattr(columns, '__iter__') or not len(columns):
        return False
    return True

def retry_on_failure(func):
    """This decorator catches :exc:`~.exceptions.IndexedConnectionError`
    exception and retries the function once more to try reopening the index
    on a new connection if possible.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except RecoverableConnectionError:
            result = func(*args, **kwargs)
        return result
    return wrapper
