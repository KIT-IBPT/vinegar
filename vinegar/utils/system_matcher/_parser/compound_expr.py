"""
Parser for a compound expression.
"""

import typing

from .base import Expression, ParseError, ParserBase
from .simple_expr import SimpleExpressionParser


def _and_expression(
    left_expression: Expression, right_expression: Expression
) -> Expression:
    """
    Return an ``and`` expression. This is an expression that evaluates to
    ``True`` if both its left and right expression evaluate to ``True``.
    """

    def evaluate(name: str) -> bool:
        # If the left expression evaluates to False, we can skip the evaluation
        # of the right expression.
        if not left_expression(name):
            return False
        return right_expression(name)

    return evaluate


def _not_expression(expression: Expression) -> Expression:
    """
    Return a ``not`` expression. This is an expression that negates its
    sub-expression.
    """

    def evaluate(name: str) -> bool:
        return not expression(name)

    return evaluate


def _or_expression(
    left_expression: Expression, right_expression: Expression
) -> Expression:
    """
    Return an ``or`` expression. This is an expression that evaluates to
    ``True`` if either its left or its right expression evaluate to ``True``.
    """

    def evaluate(name):
        # If the left expression evaluates to True, we can skip the evaluation
        # of the right expression.
        if left_expression(name):
            return True
        return right_expression(name)

    return evaluate


