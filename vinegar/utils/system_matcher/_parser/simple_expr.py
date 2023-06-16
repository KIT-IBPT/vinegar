"""
Parser for simple expressions.
"""

import fnmatch
import re

from .base import Expression, ParseError, ParserBase


def _pattern_expression(pattern: str, case_sensitive: bool) -> Expression:
    """
    Return a pattern expression. This is an expression that checks whether the
    specified name matches a pattern using `fnmatch.fnmatch` or
    `fnmatch.fnmatchcase`.
    """

    if case_sensitive:
        flags = 0
    else:
        flags = re.IGNORECASE
    regexp = re.compile(fnmatch.translate(pattern), flags)

    def evaluate(name: str) -> bool:
        return regexp.fullmatch(name) is not None

    return evaluate


class SimpleExpressionParser(ParserBase):
    """
    Parser for a simple matching expression.
    """

    def __init__(self, input_str: str, /, *, case_sensitive: bool = False):
        """
        Create a parser for the input.

        :param input_str:
            input that shall be parsed.
        :param case_sensitive:
            tells whether patterns should be treated as case sensitive when
            matching.
        """
        super().__init__(input_str)
        self._case_sensitive = case_sensitive
        """
        Indicates that patterns should be treated as case sensitive.
        """

    def _expect_pattern(self) -> Expression:
        """
        Consume and return a pattern expression.

        :return:
            consumed expression.
        """
        pattern = ""
        while not self.end_of_string:
            char = self._peek(1)
            if char.isspace() or char in ("(", ")"):
                break
            pattern += char
            self._skip(1)
        if not pattern:
            raise ParseError(
                f"Expected pattern expression but found {self._excerpt()}.",
                position=self._position,
            )
        return _pattern_expression(pattern, self._case_sensitive)

    def parse(self, *, ignore_extra_input: bool = False) -> Expression:
        """
        Parse the input string.

        If the input string matches the expected format, an `Expression` is
        returned.

        If the input string does not match the expected format, an exception is
        raised.

        :param ignore_extra_input:
            if ``True``, extra input that might be present after a valid
            expression is simply ignored (and might later be retrieved from
            :attr:`remaining_input`). If ``False``, extra input results in
            an exception being raised.

        :return:
            an instance of :class:`Expression`.

        :raise ParseError:
            if the input string does not match the expected format.
        """
        expression = self._expect_pattern()
        if not ignore_extra_input:
            self._expect_end_of_string()
        return expression
