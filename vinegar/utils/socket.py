"""
Utilities for dealing with sockets.
"""

import socket
import typing


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
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff'):
        return socket.inet_ntop(socket.AF_INET, addr_bytes[-4:])
    return ipv6_address


def socket_address_to_str(socket_address: typing.Tuple) -> str:
    """
    Return the string representation of a socket address.

    :param socket_address:
        tuple representing a socket address. If the tuple contains at least two
        elements, the first two elements are treated as a host address and a
        port number. Otherwise, the only element of the tuple is simply
        converted to a string.
    """
    if len(socket_address) < 2:
        return ipv6_address_unwrap(str(socket_address[0]))
    host = str(socket_address[0])
    port = str(socket_address[1])
    # IPv4 addresses might appear as IPv6 address when we use a dual-stack
    # socket. We want to convert such addresses to pure IPv4 addresses.
    host = ipv6_address_unwrap(host)
    # If the host address is an IPv6 address, we want to wrap it in brackets.
    if ':' in host:
        return '[{0}]:{1}'.format(host, port)
    else:
        return '{0}:{1}'.format(host, port)