class CompoundExpressionParser(ParserBase):
    """
    Parser for a compound matching expression.
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

    def _accept_keyword(
        self, accepted_keywords: typing.Sequence[str] = ("and", "not", "or")
    ) -> typing.Optional[str]:
        """
        Consume and return a keyword.

        This is similar to `_accept_any_of`, but it will only accept one of the
        specified strings when it is at the end of the parsed string or
        followed by whitespace or an opening parenthesis. This ensures that
        strings that start with a keyword but do not represent a keyword are
        not accidentally treated as this keyword.

        :param accepted_keywords:
            sequence of keywords that shall be accepted.
        :return:
            the accepted keyword or ``None`` if none of the accepted keywords
            is present at the current location.
        """
        keyword = self._peek_keyword(accepted_keywords)
        if keyword:
            self._skip(len(keyword))
        return keyword

    def _accept_whitespace(self) -> str:
        """
        Consume and return whitespace.

        Any whitespace from the current position up to the first non-whitespace
        character or the end of the string (whichever is encountered first), is
        consumed and returned.

        :return:
            consumed whitespace or the empty string if the character at the
            current position does not represent whitespace.
        """
        whitespace = ""
        while self._peek(1).isspace():
            char = self._accept_any_char()
            # isspace() is False for the empty string, so there must be at
            # least one remaining character, which means that
            # _accept_any_char() cannot return None.
            assert char is not None
            whitespace += char
        return whitespace

    def _expect_compound_and_expression(self) -> Expression:
        """
        Consume and return a compound ``and`` expression.

        Such expressions consist of unary expressions that are combined using
        the keyword ``and``. Their representation might include leading or
        trailing whitespace, which is going to be consumed by this method.

        :return:
            consumed expression.
        """
        # The “and” operator takes precedence over the “or” operator, so an
        # “and” expression must not contain an “or” expression (unless
        # parantheses are used, which make the “or” expression a unary
        # expression).
        return self._expect_generic_compound_expression(
            "and", self._expect_unary_expression, _and_expression
        )

    def _expect_compound_or_expression(self) -> Expression:
        """
        Consume and return a compound ``or`` expression.

        Such expressions consist compound ``and`` expressions that are combined
        using the keyword ``or``. Their representation might include leading or
        trailing whitespace, which is going to be consumed by this method.

        :return:
            consumed expression.
        """
        # The “and” operator takes precedence over the “or” operator, so we to
        # proces all consecutive “and” expressions before we may create an “or”
        # expression.
        return self._expect_generic_compound_expression(
            "or", self._expect_compound_and_expression, _or_expression
        )

    def _expect_generic_compound_expression(
        self,
        keyword: str,
        expect_subexpression: typing.Callable[[], Expression],
        reduce_expressions: typing.Callable[
            [Expression, Expression], Expression
        ],
    ) -> Expression:
        """
        Base function for parsing compound expressions.

        Such expressions consist of subexpressions which are connected by a
        specific keyword. Their representation might include leading or
        trailing whitespace, which is going to be consumed by this method.

        :param keyword:
            keyword that is used for separating subexpressions (if there is
            more than one).
        :param expect_subexpression:
            function that is called to parse each subexpression. This method
            must consume the input for the subexpression and return the
            respective expression.
        :param reduce_expressions:
            function that is called to combine subexpressions. Each time the
            keyword is encountered, this function is called with the expression
            left to the keyword and the expression immediately right to the
            keyword. For the second and subsequent keywords, the expression
            left to the keyword is the one that was the result of the previous
            call to this function.

        :return:
            consumed expression.
        """
        # A compound expression may have leading whitespace, which is simply
        # discarded.
        self._accept_whitespace()
        # We get the first subexpression, which must always be present.
        left_expression = expect_subexpression()
        # Before the next keyword and after the last expression, there may be
        # whitespace. In fact, if there is a keyword, it must be preceded by
        # whitespace or a closing parenthesis, but if it wasn’t this part of
        # the string would already have been consumed when calling
        # expect_subexpression().
        self._accept_whitespace()
        while not self.end_of_string:
            # Between the subexpressions, only the specified keyword is
            # allowed.
            found_keyword = self._accept_keyword((keyword,))
            # If there is no keyword (or at least not the expected one), we
            # have reached the end of this compound expression.
            if not found_keyword:
                return left_expression
            # After the keyword, we expect another subexpression. There may
            # (and in some situations must) be whitespace between the keyword
            # and the next subexpression.
            self._accept_whitespace()
            right_expression = expect_subexpression()
            left_expression = reduce_expressions(
                left_expression, right_expression
            )
            # Before the next keyword and after the last expression, there may
            # be whitespace. In fact, if there is a keyword, it must be
            # preceded by whitespace or a closing parenthesis, but if it wasn’t
            # this part of the string would already have been consumed when
            # calling expect_subexpression().
            self._accept_whitespace()
        return left_expression

    def _expect_simple_expression(self) -> Expression:
        """
        Consume and return a simple expression.

        A simple expression is a unary expression that is not a parentheses or
        ``not`` expression.

        :return:
            consumed expression.
        """
        parser = SimpleExpressionParser(
            self.remaining_input, case_sensitive=self._case_sensitive
        )
        expression = parser.parse(ignore_extra_input=True)
        self._skip(len(parser.consumed_input))
        return expression

    def _expect_unary_expression(self) -> Expression:
        """
        Consume and return a unary expression.

        Unary expressions are parentheses expressions, ``not`` expressions, and
        simple expressions.

        :return:
            consumed expression.
        """
        if self._accept("("):
            expression = self._expect_compound_or_expression()
            self._expect(")")
            return expression
        keyword = self._peek_keyword()
        if keyword == "not":
            # The not keyword must be followed by a unary expression, but in
            # between there often is (and tyically even must be) some
            # whitespace, so we consume this.
            self._skip(len(keyword))
            self._accept_whitespace()
            expression = self._expect_unary_expression()
            return _not_expression(expression)
        if keyword:
            # No other keyword is allowed here.
            raise ParseError(
                f"Expected '(', keyword 'not', or simple expression, but "
                f"found {self._excerpt()}.",
                position=self._position,
            )
        return self._expect_simple_expression()

    def _expect_whitespace(self) -> str:
        """
        Consume and return whitespace, failing if there is none.

        Any whitespace from the current position up to the first non-whitespace
        character or the end of the string (whichever is encountered first), is
        consumed and returned. If there is no whitespace at the current
        position, an exception is raised.

        :return:
            consumed whitespace.
        """
        whitespace = self._accept_whitespace()
        if not whitespace:
            raise ParseError(
                f"Expected whitespace, but found {self._excerpt()}.",
                position=self._position,
            )
        return whitespace

    def _peek_keyword(
        self, accepted_keywords: typing.Sequence[str] = ("and", "not", "or")
    ) -> typing.Optional[str]:
        """
        Check whether a keyword is present at the current position.

        This method is very similar to `_accept_keyword` with the exception
        that the keyword is returned but not consumed, leaving the parser
        position untouched.

        :param accepted_keywords:
            sequence of keywords that shall be accepted.
        :return:
            the accepted keyword or ``None`` if none of the accepted keywords
            is present at the current location.
        """
        # In order to decide whether there is a keyword, we have to look one
        # character past the keyword’s length, so we retrieve one more
        # character than the longest keyword has.
        max_keyword_len = 0
        for keyword in accepted_keywords:
            max_keyword_len = max(max_keyword_len, len(keyword))
        candidate_keyword = self._peek(max_keyword_len + 1)
        for keyword in accepted_keywords:
            if candidate_keyword.startswith(keyword):
                keyword_len = len(keyword)
                if len(candidate_keyword) == keyword_len:
                    return keyword
                following_char = candidate_keyword[keyword_len]
                if following_char == "(" or following_char.isspace():
                    return keyword
        return None

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
        # EXPRESSION = OR_EXPRESSION ;
        #
        # PARANTHESES_EXPRESSION = "(" , EXPRESSION , ")" ;
        #
        # NOT_EXPRESSION = "not" , UNARY_EXPRESSION ;
        #
        # UNARY_EXPRESSION = PARANTHESES_EXPRESSION
        #                  | NOT_EXPRESSION
        #                  | PATTERN ;
        #
        # AND_EXPRESSION = { UNARY_EXPRESSION , "and" , AND_EXPRESSION }
        #                | UNARY_EXPRESSION ;
        #
        # OR_EXPRESSION = { AND_EXPRESSION , "or" , OR_EXPRESSION }
        #               | AND_EXPRESSION ;
        #
        # This grammar describes tokens, not characters. Tokens have to be
        # separated by whitespace, except for parentheses. This grammar does
        # not describe the internal structure of patterns either, but it is
        # simply assumed that everything that is not a keyword and does not
        # contain parantheses or whitespace is a pattern.
        expression = self._expect_compound_or_expression()
        if not ignore_extra_input and not self.end_of_string:
            # When we reached the end of the compound expression, this is
            # because there wasn’t another “and” or “or” keyword.
            raise ParseError(
                f"Expected any of the keywords ['and', 'or'] or "
                f"end-of-string, but found {self._excerpt()}.",
                position=self._position,
            )
        return expression
