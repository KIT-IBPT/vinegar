"""
Transformations for both IPv4 and IPv6 addresses.
"""

import re

from vinegar.utils.socket import ipv6_address_unwrap as _ipv6_address_unwrap

from .ipv4_address import net_address as _net_address_ipv4
from .ipv4_address import normalize as _normalize_ipv4
from .ipv4_address import strip_mask as _strip_mask_ipv4
from .ipv6_address import net_address as _net_address_ipv6
from .ipv6_address import normalize as _normalize_ipv6
from .ipv6_address import strip_mask as _strip_mask_ipv6

# Regular expression matching an IPv4 address with an optional mask.
#
# This regular expression is design so that groups 1 to 4 capture the
# individual byte of the IP address and group 5 captures the subnet mask (if
# present).
_IPV4_REGEXP = re.compile(
    "([0-9]+)\\.([0-9]+)\\.([0-9]+)\\.([0-9]+)(?:/([0-9]+))?"
)


def net_address(value: str, raise_error_if_malformed: bool = False) -> str:
    """
    Calculate the network address for an IPv4 or IPv6 address and subnet mask.

    The subnet mask must be given as part of the input string (separated from
    the IP address by a forward slash) and is included in the returned net
    address.

    For example, an input of "192.168.0.1/24" results in "192.168.0.0/24" and
    an input of "2001:db8::1/32" results in "2001:db8::/32".

    :param value:
        input IP address and mask to be transformed.
    :param raise_error_if_malformed:
        ``True`` if a malformed IP address or mask should result in a
        ``ValueError`` being raised, ``False`` if it should result in the input
        value being returned as is. The default is ``False``.
    :return:
        network address for the specified IP address and mask.
    """
    # If the value matches our regular expression for an IPv4 address, we
    # delegate to the ipv4_address module. Otherwise, we delegate to the
    # ipv6_address module.
    if _IPV4_REGEXP.fullmatch(value):
        return _net_address_ipv4(value, raise_error_if_malformed)
    return _net_address_ipv6(value, raise_error_if_malformed)


def normalize(value: str, raise_error_if_malformed: bool = False) -> str:
    """
    Normalize an IPv4 or IPv6 address.

    This function takes an IPv4 or IPv6 address (as a ``str``) and transforms
    it into a normalized form. For an IPv4 address, this means that each byte
    of the IP address is represented without leading zeros. For an IPv6
    address, the normalized form of the address should be close to the format
    format as defined by `RFC 5952 <https://tools.ietf.org/html/rfc5952>`_, but
    the actual return value might differ slightly. IPv6 addresses of the form
    "::ffff:1.2.3.4" (which typically only occur when handling IPv4 connections
    on IPv6 sockets) are transformed to an IPv4 address and then normalized
    according to the regular rules. If a mask is specified (separated from the
    IP address by a forward slash), it is also transformed to not include any
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
    # If we have an IPv4-mapped IPv6 address, we extract the IPv4 address
    # before normalizing it. Otherwise, we check whether the value matches our
    # regular expression for an IPv4 address and delegate to the ipv4_address
    # module or ipv6_address module, depending on the result of this test.
    value = _ipv6_address_unwrap(value)
    if _IPV4_REGEXP.fullmatch(value):
        return _normalize_ipv4(value, raise_error_if_malformed)
    return _normalize_ipv6(value, raise_error_if_malformed)


def strip_mask(value: str, raise_error_if_malformed: bool = False) -> str:
    """
    Strip a subnet mask from an IPv4 or IPv6 address (if present).

    For example, for the input string "192.168.0.1/24", this returns
    "192.168.0.1", and for "2001:db8::1/32", this returns "2001:db8::1". If the
    input IP address does not specify a subnet mask, it is returned as is.

    :param value:
        input IP address to be transformed.
    :param raise_error_if_malformed:
        ``True`` if a malformed IP address should result in a ``ValueError``
        being raised, ``False`` if it should result in the input value being
        returned as is. The default is ``False``.
    :return:
        input IP address with the subnet mask removed.
    """
    # If the value matches our regular expression for an IPv4 address, we
    # delegate to the ipv4_address module. Otherwise, we delegate to the
    # ipv6_address module.
    if _IPV4_REGEXP.fullmatch(value):
        return _strip_mask_ipv4(value, raise_error_if_malformed)
    return _strip_mask_ipv6(value, raise_error_if_malformed)
