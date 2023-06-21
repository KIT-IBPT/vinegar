"""
Expression matcher for targeting systems.

This matcher allows matching based on the system ID or system data from the
data sources (depending on the context in which the expression is evaluated).

A system ID can be matched against an expression using the `match` function. If
the same expression is used repeatedly, a `Matcher` can be retrieved using the
`matcher` function. However, even the `match` function implements a simple
cache in order to avoid recompiling frequently used expressions.

Expressions understood by this module are combinations of four different
subexpressions:

* Expressions matching system data using glob patterns (as understood by
  `fnmatch`). These expressions start with the string ``@data_glob``. Please
  refer to :ref:`utils_system_matcher_data_glob` for details.
* Expressions matching system data by comparing to a literal string. These
  expressions start with the string ``@data_literal``. Please refer to
  :ref:`utils_system_matcher_data_literal` for details.
* Expressions matching system data using regular expressions. These expressions
  start with the string ``@data_re``. Please refer to
  :ref:`utils_system_matcher_data_re` for details.
* Expressions matching system IDs using glob patterns (as understood by
  `fnmatch`). These expressions start with the string ``@id_glob``. Please
  refer to :ref:`utils_system_matcher_id_glob` for details. For these
  expressions there is a short-hand syntax that omits the ``@id_glob`` prefix.
* Expressions matching system IDs by comparing to a literal string. These
  expressions start with the string ``@id_literal``. Please refer to
  :ref:`utils_system_matcher_id_literal` for details.
* Expressions matching system IDs using regular expressions. These expressions
  start with the string ``@id_re``. Please refer to
  :ref:`utils_system_matcher_id_re` for details.

These subexpressions can be combined using  the logical operators `and`, `not`,
and `or` and can optionally be grouped using parentheses.

As a shorthand notation, expressions matching system IDs using glob patterns
and ignoring case can be written without the prefix for the expression type.
For example, ``@id_glob/i@my-pattern-*`` can simply be written as
``my-pattern-*``.

Examples:

* ``abc.example.com`` exactly matches ``abc.example.com``.
* ``*.example.com`` matches ``abc.example.com`` and ``123.456.example.com``,
  but not ``abc.example.net``.
* ``*.example.com or *.example.net`` matches ``abc.example.com`` and
  ``123.example.net``, but not ``def.example.org``.
* ``*.example.com and not abc.*`` matches ``def.example.com`` and
  ``abc123.example.com``, but not ``abc.example.com``.
* ``(*.example.com or *.example.net) and not abc.*`` matches
  ``def.example.com`` and ``def.example.net``, but not ``abc.example.com``.
* ``@id_literal@abc.example.com or @id-glob/i@*.example.net or
  @data_re:key@prefix-.*``matches ``abc.example.com``, ``def.example.net``,
  ``ghi.Example.net``, and any system where the system data has a value
  starting with ``prefix-``, but (unless the mentioned system-data value is
  present) the system IDs ``Abc.example.com`` and ``abc.example.org`` are not
  matched.

.. _utils_system_matcher_data_glob:

System data glob matching
-------------------------

Patterns starting with ``@data_glob`` can be used to match system data. The
format is ``@data_glob[/i]:<key>@<value pattern>``.

The ``/i`` is optional and causes the matching to ignore case.

If the key or the value pattern contain reserved characters (``@``, ``(``,
``)``, or whitespace), the key or the value must be wrapped in quotes (``"`` or
``'``). If the quotes used for wrapping are used inside the pattern, they must
be escaped using the backslash (``\\``). The backslash itself must be escaped
by doubling it.


The pattern is matched against the value stored in the system data under the
specified key using the `fnmatch` module.

If the dict that is passed to the match function is a
`~vinegar.utils.smart_dict.SmartLookupDict`, nested keys can be used.

Examples:

* ``@data_glob:my-key@my-*``
* ``@data_glob:"my key"@"my val*"``
* ``@data_glob/i:'some key'@'value with special characters like the quotation
  mark \\', the backslash \\\\, the @ character, and parentheses ()'``

.. _utils_system_matcher_data_literal:

System data literal matching
----------------------------

Patterns starting with ``@data_literal`` can be used to match system data. The
format is ``@data_literal[/i]:<key>@<value>``.

The ``/i`` is optional and causes the matching to ignore case.

If the key or the value contain reserved characters (``@``, ``(``, ``)``, or
whitespace), the key or the value must be wrapped in quotes (``"`` or ``'``).
If the quotes used for wrapping are used inside the value, they must be escaped
using the backslash (``\\``). The backslash itself must be escaped by doubling
it.

The specified value is compared with the value stored in the system data under
the specified key. The expression matches if the two strings are the same
(ignoring case if the ``/i`` flag is specified).

If the dict that is passed to the match function is a
`~vinegar.utils.smart_dict.SmartLookupDict`, nested keys can be used.

Examples:

* ``@data_literal:my-key@my-value``
* ``@data_literal:"my key"@"my value"``
* ``@data_literal/i:'some key'@'value with special characters like the
  quotation mark \\', the backslash \\\\, the @ character, and parentheses
  ()'``

.. _utils_system_matcher_data_re:

System data regular-expression matching
---------------------------------------

Patterns starting with ``@data_re`` can be used to match system data. The
format is ``@data_re[/i]:<key>@<regular expression>``.

The ``/i`` is optional and causes the matching to ignore case.

If the key or the regular expression contain reserved characters (``@``, ``(``,
``)``, or whitespace), the key or the regular expression must be wrapped in
quotes (``"`` or ``'``). If the quotes used for wrapping are used inside the
regular expression, they must be escaped using the backslash (``\\``). The
backslash itself must be escaped by doubling it.

Please note that characters that have a special meaning in regular expressions
have to be escaped twice (first for the expression parser and a second time for
the `re` module).

The regular expression is matched against the value stored in the system data
under the specified key using the `re.fullmatch` function.

If the dict that is passed to the match function is a
`~vinegar.utils.smart_dict.SmartLookupDict`, nested keys can be used.

Examples:

* ``@data_re:my-key@my-.*``
* ``@data_re:"my key"@"my val.*"``
* ``@data_re/i:'some key'@'value with special characters like the quotation
  mark \\', the backslash \\\\\\\\, the @ character, and parentheses
  \\\\(\\\\)'``

.. _utils_system_matcher_id_glob:

System ID glob matching
-----------------------

Patterns starting with ``@id_glob`` can be used to match a system ID. The
format is ``@id_glob[/i]@<ID pattern>``.

The ``/i`` is optional and causes the matching to ignore case.

If the ID pattern contains reserved characters (``@``, ``(``, ``)``, or
whitespace), the key or the value must be wrapped in quotes (``"`` or ``'``).
If the quotes used for wrapping are used inside the pattern, they must be
escaped using the backslash (``\\``). The backslash itself must be escaped by
doubling it.

The pattern is matched against the system ID using the `fnmatch` module.

Examples:

* ``@id_glob@my-id-*``
* ``@id_glob@"my id*"``
* ``@id_glob/i@'value with special characters like the quotation
  mark \\', the backslash \\\\, the @ character, and parentheses ()'``

.. _utils_system_matcher_id_literal:

System ID literal matching
--------------------------

Patterns starting with ``@id_literal`` can be used to match a system ID. The
format is ``@id_literal[/i]@<ID>``.

The ``/i`` is optional and causes the matching to ignore case.

If the ID contains reserved characters (``@``, ``(``, ``)``, or whitespace),
the ID must be wrapped in quotes (``"`` or ``'``). If the quotes used for
wrapping are used inside the ID, they must be escaped using the backslash
(``\\``). The backslash itself must be escaped by doubling it.

The specified ID is compared with the ID passed to the match function. The
expression matches if the two strings are the same (ignoring case if the ``/i``
flag is specified).

Examples:

* ``@id_literal@my-id``
* ``@id_literal@"my id"``
* ``@id_literal/i:@'ID with special characters like the quotation mark \\', the
  backslash \\\\, the @ character, and parentheses ()'``

.. _utils_system_matcher_id_re:

System ID regular-expression matching
-------------------------------------

Patterns starting with ``@id_re`` can be used to match a system ID. The format
is ``@id_re[/i]@<regular expression>``.

The ``/i`` is optional and causes the matching to ignore case.

If the regular expression contains reserved characters (``@``, ``(``, ``)``, or
whitespace), the key or the regular expression must be wrapped in quotes (``"``
or ``'``). If the quotes used for wrapping are used inside the regular
expression, they must be escaped using the backslash (``\\``). The backslash
itself must be escaped by doubling it.

Please note that characters that have a special meaning in regular expressions
have to be escaped twice (first for the expression parser and a second time for
the `re` module).

The regular expression is matched against the system ID passed to the match
function using the `re.fullmatch` function.

Examples:

* ``@id_re@my-.*``
* ``@id_re@"my id.*"``
* ``@id_re/i@'ID with special characters like the quotation mark \\', the
  backslash \\\\\\\\, the @ character, and parentheses \\\\(\\\\)'``
"""
import functools

