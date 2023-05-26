"""
Transformations for IPv4 addresses.
"""

import re
import typing

# Regular expression matching an IPv4 address with an optional mask.
#
# This regular expression is design so that groups 1 to 4 capture the
# individual byte of the IP address and group 5 captures the subnet mask (if
# present).
_IPV4_REGEXP = re.compile(
    "([0-9]+)\\.([0-9]+)\\.([0-9]+)\\.([0-9]+)(?:/([0-9]+))?"
)


def broadcast_address(
    value: str, raise_error_if_malformed: bool = False
) -> str:
    """
    Calculate the broadcast address for an IPv4 address and subnet mask.

    The subnet mask must be given as part of the input string (separated from
    the IP address by a forward slash) and is not included in the returned
    broadcast address.

    For example, an input of "192.168.0.1/24" results in "192.168.0.255".

    :param value:
        input IP address and mask to be transformed.
    :param raise_error_if_malformed:
        ``True`` if a malformed IP address or mask should result in a
        ``ValueError`` being raised, ``False`` if it should result in the input
        value being returned as is. The default is ``False``.
    :return:
        broadcast address for the specified IP address and mask.
    """
    try:
        addr_bytes, mask = _str_to_addr_bytes_and_mask(value)
    except ValueError:
        if raise_error_if_malformed:
            raise
        return value
    if mask is None:
        if raise_error_if_malformed:
            raise ValueError(
                "Cannot calculate net address for IP address without subnet "
                f"mask: {value}"
            )
        return value
    addr_as_int = (
        (addr_bytes[0] << 24)
        + (addr_bytes[1] << 16)
        + (addr_bytes[2] << 8)
        + addr_bytes[3]
    )
    mask_as_int = 2 ** (32 - mask) - 1
    addr_as_int = addr_as_int | mask_as_int
    addr_bytes[0] = (addr_as_int >> 24) & 255
    addr_bytes[1] = (addr_as_int >> 16) & 255
    addr_bytes[2] = (addr_as_int >> 8) & 255
    addr_bytes[3] = addr_as_int & 255
    return f"{addr_bytes[0]}.{addr_bytes[1]}.{addr_bytes[2]}.{addr_bytes[3]}"


def net_address(value: str, raise_error_if_malformed: bool = False) -> str:
    """
    Calculate the network address for an IPv4 address and subnet mask.

    The subnet mask must be given as part of the input string (separated from
    the IP address by a forward slash) and is included in the returned net
    address.

    For example, an input of "192.168.0.1/24" results in "192.168.0.0/24".

    :param value:
        input IP address and mask to be transformed.
    :param raise_error_if_malformed:
        ``True`` if a malformed IP address or mask should result in a
        ``ValueError`` being raised, ``False`` if it should result in the input
        value being returned as is. The default is ``False``.
    :return:
        network address for the specified IP address and mask.
    """
    try:
        addr_bytes, mask = _str_to_addr_bytes_and_mask(value)
    except ValueError:
        if raise_error_if_malformed:
            raise
        return value
    if mask is None:
        if raise_error_if_malformed:
            raise ValueError(
                "Cannot calculate net address for IP address without subnet "
                f"mask: {value}"
            )
        return value
    addr_as_int = (
        (addr_bytes[0] << 24)
        + (addr_bytes[1] << 16)
        + (addr_bytes[2] << 8)
        + addr_bytes[3]
    )
    mask_as_int = (2**32 - 1) & ~(2 ** (32 - mask) - 1)
    addr_as_int = addr_as_int & mask_as_int
    addr_bytes[0] = (addr_as_int >> 24) & 255
    addr_bytes[1] = (addr_as_int >> 16) & 255
    addr_bytes[2] = (addr_as_int >> 8) & 255
    addr_bytes[3] = addr_as_int & 255
    return (
        f"{addr_bytes[0]}.{addr_bytes[1]}.{addr_bytes[2]}.{addr_bytes[3]}/"
        f"{mask}"
    )


def normalize(value: str, raise_error_if_malformed: bool = False) -> str:
    """
    Normalize an IPv4 address.

    This function takes an IPv4 address (as a ``str``) and transforms it into a
    normalized form. This means that each byte of the IP address is represented
    without leading zeros. If a mask is specified (separated from the IP
    address by a forward slash), it is also transformed to not include any
    leading zeros.

    When a malformed IP address is encountered, the behavior depends on the
    ``raise_error_if_malformed`` option. If that option is set to ``True``, a
    ``ValueError`` is raised. If it is ``False`` (the default), the input value
    is returned unchanged.

    :param value:
        input IP address to be transformed.
    :param raise_error_if_malformed:
        ``True`` if a malformed IP address should result in a ``ValueError``
        being raised, ``False`` if it should result in the input value being
        returned as is. The default is ``False``.
    :return:
        normalized form of the input IP address.
    """
    try:
        addr_bytes, mask = _str_to_addr_bytes_and_mask(value)
    except ValueError:
        if raise_error_if_malformed:
            raise
        return value
    value = f"{addr_bytes[0]}.{addr_bytes[1]}.{addr_bytes[2]}.{addr_bytes[3]}"
    if mask is not None:
        value = f"{value}/{mask}"
    return value


def strip_mask(value: str, raise_error_if_malformed: bool = False) -> str:
    """
    Strip a subnet mask from an IPv4 address (if present).

    For example, for the input string "192.168.0.1/24", this returns
    "192.168.0.1". If the input IP address does not specify a subnet mask, it
    is returned as is.

    :param value:
        input IP address to be transformed.
    :param raise_error_if_malformed:
        ``True`` if a malformed IP address should result in a ``ValueError``
        being raised, ``False`` if it should result in the input value being
        returned as is. The default is ``False``.
    :return:
        input IP address with the subnet mask removed.
    """
    # We use _str_to_addr_bytes_and_mask to check that the value is
    # well-formed.
    try:
        _str_to_addr_bytes_and_mask(value)
    except ValueError:
        if raise_error_if_malformed:
            raise
        return value
    # Now we know that the value is well-formed, so we can simply cut
    # everything after the "/" character.
    value, _, _ = value.partition("/")
    return value


def _str_to_addr_bytes_and_mask(
    value: str,
) -> typing.Tuple[typing.List[int], typing.Optional[int]]:
    match = _IPV4_REGEXP.fullmatch(value)
    if match is None:
        raise ValueError(f"Not a valid IPv4 address: {value}")
    addr_bytes = match.group(1, 2, 3, 4)
    addr_bytes = [int(addr_byte) for addr_byte in addr_bytes]
    mask = match.group(5)
    if mask is not None:
        mask = int(mask)
    for addr_byte in addr_bytes:
        if addr_byte > 255:
            raise ValueError(f"Not a valid IPv4 address: {value}")
    if mask is not None and mask > 32:
        raise ValueError(f"Invalid mask in IPv4 address: {value}")
    return (addr_bytes, mask)
