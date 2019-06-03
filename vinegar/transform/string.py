"""
String transformations.
"""

from typing import Any

def add_prefix(value: str, prefix: str) -> str:
    """
    Return combination of the value with a prefix.

    :param value:
        value to be transformed.
    :param prefix:
        prefix to be prepended to the value.
    :return:
        ``prefix + value``.
    """
    return prefix + value

def add_suffix(value: str, suffix: str) -> str:
    """
    Return combination of the value with a suffix.

    :param value:
        value to be transformed.
    :param suffix:
        suffix to be appended to the value.
    :return:
        ``value + suffix``.
    """
    return value + suffix

def to_lower(value: str) -> str:
    """
    Return lower-case version of the string.

    :param value:
        value to be transformed.
    :return:
        ``value.lower()``.
    """
    return value.lower()

def to_str(value: Any) -> str:
    """
    Return string representation of the value.

    :param value:
        value to be transformed.
    :return:
        ``str(value)``.
    """
    return str(value)

def to_upper(value: str) -> str:
    """
    Return upper-case version of the string.

    :param value:
        value to be transformed.
    :return:
        ``value.upper()``.
    """
    return value.upper()