from typing import Optional

from ._parser.base import Expression, ParseError
from ._parser.compound_expr import CompoundExpressionParser


class Matcher:
    """
    Matcher object representing a pattern. This is useful when the same pattern
    is used over-and-over again and has a well-defined life-cycle.

    Matcher objects are thread safe.

    Instances of this class should be retrieved through the `matcher` function.
    """

    def __init__(self, expression_str: str, /):
        """
        Instances of this class should be retrieved through the `matcher`
        function.

        :param expression_str:
            the expression that shall be compiled.
        """
        self._expression = _expression_from_string_cached(expression_str)
        self._expression_str = expression_str

    def matches(
        self,
        *,
        system_id: Optional[str] = None,
        system_data: Optional[dict] = None,
    ) -> bool:
        """
        Tell whether this matcher matches the specified arguments.

        :param system_id:
            system ID to be matched against the expression. If ``None`` this is
            treated like an empty string.
        :param system_data:
            system data to be matched against the expression. If ``None`` this
            is treated like an empty dict. If nested keys are to be supported
            in expressions, the passed dict must be a
            `~vinegar.utils.smart_dict.SmartLookupDict`.

        :return:
            ``True`` if the expression represented by this matcher matches the
            specified system ID and system data, ``False`` otherwise.
        """
        if system_id is None:
            system_id = ""
        if system_data is None:
            system_data = {}
        return self._expression(system_id, system_data)

    def __str__(self):
        return self._expression_str


