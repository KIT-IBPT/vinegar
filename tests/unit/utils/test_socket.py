"""
Tests for `vinegar.utils.socket`.
"""

import unittest

from vinegar.utils.socket import ipv6_address_unwrap, socket_address_to_str


class TestSocket(unittest.TestCase):
    """
    Tests for the `vingear.utils.socket` module.
    """

    def test_ipv6_address_unwrap(self):
        """
        Test the ``ipv6_address_unwrap`` function.
        """
        # Regularly formatted IPv4-mapped IPv6 addresses.
        self.assertEqual("1.2.3.4", ipv6_address_unwrap('::ffff:1.2.3.4'))
        self.assertEqual("127.0.0.1", ipv6_address_unwrap('::FFFF:127.0.0.1'))
        # Unusually formatted IPv4-mapped IPv6 addresses.
        self.assertEqual("1.2.3.4", ipv6_address_unwrap('::ffff:0102:0304'))
        self.assertEqual("127.0.0.1", ipv6_address_unwrap('::FfFf:7f00:1'))
        # Strings that are not IPv4-mapped IPv6 addresses
        self.assertEqual("abc", ipv6_address_unwrap('abc'))
        self.assertEqual("fc00::abcd", ipv6_address_unwrap('fc00::abcd'))

    def test_socket_address_to_str(self):
        """
        Test the ``socket_address_to_str`` function.
        """
        # IP address only.
        self.assertEqual("127.0.0.1", socket_address_to_str(('127.0.0.1',)))
        self.assertEqual("1.2.3.4", socket_address_to_str(('::ffff:1.2.3.4',)))
        self.assertEqual("fc00::1234", socket_address_to_str(('fc00::1234',)))
        # IP address and port number.
        self.assertEqual(
            "127.0.0.1:123", socket_address_to_str(('127.0.0.1:123',)))
        self.assertEqual(
            "1.2.3.4:456", socket_address_to_str(('::ffff:1.2.3.4', 456)))
        self.assertEqual(
            "[fc00::1234]:789", socket_address_to_str(('fc00::1234', 789)))
