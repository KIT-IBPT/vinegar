"""
Utilities for dealing with sockets and IP addresses.
"""

import re
import socket
import typing

# Regular expression that we use for matching the netmask portion of an IP
# address with a netmask.
_NETMASK_REGEXP = re.compile("[0-9]+")


def _ip_address_in_subnet(
    ip_address_bytes: bytes, network_address_bytes: bytes, netmask_bits: int
) -> bool:
    assert len(ip_address_bytes) == len(network_address_bytes)
    assert netmask_bits <= (len(ip_address_bytes) * 8)
    # First, we compare the full bytes of the two addresses.
    whole_bytes = netmask_bits // 8
    if ip_address_bytes[:whole_bytes] != network_address_bytes[:whole_bytes]:
        return False
    # Second, we compare the relevant bits of the last relevant byte.
    remaining_bits = netmask_bits % 8
    if remaining_bits == 0:
        return True
    ip_address_byte = ip_address_bytes[whole_bytes]
    network_address_byte = network_address_bytes[whole_bytes]
    byte_mask = 256 - (1 << (8 - remaining_bits))
    return (ip_address_byte & byte_mask) == (network_address_byte & byte_mask)


def _parse_ip_address(
    ip_address: str, allow_netmask: bool
) -> typing.Tuple[int, bytes, int]:
    original_ip_address = ip_address
    if allow_netmask and "/" in ip_address:
        ip_address, netmask = ip_address.rsplit("/", 1)
        if _NETMASK_REGEXP.fullmatch(netmask):
            netmask = int(netmask)
        else:
            ip_address = original_ip_address
            netmask = None
    else:
        netmask = None
    # First, we try to interpret the address as an IPv4 address.
    try:
        ip_address_bytes = socket.inet_pton(socket.AF_INET, ip_address)
        if netmask is None:
            netmask = 32
        elif netmask > 32:
            raise ValueError(
                f'Error parsing "{original_ip_address}": Invalid netmask.'
            )
        return socket.AF_INET, ip_address_bytes, netmask
    except OSError:
        # If there is an error, this most likely means that we are dealing with
        # an IPv6 address.
        pass
    try:
        ip_address_bytes = socket.inet_pton(socket.AF_INET6, ip_address)
        if netmask is None:
            netmask = 128
        elif netmask > 128:
            raise ValueError(
                f'Error parsing "{original_ip_address}": Invalid netmask.'
            )
        return socket.AF_INET6, ip_address_bytes, netmask
    except OSError as err:
        # The address is neither a valid IPv4 nor a valid IPv6 address.
        raise ValueError(
            f'Error parsing "{original_ip_address}": This neither is a valid '
            "IPv4 nor IPv6 address."
        ) from err


def _parse_ip_address_split_ipv4_ipv6(
    ip_address: str,
) -> typing.Tuple[typing.Optional[bytes], bytes]:
    ip_address_family, ip_address_bytes, _ = _parse_ip_address(
        ip_address, False
    )
    # If the IP address is an IPv4 address, we also convert it to an
    # IPv4-mapped IPv6 address in order to be able to correctly match it
    # against IPv6 candidate addresses. If it is an IPv4-mapped IPv6 address,
    # we also convert it to an IPv4 address in order to correctly match it
    # against IPv4 candidate addresses.
    if ip_address_family == socket.AF_INET:
        ip_address_bytes_ipv4 = ip_address_bytes
        ip_address_bytes_ipv6 = (
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff"
            + ip_address_bytes
        )
    elif ip_address_bytes.startswith(
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff"
    ):
        ip_address_bytes_ipv4 = ip_address_bytes[-4:]
        ip_address_bytes_ipv6 = ip_address_bytes
    else:
        ip_address_bytes_ipv4 = None
        ip_address_bytes_ipv6 = ip_address_bytes
    return ip_address_bytes_ipv4, ip_address_bytes_ipv6


Inet4SocketAddress = typing.Tuple[str, int]
"""
Alias for the address type used with ``AF_INET`` sockets.
"""

Inet6SocketAddress = typing.Tuple[str, int, int, int]
"""
Alias for the address type used with ``AF_INET6`` sockets.
"""

InetSocketAddress = typing.Union[Inet4SocketAddress, Inet6SocketAddress]
"""
Alias for the union of `Inet4SocketAddress` and `Inet6SocketAddress`.
"""


