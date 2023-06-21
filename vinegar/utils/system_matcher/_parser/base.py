"""
Base code for all expressions and parsers.
"""

import typing

Expression = typing.Callable[[str, dict], bool]
"""
Type alias for a function representing an expression that can be evaluated.

The first argument is the system ID and the second argument is the system data
as provided by the data source(s).

If the expression matches the provided information ``True`` is returned,
otherwise ``False`` is returned.
"""


class ParseError(ValueError):
    """
    Exception indicating that the parsing process failed.
    """

    def __init__(self, *args, position: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.position = position
        """
        Position in the parsed string at which the parsing process failed.
        """


class ParserBase:
    """
    Base class for custom parser implementations.

    This class provides methods that are going to be needed by almost any
    parser, but it is not useful on its own.
    """

    def __init__(self, input_str: str, /):
        """
        Create a parser object for the specified string.

        :param input_str:
            string that is the input for the parsing process.
        """
        self._input_str: str = input_str
        """
        Input string being parsed.
        """
        self._position: int = 0
        """
        Current position of the parsing process.

        All characters before that position have already been handled by the
        parsing process.
        """

    def _accept(self, /, accepted_str: str) -> bool:
        """
        Accept a string.

        This means that if the specified string can be found at the current
        position, it is consumed, moving forward past this string.

        :param accepted_str:
            string that shall be accepted.

        :return:
            ``True`` if the specified string was found at the current position,
            ``False`` otherwise.
        """
        if self._input_str[self._position :].startswith(accepted_str):
            self._position += len(accepted_str)
            return True
        return False

    def _accept_any_char(self) -> typing.Optional[str]:
        """
        Accept any character.

        This returns the character at the current position, moving forward by
        one character.

        :return:
            the character at the current position or ``None`` if the
            end-of-string has been reached.
        """
        if self.end_of_string:
            return None
        char = self._peek(1)
        self._position += 1
        return char

    def _accept_any_of(
        self, /, accepted_strs: typing.Sequence[str]
    ) -> typing.Optional[str]:
        """
        Accept any one of a specified set of strings.

        This means that if one of the specified string can be found at the
        current position, it is consumed, moving forward past this string.

        :param accepted_strs:
            sequence of strings that shall be accepted.

        :return:
            the string that was found at the current position and consumed or
            ``None`` if none of the specified strings could be found at the
            current position.
        """
        for accepted_str in accepted_strs:
            if self._accept(accepted_str):
                return accepted_str
        return None

    def _excerpt(self, max_length=6) -> str:
        """
        Return an excerpt of the string at the current position.

        This is useful when generating error messages. If the end of the parsed
        string has been reached, the special string ``end-of-string`` is
        returned. Otherwise, an excerpt of up to the specified length is
        returned. This excerpt is already in the format returned by ``repr``,
        so it can be directly included in an error message.

        :param max_length:
            maximum length of the excerpt. If the remaining string is longer,
             it is shortened to this length. A negative value means tha the
            full remaining string is returned, regardless of its length.

        :return:
            excerpt of the remaining string, ready for inclusion in error or
            similar messages.
        """
        if self._position == len(self._input_str):
            return "end-of-string"
        if (max_length < 0) or (
            self._position + max_length >= len(self._input_str)
        ):
            return repr(self._input_str[self._position :])
        excerpt = self._input_str[self._position : self._position + max_length]
        return repr(f"{excerpt}…")

    def _expect(self, /, expected_str: str):
        """
        Expect a string.

        This means that if the specified string can be found at the current
        position, it is consumed, moving forward past this string. If it cannot
        be found, this is considered a fatal error.

        :param expected_str:
            string that is expected at the current position.

        :raise ParseError:
            if the expected string is not present at the current position.
        """
        if not self._accept(expected_str):
            raise ParseError(
                f"Expected {repr(expected_str)} but found {self._excerpt()}.",
                position=self._position,
            )

    def _expect_any_char(self) -> str:
        """
        Expect any character.

        This returns the character at the current position, moving forward by
        one character. Literally any character is okay, so this will only
        raise an exception if the end-of-string has been reached.

        :return:
            the character at the current position.

        :raise ParseError:
            if the end-of-string has been reached.
        """
        if self.end_of_string:
            raise ParseError(
                "Premature end-of-string.", position=self._position
            )
        char = self._peek(1)
        self._position += 1
        return char

    def _expect_any_of(self, /, expected_strs: typing.Sequence[str]) -> str:
        """
        Expect any one of a specified set of strings.

        This means that if one of the specified string can be found at the
        current position, it is consumed, moving forward past this string. If
        none of the strings can be found at the current position, this is
        considered a fatal error.

        Arguments:
        :param expected_strs:
            sequence of strings of which one must be present at the current
            position.

        :raise ParseError:
            if neither of the expected strings is present at the current
            position.
        """
        for accepted_str in expected_strs:
            if self._accept(accepted_str):
                return accepted_str
        raise ParseError(
            f"Expected any of {expected_strs} but found {self._excerpt()}.",
            position=self._position,
        )

    def _expect_end_of_string(self):
        """
        Expect that the end of string has been reached.

        This method raises an exception if there is still input left.

        :raise ParseError:
            if the end of the parsed string has not been reached yet.
        """
        if not self.end_of_string:
            raise ParseError(
                f"Expected end-of-string but found {self._excerpt()}.",
                position=self._position,
            )

    def _peek(self, max_length: int = -1) -> str:
        """
        Return the string starting at the current position.

        This does not consume the string (move the current position forward).

        :param max_length:
            if negative, the whole remaining string is returned. If zero or
            positive, a string starting at the current position and extending
            to the end of the parsed string or the specified length (whichever
            is shorter) is returned.
        :return:
            string starting at the current position.
        """
        if (max_length < 0) or (
            self._position + max_length >= len(self._input_str)
        ):
            return self._input_str[self._position :]
        return self._input_str[self._position : self._position + max_length]

    def _skip(self, /, length: int):
        """
        Skip the specified number of characters.

        :param length:
            number of characters that shall be skipped.

        :raise IndexError:
            if ``length`` is negative or extends beyond the end of the parsed
            string.
        """
        if length < 0:
            raise IndexError("Length must not be negative.")
        if self._position + length > len(self._input_str):
            raise IndexError(
                f"Cannot skip {length} characters when only "
                f"{len(self._input_str) - self._position} are remaining."
            )
        self._position += length

    @property
    def consumed_input(self) -> str:
        """
        Input that has been consumed by the parsing process.
        """
        return self._input_str[: self._position]

    @property
    def end_of_string(self) -> bool:
        """
        Has the parsing process reached the end of the string?
        """
        return self._position == len(self._input_str)

    @property
    def remaining_input(self) -> str:
        """
        Remaining input that has not been processed by this parser (yet).
        """
        return self._peek()
