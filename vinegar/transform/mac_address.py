"""
Transformations for MAC addresses.
"""

import re

# Regular expression matching a MAC address.
#
# The regular expression is designed so that it matches MAC addresses using ":"
# or "-" as the delimiter and matches addresses where the leading zero of a
# hexadecimal byte that is less than 0x10 is omitted.
#
# The expression is designed so that groups 1, 3, 5, 7, 9, and 11 match the six
# bytes of the MAC address.
_MAC_REGEXP = re.compile(
    """(?x)
    # Enable verbose mode (whitespace is ignored so that we can use this
    # multi-line formatting. The comment comes after the flag because the flag
    # must be the first thing in the expression.

    # Match the first address byte.
    ([0-9A-Fa-f]{1,2})
    # Matches the first delimiter (":" or "-").
    (?P<delimiter>[:\\-])
    # Match the second address byte.
    ([0-9A-Fa-f]{1,2})
    # Match the next delimiter. It must be the same as the first one.
    ((?P=delimiter))
    # Match the third address byte.
    ([0-9A-Fa-f]{1,2})
    # Match the next delimiter. It must be the same as the first one.
    ((?P=delimiter))
    # Match the fourth address byte.
    ([0-9A-Fa-f]{1,2})
    # Match the next delimiter. It must be the same as the first one.
    ((?P=delimiter))
    # Match the fivth address byte.
    ([0-9A-Fa-f]{1,2})
    # Match the next delimiter. It must be the same as the first one.
    ((?P=delimiter))
    # Match the sixth address byte.
    ([0-9A-Fa-f]{1,2})
    """
)


def normalize(
    value: str,
    target_case: str = "upper",
    delimiter: str = ":",
    raise_error_if_malformed: bool = False,
) -> str:
    """
    Normalize a MAC address.

    This function takes a MAC address (as a ``str``) and transforms it into a
    normalized form. This means that each byte of the MAC address is
    represented by exactly two characters (adding a leading "0" if needed). The
    MAC address is also transformed to consistenly use upper or lower case
    characters and to use the specified delimiter.

    While an input MAC address can have mixed upper / lower case characters, it
    must consistently use one delimiter (":" or "-").

    When a malformed MAC address is encountered, the behavior depends on the
    ``raise_error_if_malformed`` option. If that option is set to ``True``, a
    ``ValueError`` is raised. If it is ``False`` (the default), the input value
    is returned unchanged.

    :param value:
        input MAC address to be transformed.
    :param target_case:
        ``upper`` if the transformed MAC address shall use upper-case
        characters, ``lower`` if the transformed MAC address shall use
        lower-case characters. The default is ``upper``.
    :param delimiter:
        ``:`` or ``colon`` if the bytes of the MAC address shall be separated
        by a colon and ``-``, ``dash`` or ``minus`` if the bytes of the MAC
        address shall be separated by a minus sign. The default is ``:``.
    :param raise_error_if_malformed:
        ``True`` if a malformed MAC address should result in a ``ValueError``
        being raised, ``False`` if it should result in the input value being
        returned as is. The default is ``False``.
    :return:
        normalized form of the input MAC address.
    """
    if delimiter in (":", "colon"):
        delimiter = ":"
    elif delimiter in ("-", "dash", "minus"):
        delimiter = "-"
    else:
        raise ValueError(
            'Invalid delimiter "{0}". Valid values are ":", "-", "colon", '
            '"dash" or "minus".'.format(delimiter)
        )
    if target_case not in ("lower", "upper"):
        raise ValueError(
            'Invalid target case "{0}": Valid values are "lower" and '
            '"upper".'.format(target_case)
        )
    match = _MAC_REGEXP.fullmatch(value)
    if match is None:
        if raise_error_if_malformed:
            raise ValueError("Not a valid MAC address: {0}".format(value))
        return value
    # The parts of the string that represent the address bytes are in groups
    # 1, 3, 5, 7, 9, and 11 of the expression.
    addr_bytes = match.group(1, 3, 5, 7, 9, 11)
    # We convert to the hex numbers to integer and back to a hexadecimal
    # string, using a width of two and upper / lower case depending on the
    # setting.
    if target_case == "upper":
        format_specifier = "{:02X}"
    else:
        format_specifier = "{:02x}"
    addr_bytes = [
        format_specifier.format(int(addr_byte, 16)) for addr_byte in addr_bytes
    ]
    # Finally, we join the hex numbers using the delimiter.
    return delimiter.join(addr_bytes)