def contains_ip_address(
    ip_address_set: typing.Collection[str],
    ip_address: str,
    allow_netmask: bool = True,
    raise_error_if_malformed: bool = False,
) -> bool:
    """
    Check whether an IP address is contained in a set of IP addresses.

    This works with both IPv4 and IPv6 addresses. Optionally, the set of IP
    addresses may contain address ranges in CIDR notation (e.g.
    192.168.0.0/24).

    This function supports IPv4-mapped IPv6 addresses. Such addresses are
    treated like the IPv4 address that they represent.

    :param ip_address_set:
        list or set of IP addresses with which the  ``ip_address`` shall be
        compared. If ``allow_netmask`` is ``True``, this may include ranges of
        IP addresses specified using the CIDR notation.
    :param ip_address:
        IP address that shall be tested. This can be an IPv4 or an IPv6
        address.
    :param allow_netmask:
        ``True`` if ip_address_set may contain address ranges, ``False`` if it
        may only contain single IP addresses. The default is ``True``.
    :param raise_error_if_malformed:
        ``True`` if a malformed IP address in ``ip_address_set` or
        ``ip_address`` should result in a ``ValueError`` being raised.
        ``False`` if it should result in the entry being ignored (for
        ``ip_address_set``) or ``False`` being returned (for ``ip_address``).
    :return:
        ``True`` if ``ip_address`` is contained in ``ip_address_set``,
        ``False`` otherwise.
    """
    # We parse the IP address, returning the byte sequence both as an IPv4
    # address and an IPv4-mapped IPv6 address. If the original address is an
    # IPv6 address that is not an IPv4-mapped IPv6 address, the IPv4 address is
    # None.
    try:
        (
            ip_address_bytes_ipv4,
            ip_address_bytes_ipv6,
        ) = _parse_ip_address_split_ipv4_ipv6(ip_address)
    except ValueError:
        if raise_error_if_malformed:
            raise
        return False
    # Now, we can compare with all candidates until we find a match.
    for candidate_ip_address in ip_address_set:
        try:
            (
                candidate_ip_address_family,
                candidate_ip_address_bytes,
                candidate_ip_address_netmask,
            ) = _parse_ip_address(candidate_ip_address, allow_netmask)
        except ValueError:
            if raise_error_if_malformed:
                raise
            continue
        if (
            candidate_ip_address_family == socket.AF_INET
            and ip_address_bytes_ipv4
        ):
            if _ip_address_in_subnet(
                ip_address_bytes_ipv4,
                candidate_ip_address_bytes,
                candidate_ip_address_netmask,
            ):
                return True
        elif candidate_ip_address_family == socket.AF_INET6:
            if _ip_address_in_subnet(
                ip_address_bytes_ipv6,
                candidate_ip_address_bytes,
                candidate_ip_address_netmask,
            ):
                return True
    return False


def ipv6_address_unwrap(ipv6_address: str) -> str:
    """
    Unwrap an IPv4 address that is encoded in an IPv6 address.

    This function works on IPv6 address in the form ``::ffff:127.0.0.1``
    (``127.0.0.1`` might be any IPv4 address). This so-called IPv4-mapped IPv6
    addresses are described in RF 4291. If such an address is encountered
    (regardless of whether it uses the classic decimal-dot notation or the
    hexadecimal-colon notation), the actual IPv4 address is extracted and
    returned.

    For any string not representing such an address, this function simply
    returns the original string.

    :param ipv6_address:
        string that might represent an IPv4 address wrapped in an IPv6 address
        (like ``::ffff::127.0.0.1``).
    :return:
        the unwrapped IPv4 address or ``ipv6_address`` if the string does not
        match the expected format.
    """
    try:
        addr_bytes = socket.inet_pton(socket.AF_INET6, ipv6_address)
    except OSError:
        # This happens when the string does not represent a valid IPv6 address.
        return ipv6_address
    if addr_bytes.startswith(
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff"
    ):
        return socket.inet_ntop(socket.AF_INET, addr_bytes[-4:])
    return ipv6_address


def socket_address_to_str(socket_address: InetSocketAddress) -> str:
    """
    Return the string representation of a socket address.

    :param socket_address:
        tuple representing a socket address.
    """
    host, port = socket_address[:2]
    # IPv4 addresses might appear as IPv6 address when we use a dual-stack
    # socket. We want to convert such addresses to pure IPv4 addresses.
    host = ipv6_address_unwrap(host)
    # If the host address is an IPv6 address, we want to wrap it in brackets.
    if ":" in host:
        return f"[{host}]:{port}"
    return f"{host}:{port}"