def match(
    expression_str: str,
    /,
    *,
    system_id: Optional[str] = None,
    system_data: Optional[dict] = None,
) -> bool:
    """
    Tell whether the specified ``expression_str`` matches the arguments.

    Raises an exception if ``expression_str`` is not a valid matcher expression
    supported by this module.

    This function internally keeps a cache of compiled expressions in order to
    reduce the overhead when the same expression is used repeatedly. Code that
    knows that such repeatitive behavior will occur should still prefer the
    `matcher` function if possible.

    :param expression_str:
        expression to be compiled. Please refer to the
        `module documentation <vinegar.utils.system_matcher>` for details about
        the pattern format.
    :param system_id:
        system ID to be matched against the expression. If ``None`` this is
        treated like an empty string.
    :param system_data:
        system data to be matched against the expression. If ``None`` this
        is treated like an empty dict. If nested keys are to be supported in
        expressions, the passed dict must be a
        `~vinegar.utils.smart_dict.SmartLookupDict`.

    :return:
        ``True`` if the ``expression_str`` matches the ``system_id`` and
        ``system_data``, ``False`` otherwise.

    :raise ValueError:
        if the expression is invalid and cannot be compiled.
    """
    expression = _expression_from_string_cached(expression_str)
    if system_id is None:
        system_id = ""
    if system_data is None:
        system_data = {}
    return expression(system_id, system_data)


def matcher(expression_str: str, /) -> Matcher:
    """
    Return a `Matcher` for the specified expression.

    Raises an exception if ``expression_str`` is not a valid matcher expression
    supported by this module.

    This function internally keeps a cache of compiled expressions in order to
    reduce the overhead when the same expression is used repeatedly. However,
    calling code is still encouraged to keep a reference to the returned
    matcher when it knows that the same expression is going to be used
    repeatedly.

    :param expression_str:
        expression to be compiled. Please refer to the
        `module documentation <vinegar.utils.system_matcher>` for details about
        the expression format.

    :return:
        matcher for the specified expression.

    :raise ValueError:
        if the expression is invalid and cannot be compiled.
    """
    return Matcher(expression_str)


@functools.lru_cache(maxsize=256, typed=True)
def _expression_from_string_cached(expression_str: str) -> Expression:
    """
    Call `_expression_from_string` but cache the result.

    This is used by `match` for performance reasons.
    """
    try:
        return CompoundExpressionParser(expression_str).parse()
    except ParseError as err:
        raise ValueError(
            f"Error at index {err.position} while parsing matcher expression "
            f"{expression_str!r}: {str(err)}"
        ) from err
