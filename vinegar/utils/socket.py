"""
Utilities for dealing with sockets.
"""

import typing

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
    # If the host address is an IPv6 address, we want to wrap it in brackets.
    if ':' in host:
        return '[{0}]:{1}'.format(host, port)
    else:
        return '{0}:{1}'.format(host, port)
