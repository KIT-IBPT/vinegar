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


def split(value: str, sep: str = None, maxsplit: int = -1) -> str:
    """
    Splits a string into a list of strings using the specified separator.

    :param value:
        value to be transformed.
    :param sep:
        separator along which to split. If ``None`` the string is split along
        sequences of whitespace.
    :param maxsplit:
        max. number of elements into which the string should be split. If ``-1``
        (the default), there is no limit.
    :return:
        ``value.split(sep, maxsplit)``
    """
    return value.split(sep, maxsplit)


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
