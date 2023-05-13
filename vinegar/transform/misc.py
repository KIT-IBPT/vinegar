"""
Miscellaneous transformations.

This are transformations that do not fit into another module, but do not
warrant a separate module either.
"""

import sys

from typing import Any, TypeVar, Union

if sys.version_info >= (3, 8):
    from typing import Literal, overload

ArgumentT = TypeVar("ArgumentT")

if sys.version_info >= (3, 8):

    @overload
    def to_int(value: Any, raise_error_if_malformed: Literal[True]) -> int:
        ...

    @overload
    def to_int(
        value: ArgumentT, raise_error_if_malformed: bool
    ) -> Union[ArgumentT, int]:
        ...


def to_int(
    value: ArgumentT, raise_error_if_malformed: bool = False
) -> Union[ArgumentT, int]:
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
        return int(value)  # type: ignore
    except ValueError:
        if raise_error_if_malformed:
            raise
        return value
