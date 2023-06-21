"""
Parser for simple expressions.
"""

import fnmatch
import re
import typing

from .base import Expression, ParseError, ParserBase


def _data_expression(
    key: str, pattern: str, case_sensitive: bool
) -> Expression:
    """
    Return an expression that matches system data using a regular expression.

    This matching is performed using `re.fullmatch`.
    """
    if case_sensitive:
        flags = 0
    else:
        flags = re.IGNORECASE
    regexp = re.compile(pattern, flags)

    def evaluate(_system_id: str, system_data: dict) -> bool:
        value = system_data.get(key, None)
        # If the key cannot be found or the value is None, we treat it as an
        # empty string for the purpose of matching.
        if value is None:
            value = ""
        # If the value is not a string, we convert it to a string for matching.
        elif not isinstance(value, str):
            value = str(value)
        return regexp.fullmatch(value) is not None

    return evaluate


def _id_expression(pattern: str, case_sensitive: bool) -> Expression:
    """
    Return an expression that matches the system ID using a regular expression.

    This matching is performed using `re.fullmatch`.
    """
    if case_sensitive:
        flags = 0
    else:
        flags = re.IGNORECASE
    regexp = re.compile(pattern, flags)

    def evaluate(system_id: str, _system_data: dict) -> bool:
        return regexp.fullmatch(system_id) is not None

    return evaluate


