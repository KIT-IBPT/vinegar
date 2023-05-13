"""
Transformations for IPv6 addresses.
"""

import socket
import typing


def net_address(value: str, raise_error_if_malformed: bool = False) -> str:
    """
    Calculate the network address for an IPv6 address and subnet mask.

    The subnet mask must be given as part of the input string (separated from
    the IP address by a forward slash) and is included in the returned net
    address.

    For example, an input of "2001:db8::1/32" results in "2001:db8::/32".

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
                "mask: {0}".format(value)
            )
        return value
    offset = 0
    addr_as_int = 0
    for addr_byte in reversed(addr_bytes):
        addr_as_int += addr_byte << offset
        offset += 8
    mask_as_int = (2**128 - 1) & ~(2 ** (128 - mask) - 1)
    addr_as_int = addr_as_int & mask_as_int
    addr_bytes = bytearray(len(addr_bytes))
    offset = 120
    for i, _ in enumerate(addr_bytes):
        addr_bytes[i] = (addr_as_int >> offset) & 255
        offset -= 8
    return "%s/%d" % (socket.inet_ntop(socket.AF_INET6, addr_bytes), mask)


def normalize(value: str, raise_error_if_malformed: bool = False) -> str:
    """
    Normalize an IPv6 address.

    This function takes an IPv6 address (as a ``str``) and transforms it into a
    normalized form. The normalized form of the address should be close to the
    format as defined by `RFC 5952 <https://tools.ietf.org/html/rfc5952>`_, but
    the actual return value might differ slightly.

    .. note::

        Internally, this method uses ``socket.inet_pton`` and
        ``socket.inet_ntop`` to normalize the address. This means that the
        actual result might differ slightly depending on the platform. However,
        it is guaranteed that when normalizing different forms of the same
        address, the normalized form will always be the same when doing this on
        the same platform.

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
    value = socket.inet_ntop(socket.AF_INET6, addr_bytes)
    if mask is not None:
        value = "{0}/{1}".format(value, mask)
    return value


def strip_mask(value: str, raise_error_if_malformed: bool = False) -> str:
    """
    Strip a subnet mask from an IPv6 address (if present).

    For example, for the input string "2001:db8::1/32", this returns
    "2001:db8::1". If the input IP address does not specify a subnet mask, it
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
) -> typing.Tuple[bytes, typing.Optional[int]]:
    if "/" in value:
        (addr, mask) = value.split("/", 1)
    else:
        addr = value
        mask = None
    try:
        addr_bytes = socket.inet_pton(socket.AF_INET6, addr)
    except OSError:
        raise ValueError("Invalid IPv6 address: %s" % value) from None
    if mask is not None:
        try:
            mask = int(mask)
            if mask < 0 or mask > 128:
                raise ValueError()
        except ValueError:
            # We are not interested in the original exception because the
            # exception that we raise here contains all the necessary
            # information.
            #
            # pylint: disable=raise-missing-from
            raise ValueError("Invalid mask in IPv6 address: {0}".format(value))
    return addr_bytes, mask
