"""
Expression matcher for targeting systems. This matcher extends the basic
`fnmatch` pattern syntax with expressions combining several patterns.

A string can be matched against a pattern using the `match` function. If the
same pattern is used repeatedly, a `Matcher` can be retrieved using the
`matcher` function. However, even the `match` function implements a simple cache
in order to avoid recompiling frequently used patterns.

Pattern expressions understood by this module are combinations of the patterns
understood by `fnmatch`. These combinations can be defined through the use of
the logical operators `and`, `not`, and `or`, optionally grouped using
parentheses.

Examples:

* "abc.example.com" exactly matches "abc.example.com".
* "\\*.example.com" matches "abc.example.com" and "123.456.example.com", but not
  "abc.example.net".
* "\\*.example.com or \\*.example.net" matches "abc.example.com" and
  "123.example.net", but not "def.example.org".
* "\\*.example.com and not abc.\\*" matches "def.example.com" and
  "abc123.example.com", but not "abc.example.com".
* "(\\*.example.com or \\*.example.net) and not abc.\\*" matches
  "def.example.com" and "def.example.net", but not "abc.example.com".
"""

import abc
import fnmatch
import functools
import re


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
            pattern, case_sensitive)
        self._pattern = pattern

    def matches(self, name: str) -> bool:
        """
        Tell whether the specified ``name`` matches the pattern.

        :param name: name to be matched against the pattern.
        """
        return self._expression.matches(name)

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
    return expression.matches(name)