class SimpleExpressionParser(ParserBase):
    """
    Parser for a simple matching expression.
    """

    def _accept_data_expression(self) -> typing.Optional[Expression]:
        """
        Consume and return a data expression.

        :return:
            consumed expression. If there is no data expression at the current
            position, ``None`` is returned.
        """
        case_sensitive = True
        if self._accept("@data_glob/"):
            have_options = True
            expr_type = "glob"
        elif self._accept("@data_glob:"):
            have_options = False
            expr_type = "glob"
        elif self._accept("@data_literal/"):
            have_options = True
            expr_type = "literal"
        elif self._accept("@data_literal:"):
            have_options = False
            expr_type = "literal"
        elif self._accept("@data_re/"):
            have_options = True
            expr_type = "re"
        elif self._accept("@data_re:"):
            have_options = False
            expr_type = "re"
        else:
            # If none of the possible prefixes matches, this is not a data
            # expression.
            return None
        if have_options:
            # At the moment, we only support the “i” option, which disables
            # case sensitivity.
            if self._accept("i"):
                case_sensitive = False
            self._expect(":")
        # After the prefix, we expect the key.
        key = self._expect_key()
        # The value is separated from the key by the @ character.
        self._expect("@")
        # Now we expect a pattern.
        pattern_position = self._position
        pattern = self._expect_glob_pattern_or_re()
        # When handling a glob expression, we have to translate the glob
        # pattern to a regular expression for matching.
        if expr_type == "glob":
            pattern = fnmatch.translate(pattern)
        # If we are handling a literal expression, we have to escape the string
        # in order to get a proper regular expression. Alternatively, we could
        # use a different expression function that compares strings instead of
        # using the re module, but this would make the code more complicated.
        elif expr_type == "literal":
            pattern = re.escape(pattern)
        try:
            return _data_expression(key, pattern, case_sensitive)
        except re.error as err:
            raise ParseError(
                f"Could not compile regular expression pattern {pattern!r}.",
                position=pattern_position,
            ) from err

    def _accept_id_expression(self) -> typing.Optional[Expression]:
        """
        Consume and return an ID expression.

        :return:
            consumed expression. If there is no ID expression at the current
            position, ``None`` is returned.
        """
        case_sensitive = True
        if self._accept("@id_glob/"):
            have_options = True
            expr_type = "glob"
        elif self._accept("@id_glob@"):
            have_options = False
            expr_type = "glob"
        elif self._accept("@id_literal/"):
            have_options = True
            expr_type = "literal"
        elif self._accept("@id_literal@"):
            have_options = False
            expr_type = "literal"
        elif self._accept("@id_re/"):
            have_options = True
            expr_type = "re"
        elif self._accept("@id_re@"):
            have_options = False
            expr_type = "re"
        else:
            # If none of the possible prefixes matches, this is not a data
            # expression.
            return None
        if have_options:
            # At the moment, we only support the “i” option, which disables
            # case sensitivity.
            if self._accept("i"):
                case_sensitive = False
            self._expect("@")
        # After the prefix, we expect the pattern.
        pattern_position = self._position
        pattern = self._expect_glob_pattern_or_re()
        # When handling a glob expression, We have to translate the glob
        # pattern to a regular expression for matching.
        if expr_type == "glob":
            pattern = fnmatch.translate(pattern)
        # If we are handling a literal expression, we have to escape the string
        # in order to get a proper regular expression. Alternatively, we could
        # use a different expression function that compares strings instead of
        # using the re module, but this would make the code more complicated.
        elif expr_type == "literal":
            pattern = re.escape(pattern)
        try:
            return _id_expression(pattern, case_sensitive)
        except re.error as err:
            raise ParseError(
                f"Could not compile regular expression pattern {pattern!r}.",
                position=pattern_position,
            ) from err

    def _expect_glob_pattern_or_re(self) -> str:
        """
        Consume and return a glob pattern or regular expression.

        Such a pattern may be quoted using ``"`` or ``'``. If quotes are used,
        the pattern is terminated by closing the quotes. If quotes are not
        used, it is terminated by any character that may not be a part of the
        unquoted pattern. These characters are ``(``, ``)``, and any kind of
        whitespace. Unquoted patterns must not be empty.

        :return:
            consumed pattern.
        """
        last_char_was_escape = False
        used_quotes = self._accept_any_of(("'", '"'))
        pattern = ""
        while not self.end_of_string:
            if last_char_was_escape:
                assert used_quotes is not None
                # The only escape sequences that we support are to escape the
                # used type of quotes and to escape the backslash itself.
                pattern += self._expect_any_of((used_quotes, "\\"))
                last_char_was_escape = False
            elif used_quotes:
                char = self._expect_any_char()
                # A backslash inside quotes escapes the next character.
                if char == "\\":
                    last_char_was_escape = True
                    continue
                # The same kind of quotes that were used at the beginning
                # indicate the end of the pattern.
                if char == used_quotes:
                    return pattern
                # Everything else is a part of the pattern.
                pattern += char
            else:
                char = self._peek(1)
                if char.isspace() or char in ("@", "(", ")"):
                    # Unquoted patterns must not be empty.
                    if not pattern:
                        raise ParseError(
                            "Expected pattern expression but found "
                            f"{self._excerpt()}.",
                            position=self._position,
                        )
                    return pattern
                # Everything else is a part of the pattern.
                pattern += char
                self._skip(1)
        # We only make it here when we reach the end of the string.
        # If the last character was the backslash, this is an error because the
        # escape sequence is incomplete.
        if last_char_was_escape:
            # We can raise an exception with the proper description by
            # expecting one of the characters that we would also have expected
            # if we had not reached the end-of-string prematurely.
            assert used_quotes is not None
            self._expect_any_of((used_quotes, "\\"))
        # If quotes were used, this is an error, because they were not closed
        # (if they were closed, we would have returned from the loop).
        if used_quotes:
            # We can generate the right exception by expecting the closing
            # quotes.
            self._expect(used_quotes)
        # If we reached the end of the string without reading any characters,
        # this is an error as well, because the pattern must not be empty
        # unless it is quoted (and it is not quoted because in that case we
        # would have returned earlier).
        if not pattern:
            raise ParseError(
                "Expected pattern expression but found end-of-string.",
                position=self._position,
            )
        return pattern

    def _expect_key(self) -> str:
        """
        Consume and return a key.

        A key may be quoted using ``"`` or ``'``. If quotes are used, the key
        is terminated by closing the quotes. If quotes are not used, it is
        terminated by any character that may not be a part of the unquoted key.
        These characters are ``@``, ``(``, ``)``, and any kind of whitespace.

        :return:
            consumed key.
        """
        last_char_was_escape = False
        used_quotes = self._accept_any_of(("'", '"'))
        key = ""
        while not self.end_of_string:
            if last_char_was_escape:
                assert used_quotes is not None
                # The only escape sequences that we support are to escape the
                # used type of quotes and to escape the backslash itself.
                key += self._expect_any_of((used_quotes, "\\"))
                last_char_was_escape = False
            elif used_quotes:
                char = self._peek(1)
                # The quotes must not be closed without any content (empty keys
                # are not allowed).
                if not key and char == used_quotes:
                    raise ParseError(
                        f"Expected any character except {used_quotes!r} but "
                        f"found {self._excerpt()}.",
                        position=self._position,
                    )
                self._skip(1)
                # A backslash inside quotes escapes the next character.
                if char == "\\":
                    last_char_was_escape = True
                    continue
                # The same kind of quotes that were used at the beginning
                # indicate the end of the key.
                if char == used_quotes:
                    return key
                # Everything else is a part of the key.
                key += char
            else:
                char = self._peek(1)
                if char.isspace() or char in ("@", "(", ")"):
                    if not key:
                        raise ParseError(
                            "Expected any non-whitespace character except "
                            f"['@', '(', ')'] but found {self._excerpt()}.",
                            position=self._position,
                        )
                    return key
                # Everything else is a part of the key.
                key += char
                self._skip(1)
        # We only make it here when we reach the end of the string.
        # If the last character was the backslash, this is an error because the
        # escape sequence is incomplete.
        if last_char_was_escape:
            # We can raise an exception with the proper description by
            # expecting one of the characters that we would also have expected
            # if we had not reached the end-of-string prematurely.
            assert used_quotes is not None
            self._expect_any_of((used_quotes, "\\"))
        # If quotes were used, this is an error, because they were not closed
        # (if they were closed, we would have returned from the loop).
        if used_quotes:
            # We can generate the right exception by expecting the closing
            # quotes.
            self._expect(used_quotes)
        # If we reached the end of the string without reading any characters,
        # this is an error as well, because the key must not be empty.
        if not key:
            self._expect_any_char()
        return key

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
        # The expressions that we support are described by the following
        # (simplified) grammar:
        #
        # SIMPLE_EXPRESSION = DATA_EXPRESSION
        #                   | ID_EXPRESSION
        #                   | UNQUALIFIED_EXPRESSION ;
        #
        # DATA_EXPRESSION = "@" ( "data_glob" | "data_literal" | "data_re" ) ,
        #                   [ OPTION_STRING ] , ":" , KEY , "@" , VALUE ;
        #
        # ID_EXPRESSION = "@" ( "id_glob" | "id_literal" | "id_re" ) ,
        #                 [ OPTION_STRING ] , "@" , VALUE ;
        #
        # UNQUALIFIED_EXPRESSION = DOUBLE_QUOTED_VALUE
        #                        | SINGLE_QUOTED_VALUE
        #                        | UNQUOTED_LIMITED_VALUE ;
        #
        # OPTION_STRING = "/" [ "i" ] ;
        #
        # KEY = DOUBLE_QUOTED_KEY
        #     | SINGLE_QUOTED_KEY
        #     | UNQUOTED_KEY ;
        #
        # VALUE = DOUBLE_QUOTED_VALUE
        #       | SINGLE_QUOTED_VALUE
        #       | UNQUOTED_UNLIMITED_VALUE ;
        #
        # The DOUBLE_QUOTED_KEY is any string that is wrapped in “"”, where the
        # characters between the “"” may be any characters except “"” and “\”.
        # However, these two special characters are allowed, if they are
        # directly preceded by a “\” (escaping). There must be at least one
        # character between the wraping “"”.
        #
        # The SINGLE_QUOTED_KEY is any string that is wrapped in “'”, where the
        # characters between the “'” may be any characters except “'” and “\”.
        # However, these two special characters are allowed, if they are
        # directly preceded by a “\” (escaping). There must be at least one
        # character between the wraping “'”.
        #
        # The UNQUOTED_KEY is any string that contains at least one character
        # but does not contain any whitespace characters or the characters
        # “@”, “(”, or “)”. The string must not start with the characters
        # “"” or “'”.
        #
        # The DOUBLE_QUOTED_VALUE is any string that is wrapped in “"”, where
        # the characters between the “"” may be any characters except “"” and
        # “\”. However, these two special characters are allowed, if they are
        # directly preceded by a “\” (escaping).
        #
        # The SINGLE_QUOTED_VALUE is any string that is wrapped in “'”, where
        # the characters between the “'” may be any characters except “'” and
        # “\”. However, these two special characters are allowed, if they are
        # directly preceded by a “\” (escaping).
        #
        # The UNQUOTED_LIMITED_VALUE is any string that contains at least one
        # character but does not contain any whitespace characters or the
        # characters “@”, “(”, or “)”. The string must not start with the
        # characters “"” or “'”. Furthermore, the string must not be the
        # literals “and”, “not”, or “or”.
        #
        # The UNQUOTED_UNLIMITED_VALUE is any string that does not contain any
        # whitespace characters or the characters “@”, “(”, or “)”. The string
        # must not start with the characters “"” or “'”.
        expression = self._accept_data_expression()
        if expression:
            return expression
        expression = self._accept_id_expression()
        if expression:
            return expression
        # We do not allow any expressions that start with “@” and do not
        # specify one of the supported types. This is to avoid strange behavior
        # in case of typos and in order to allow adding additional types in the
        # future without breaking backwards compatibility.
        if self._peek(1) == "@":
            raise ParseError(
                f"Found unsupported expression type at {self._excerpt()}.",
                position=self._position,
            )
        # If the expression type is not specified explicitly, we assume that
        # the expression is a glob pattern matching the system ID. In this
        # case, we do not allow an empty unquoted pattern, because it would be
        # indistinguishable from a pattern expression that is simply missing.
        pattern = self._expect_glob_pattern_or_re()
        # We have to translate the glob pattern to a regular expression for
        # matching.
        pattern = fnmatch.translate(pattern)
        expression = _id_expression(pattern, False)
        if not ignore_extra_input:
            self._expect_end_of_string()
        return expression
