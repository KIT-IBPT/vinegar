"""
Utilities for dealing with sockets.
"""

import re
import typing

# Regular expression that matches an IPv4 address that is encoded inside an IPv6
# address (e.g. ::ffff:127.0.0.1).
_IPV4_IN_IPV6_ADDRESS_REGEXP = re.compile(
    '::(?:ffff|FFFF):([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)')

def ipv6_address_unwrap(ipv6_address: str) -> str:
    """
    Unwrap an IPv4 address that is encoded in an IPv6 address.

    This function works on IPv6 address in the form ``::ffff:127.0.0.1``
    (``127.0.0.1`` might be any IPv4 address). If such an address is
    encountered, the actual IPv4 address is extracted and returned.

    For any string not matching this pattern, this function simply returns the
    original string.
    
    :param ipv6_address:
        string that might represent an IPv4 address wrapped in an IPv6 address
        (like ``::ffff::127.0.0.1``).
    :return:
        the unwrapped IPv4 address or ``ipv6_address`` if the string does not
        match the expected format.
    """
    match = _IPV4_IN_IPV6_ADDRESS_REGEXP.fullmatch(ipv6_address)
    if match:
        return match.group(1)
    else:
        return ipv6_address

def socket_address_to_str(socket_address: typing.Tuple):
    """
    Return the string representation of a socket address.

    :param socket_address:
        tuple representing a socket address. If the tuple contains at least two
        elements, the first two elements are treated as a host address and a
        port number. Otherwise, the only element of the tuple is simply
        converted to a string.
    """
    if len(socket_address) < 2:
        return str(socket_address[0])
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