def matcher(pattern: str, case_sensitive: bool = False) -> Matcher:
    """
    Return a `Matcher` for the specified pattern.

    Raises an exception if ``pattern`` is not a valid pattern expression
    supported by this module.

    This function internally keeps a cache of compiled patterns in order to
    reduce the overhead when the same pattern is used repeatedly. However,
    calling code is still encouraged to keep a reference to the returned matcher
    when it knows that the same pattern is going to be used repeatedly.

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


class _Expression(abc.ABC):
    """
    Base class for all expression supported by our expression language.
    """

    @abc.abstractmethod
    def matches(self, name: str) -> bool:
        raise NotImplementedError


class _AndExpression(_Expression):
    """
    And expression. This is an expression that evaluates to ``True`` if both its
    left and right expression evaluate to ``True``.
    """

    def __init__(self, left_expression, right_expression):
        self._left_expression = left_expression
        self._right_expression = right_expression

    def matches(self, name):
        # If the left expression evaluates to False, we can skip the evaluation
        # of the right expression.
        if not self._left_expression.matches(name):
            return False
        else:
            return self._right_expression.matches(name)


class _OrExpression(_Expression):
    """
    Or expression. This is an expression that evaluates to ``True`` if either
    its left or its right expression evaluates to ``True``.
    """

    def __init__(self, left_expression, right_expression):
        self._left_expression = left_expression
        self._right_expression = right_expression

    def matches(self, name):
        # If the left expression evaluates to True, we can skip the evaluation
        # of the right expression.
        if self._left_expression.matches(name):
            return True
        else:
            return self._right_expression.matches(name)


class _PatternExpression(_Expression):
    """
    Pattern expression. This is an expression that checks whether the specified
    name matches a pattern using `fnmatch.fnmatch` or `fnmatch.fnmatchcase`.
    """

    def __init__(self, pattern, case_sensitive):
        if case_sensitive:
            flags = 0
        else:
            flags = re.IGNORECASE
        self._regexp = re.compile(fnmatch.translate(pattern), flags)

    def matches(self, name):
        return self._regexp.fullmatch(name) is not None


class _NotExpression(_Expression):
    """
    Not expression. This is an expression that negates its sub-expression.
    """

    def __init__(self, expression):
        self._expression = expression

    def matches(self, name):
        return not(self._expression.matches(name))


def _expect_expression(tokens, case_sensitive):
    """
    Consume and return an expression from ``tokens``. Unlike
    `_expect_unary_expression`, this function always consumes all tokens.

    This function raises an exception if the ``tokens`` do not represent a valid
    expression.
    """
    # The expressions that we support are described by the following
    # (simplified) grammar:
    #
    # EXPRESSION = PARENTHESES_EXPRESSION
    #            | NOT_EXPRESSION
    #            | AND_EXPRESSION
    #            | OR_EXPRESSION
    #            | PATTERN ;
    #
    # PARANTHESES_EXPRESSION = "(" , EXPRESSION , ")" ;
    #
    # NOT_EXPRESSION = "not" , UNARY_EXPRESSION ;
    # UNARY_EXPRESSION = PARANTHESES_EXPRESSION
    #                  | NOT_EXPRESSION
    #                  | PATTERN ;
    #
    # AND_EXPRESSION = { UNARY_EXPRESSION , "and" , UNARY_EXPRESSION }
    #                | { UNARY_EXPRESSION , "and" , AND_EXPRESSION } ;
    #
    # OR_EXPRESSION = EXPRESSION , "or" , EXPRESSION ;
    #
    # This grammar describes tokens, not characters. Tokens have to be separated
    # by whitespace, except for parentheses. This grammar does not describe the
    # internal structure of patterns either, but it is simply assumed that
    # everything that does not match anything else is a pattern.

    # Every expression starts with a unary expression (that is a parentheses
    # expression, a "not" expression, or a pattern).
    left_expression = _expect_unary_expression(tokens, case_sensitive)
    right_expression = None

    while tokens:
        token = tokens.pop(0)
        if token == 'and':
            local_expression = _expect_unary_expression(tokens, case_sensitive)
            # We might have had a preceding or operator where we were not sure
            # whether we could use its second argument because it could have
            # been part of an "and" expression. Now we know that it actually is
            # part of an and expression, so we use it for that purpose.
            if right_expression is not None:
                right_expression = _AndExpression(
                    right_expression, local_expression)
            else:
                left_expression = _AndExpression(
                    left_expression, local_expression)
        elif token == 'or':
            # We might have had a preceding or operator where we were not sure
            # whether we could use its second argument because it could have
            # been part of an "and" expression. Now we know that it is not and
            # can use it.
            if right_expression is not None:
                left_expression = _OrExpression(
                    left_expression, right_expression)
                right_expression = None
            # The expression that we just consumed might be part of an "and"
            # expression, so we cannot use it as a part of the "or" expression
            # right away.
            right_expression = _expect_unary_expression(tokens, case_sensitive)
        else:
            raise ValueError(
                'Found token "{0}" where "and" or "or" were expected.'.format(
                    token))

    # A right expression is only left if there was an or expression that has not
    # been completely handled yet, so we build that or expression now.
    if right_expression is not None:
        left_expression = _OrExpression(left_expression, right_expression)
        right_expression = None
    return left_expression


def _expect_unary_expression(tokens, case_sensitive):
    """
    Consume and return a unary expression from ``tokens``.

    This function raises an exception if no unary expression can be extracted
    from the beginning of the ``tokens``.
    """
    if not tokens:
        raise ValueError('Found empty string where an expression was expected.')
    token = tokens.pop(0)
    if token == '(':
        closing_index = _find_closing_parenthesis(tokens)
        tokens_in_parentheses = tokens[:closing_index]
        # We cannot assign to tokens because in this case the change would not
        # be visible to the calling code. Therefore, we do not use a slice
        # expression and rather call pop instead.
        for _ in range(0, closing_index + 1):
            tokens.pop(0)
        return _expect_expression(tokens_in_parentheses, case_sensitive)
    elif token == 'not':
        expression = _expect_unary_expression(tokens, case_sensitive)
        return _NotExpression(expression)
    elif token in ('and', 'or'):
        raise ValueError(
            'Found "{0}" where "(", "not" or pattern was expected.'.format(
                token))
    else:
        return _PatternExpression(token, case_sensitive)


def _expression_from_string(expression, case_sensitive):
    """
    Return the `_Expression` represented by the specified string.

    This function raises an exception if the string does represent a valid
    expression.
    """
    # First, we split the pattern into tokens so that we can parse it more
    # easily.
    tokens = expression.split()
    # Parentheses differ from other tokens because they do not have to be
    # separated by whitespace, so we have to split the individual tokens until
    # there is no parenthesis in them any longer. Of course, this does not apply
    # to tokens that only consist of a parenthesis.
    split_tokens = []
    for token in tokens:
        partial_token = ''
        for character in token:
            if character == '(' or character == ')':
                if partial_token:
                    split_tokens.append(partial_token)
                split_tokens.append(character)
                partial_token = ''
            else:
                partial_token += character
        if partial_token:
            split_tokens.append(partial_token)
    try:
        return _expect_expression(split_tokens, case_sensitive)
    except ValueError as e:
        message = str(e)
        if not message:
            message = type(e).__name__
        raise ValueError(
            'Cannot parse expression "{0}": {1}'
            .format(expression, message)) from None


@functools.lru_cache(maxsize=256, typed=True)
def _expression_from_string_cached(expression, case_sensitive):
    """
    Call `_expression_from_string` but cache the result.

    This is used by `match` for performance reasons.
    """
    return _expression_from_string(expression, case_sensitive)


def _find_closing_parenthesis(tokens):
    """
    Find the index of the next closing parenthesis that is not canceled out by a
    preceding opening parenthesis. This function is mainly intended for use by
    `_expect_unary_expression`.

    This function raises an exception if no such parenthesis can be found.
    """
    open_count = 0
    token_index = 0
    for token in tokens:
        if token == '(':
            open_count += 1
        elif token == ')':
            open_count -= 1
        if open_count < 0:
            return token_index
        token_index += 1
    # If we make it here, there is no closing parenthesis, so the parentheses
    # are unbalanced.
    raise ValueError('Unbalanced parentheses.')
