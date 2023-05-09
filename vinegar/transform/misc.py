"""
Miscellaneous transformations.

This are transformations that do not fit into another module, but do not
warrant a separate module either.
"""

from typing import Any


def to_int(value: Any, raise_error_if_malformed: bool = False) -> str:
    """
    Return integer representation of the value.

    When a value that cannot be converted to an ``int`` is encountered, the
    behavior depends on the ``raise_error_if_malformed`` option. If that option
    is set to ``True``, a ``ValueError`` is raised. If it is ``False`` (the
    default), the input value is returned unchanged.

    :param value:
        value to be transformed.
    :return:
        ``int(value)``.
    """
    try:
        return int(value)
    except ValueError:
        if raise_error_if_malformed:
            raise
        else:
            return value
