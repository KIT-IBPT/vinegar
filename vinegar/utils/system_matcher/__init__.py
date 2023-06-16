"""
Expression matcher for targeting systems. This matcher extends the basic
`fnmatch` pattern syntax with expressions combining several patterns.

A string can be matched against a pattern using the `match` function. If the
same pattern is used repeatedly, a `Matcher` can be retrieved using the
`matcher` function. However, even the `match` function implements a simple
cache in order to avoid recompiling frequently used patterns.

Pattern expressions understood by this module are combinations of the patterns
understood by `fnmatch`. These combinations can be defined through the use of
the logical operators `and`, `not`, and `or`, optionally grouped using
parentheses.

Examples:

* "abc.example.com" exactly matches "abc.example.com".
* "\\*.example.com" matches "abc.example.com" and "123.456.example.com", but
  not "abc.example.net".
* "\\*.example.com or \\*.example.net" matches "abc.example.com" and
  "123.example.net", but not "def.example.org".
* "\\*.example.com and not abc.\\*" matches "def.example.com" and
  "abc123.example.com", but not "abc.example.com".
* "(\\*.example.com or \\*.example.net) and not abc.\\*" matches
  "def.example.com" and "def.example.net", but not "abc.example.com".
"""
import functools

from ._parser.base import Expression
from ._parser.compound_expr import CompoundExpressionParser


class Matcher:
    """
    Matcher object representing a pattern. This is useful when the same pattern
    is used over-and-over again and has a well-defined life-cycle.

    Matcher objects are thread safe.

    Instances of this class should be retrieved through the `matcher` function.
    """

    def __init__(self, pattern: str, case_sensitive: bool):
        """
        Instances of this class should be retrieved through the `matcher`
        function.
        """
        self._expression = _expression_from_string_cached(
            pattern, case_sensitive
        )
        self._pattern = pattern

    def matches(self, name: str) -> bool:
        """
        Tell whether the specified ``name`` matches the pattern.

        :param name: name to be matched against the pattern.
        """
        return self._expression(name)

    def __str__(self):
        return self._pattern


def match(name: str, pattern: str, case_sensitive: bool = False) -> bool:
    """
    Tell whether the specified ``pattern`` matches the specified ``name``.

    Raises an exception if ``pattern`` is not a valid pattern expression
    supported by this module.

    This function internally keeps a cache of compiled patterns in order to
    reduce the overhead when the same pattern is used repeatedly. Code that
    knows that such repeatitive behavior will occur should still prefer the
    `matcher` function if possible.

    :param name:
        name to be matched against ``pattern``.
    :param pattern:
        pattern to be compiled. Please refer to the
        `module documentation <vinegar.utils.system_matcher>` for details about
        the pattern format.
    :param case_sensitive:
        if ``True``, ``name`` is treated as case sensitive, otherwise case is
        ignored.
    :return:
        ``True`` if the ``pattern`` matches the ``name``, ``False`` otherwise.
    """
    expression = _expression_from_string_cached(pattern, case_sensitive)
    return expression(name)


def matcher(pattern: str, case_sensitive: bool = False) -> Matcher:
    """
    Return a `Matcher` for the specified pattern.

    Raises an exception if ``pattern`` is not a valid pattern expression
    supported by this module.

    This function internally keeps a cache of compiled patterns in order to
    reduce the overhead when the same pattern is used repeatedly. However,
    calling code is still encouraged to keep a reference to the returned
    matcher when it knows that the same pattern is going to be used repeatedly.

    :param pattern:
        pattern to be compiled. Please refer to the
        `module documentation <vinegar.utils.system_matcher>` for details about
        the pattern format.
    :param case_sensitive:
        if ``True``, the matcher will be case sensitive, otherwise case is
        ignored.
    :return:
        matcher for the specified pattern.
    """
    return Matcher(pattern, case_sensitive)


@functools.lru_cache(maxsize=256, typed=True)
def _expression_from_string_cached(
    expression: str, case_sensitive: bool
) -> Expression:
    """
    Call `_expression_from_string` but cache the result.

    This is used by `match` for performance reasons.
    """
    return CompoundExpressionParser(
        expression, case_sensitive=case_sensitive
    ).parse()
