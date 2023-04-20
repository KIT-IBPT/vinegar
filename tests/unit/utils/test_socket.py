"""
Tests for `vinegar.utils.socket`.
"""

import unittest

from vinegar.utils.socket import (
    contains_ip_address,
    ipv6_address_unwrap,
    socket_address_to_str,
)


class TestSocket(unittest.TestCase):
    """
    Tests for the `vingear.utils.socket` module.
    """

    def test_contains_ip_address_empty_list(self):
        """
        Test the ``contains_ip_address`` function (with an empty list).
        """
        # An empty list should not cause an exception.
        self.assertFalse(contains_ip_address([], "192.168.0.1"))
        self.assertFalse(contains_ip_address([], "::1", True))

    def test_contains_ip_address_malformed(self):
        """
        Test the ``contains_ip_address`` function with malformed input.
        """
        # A malformed IP address (whether it is in the set of IP addresses or
        # the IP address to be tested) should only cause an exception if the
        # raise_error_if_malformed flag is set.
        self.assertFalse(contains_ip_address([], "127.0.0.1/8"))
        with self.assertRaises(ValueError):
            contains_ip_address(
                [], "127.0.0.1/8", raise_error_if_malformed=True
            )
        self.assertFalse(contains_ip_address([], "abcd"))
        with self.assertRaises(ValueError):
            contains_ip_address([], "abcd", raise_error_if_malformed=True)
        self.assertFalse(contains_ip_address(["abcd"], "127.0.0.1"))
        with self.assertRaises(ValueError):
            contains_ip_address(
                ["abcd"],
                "127.0.0.1",
                raise_error_if_malformed=True,
            )
        # This is malformed because we did not allow a netmask. When the
        # raise_error_if_malformed flag is set, this should return False
        # because the entry with the netmask is ignored (even though it would
        # match).
        self.assertFalse(
            contains_ip_address(
                ["127.0.0.1/32"], "127.0.0.1", allow_netmask=False
            )
        )
        with self.assertRaises(ValueError):
            contains_ip_address(
                ["127.0.0.1/8"],
                "127.0.0.1",
                allow_netmask=False,
                raise_error_if_malformed=True,
            )

    def test_contains_ip_address_no_netmask(self):
        """
        Test the ``contains_ip_address`` function with ``allow_netmask=False``.
        """
        # We specify entries with a netmask here, even though we test with
        # allow_netmask=False. These entries should simply be ignored.
        ip_addresses = [
            "192.168.1.0/24",
            "10.0.37.35/27",
            "10.1.0.25/32",
            "10.2.3.27",
            "10.4.2.31",
            "fc00::ab:0/112",
            "fc00::13:1/110",
            "fc00::1234/128",
            "fc00::c5:4",
            "fc00::1234:d3:abcd",
            "::ffff:10.27.0.4/112",
            "::ffff:10.117.32.3",
        ]
        # Tests for 10.2.3.27.
        self.assertTrue(
            contains_ip_address(ip_addresses, "10.2.3.27", allow_netmask=False)
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "10.2.3.26", allow_netmask=False)
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "10.2.3.28", allow_netmask=False)
        )
        # Tests for 10.4.2.31.
        self.assertTrue(
            contains_ip_address(ip_addresses, "10.4.2.31", allow_netmask=False)
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "10.4.2.30", allow_netmask=False)
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "10.4.2.32", allow_netmask=False)
        )
        # Tests for fc00::c5:4.
        self.assertTrue(
            contains_ip_address(
                ip_addresses, "fc00::c5:4", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "fc00::c5:3", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "fc00::c5:5", allow_netmask=False
            )
        )
        # Tests for fc00::1234:d3:abcd.
        self.assertTrue(
            contains_ip_address(
                ip_addresses, "fc00::1234:d3:abcd", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "fc00::1234:d3:abcc", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "fc00::1234:d3:abce", allow_netmask=False
            )
        )
        # Tests for ::ffff:10.117.32.3.
        self.assertTrue(
            contains_ip_address(
                ip_addresses, "10.117.32.3", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "10.117.32.2", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "10.117.32.4", allow_netmask=False
            )
        )
        # Tests with IPv4-mapped IPv6 addresses.
        self.assertTrue(
            contains_ip_address(
                ip_addresses, "::ffff:10.117.32.3", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "::ffff:10.117.32.2", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "::ffff:10.117.32.4", allow_netmask=False
            )
        )
        # The entries that specify a subnet mask should be ignored, so they
        # should not produce any matches.
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "192.168.1.0", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "10.0.37.32", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "10.1.0.25", allow_netmask=False)
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "fc00::ab:0", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "fc00::12:0", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "fc00::1234", allow_netmask=False
            )
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "10.27.0.0", allow_netmask=False)
        )
        self.assertFalse(
            contains_ip_address(
                ip_addresses, "::ffff:192.168.1.0", allow_netmask=False
            )
        )

    def test_contains_ip_address_with_netmask(self):
        """
        Test the ``contains_ip_address`` function with ``allow_netmask=True``.
        """
        ip_addresses = [
            "192.168.1.0/24",
            "10.0.37.35/27",
            "10.1.0.25/32",
            "10.2.3.27",
            "10.4.2.31",
            "fc00::ab:0/112",
            "fc00::13:1/110",
            "fc00::1234/128",
            "fc00::c5:4",
            "fc00::1234:d3:abcd",
            "::ffff:10.27.0.4/112",
            "::ffff:10.117.32.3",
        ]
        # Tests for 192.168.1.0/24.
        self.assertTrue(contains_ip_address(ip_addresses, "192.168.1.0"))
        self.assertTrue(contains_ip_address(ip_addresses, "192.168.1.255"))
        self.assertFalse(contains_ip_address(ip_addresses, "192.168.0.255"))
        self.assertFalse(contains_ip_address(ip_addresses, "192.168.2.0"))
        # Tests for 10.0.37.35/27.
        self.assertTrue(contains_ip_address(ip_addresses, "10.0.37.32"))
        self.assertTrue(contains_ip_address(ip_addresses, "10.0.37.63"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.0.37.31"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.0.37.64"))
        # Tests for 10.1.0.25/32.
        self.assertTrue(contains_ip_address(ip_addresses, "10.1.0.25"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.1.0.24"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.1.0.26"))
        # Tests for 10.2.3.27.
        self.assertTrue(contains_ip_address(ip_addresses, "10.2.3.27"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.2.3.26"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.2.3.28"))
        # Tests for 10.4.2.31.
        self.assertTrue(contains_ip_address(ip_addresses, "10.4.2.31"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.4.2.30"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.4.2.32"))
        # Tests fc00::ab:0/112.
        self.assertTrue(contains_ip_address(ip_addresses, "fc00::ab:0"))
        self.assertTrue(contains_ip_address(ip_addresses, "fc00::ab:ffff"))
        self.assertFalse(contains_ip_address(ip_addresses, "fc00::aa:ffff"))
        self.assertFalse(contains_ip_address(ip_addresses, "fc00::ac:0"))
        # Tests fc00::13:1/110.
        self.assertTrue(contains_ip_address(ip_addresses, "fc00::10:0"))
        self.assertTrue(contains_ip_address(ip_addresses, "fc00::13:ffff"))
        self.assertFalse(contains_ip_address(ip_addresses, "fc00::0f:ffff"))
        self.assertFalse(contains_ip_address(ip_addresses, "fc00::14:0"))
        # Tests for fc00::1234/128.
        self.assertTrue(contains_ip_address(ip_addresses, "fc00::1234"))
        self.assertFalse(contains_ip_address(ip_addresses, "fc00::1233"))
        self.assertFalse(contains_ip_address(ip_addresses, "fc00::1235"))
        # Tests for fc00::c5:4.
        self.assertTrue(contains_ip_address(ip_addresses, "fc00::c5:4"))
        self.assertFalse(contains_ip_address(ip_addresses, "fc00::c5:3"))
        self.assertFalse(contains_ip_address(ip_addresses, "fc00::c5:5"))
        # Tests for fc00::1234:d3:abcd.
        self.assertTrue(
            contains_ip_address(ip_addresses, "fc00::1234:d3:abcd")
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "fc00::1234:d3:abcc")
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "fc00::1234:d3:abce")
        )
        # Tests for ::ffff:10.27.0.4/112.
        self.assertTrue(contains_ip_address(ip_addresses, "10.27.0.0"))
        self.assertTrue(contains_ip_address(ip_addresses, "10.27.255.255"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.26.255.255"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.28.0.0"))
        # Tests for ::ffff:10.117.32.3.
        self.assertTrue(contains_ip_address(ip_addresses, "10.117.32.3"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.117.32.2"))
        self.assertFalse(contains_ip_address(ip_addresses, "10.117.32.4"))
        # Tests with IPv4-mapped IPv6 addresses.
        self.assertTrue(
            contains_ip_address(ip_addresses, "::ffff:192.168.1.0")
        )
        self.assertTrue(
            contains_ip_address(ip_addresses, "::ffff:192.168.1.255")
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "::ffff:192.168.0.255")
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "::ffff:192.168.2.0")
        )
        self.assertTrue(
            contains_ip_address(ip_addresses, "::ffff:10.117.32.3")
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "::ffff:10.117.32.2")
        )
        self.assertFalse(
            contains_ip_address(ip_addresses, "::ffff:10.117.32.4")
        )

    def test_ipv6_address_unwrap(self):
        """
        Test the ``ipv6_address_unwrap`` function.
        """
        # Regularly formatted IPv4-mapped IPv6 addresses.
        self.assertEqual("1.2.3.4", ipv6_address_unwrap("::ffff:1.2.3.4"))
        self.assertEqual("127.0.0.1", ipv6_address_unwrap("::FFFF:127.0.0.1"))
        # Unusually formatted IPv4-mapped IPv6 addresses.
        self.assertEqual("1.2.3.4", ipv6_address_unwrap("::ffff:0102:0304"))
        self.assertEqual("127.0.0.1", ipv6_address_unwrap("::FfFf:7f00:1"))
        # Strings that are not IPv4-mapped IPv6 addresses
        self.assertEqual("abc", ipv6_address_unwrap("abc"))
        self.assertEqual("fc00::abcd", ipv6_address_unwrap("fc00::abcd"))

    def test_socket_address_to_str(self):
        """
        Test the ``socket_address_to_str`` function.
        """
        # IP address only.
        self.assertEqual("127.0.0.1", socket_address_to_str(("127.0.0.1",)))
        self.assertEqual("1.2.3.4", socket_address_to_str(("::ffff:1.2.3.4",)))
        self.assertEqual("fc00::1234", socket_address_to_str(("fc00::1234",)))
        # IP address and port number.
        self.assertEqual(
            "127.0.0.1:123", socket_address_to_str(("127.0.0.1:123",))
        )
        self.assertEqual(
            "1.2.3.4:456", socket_address_to_str(("::ffff:1.2.3.4", 456))
        )
        self.assertEqual(
            "[fc00::1234]:789", socket_address_to_str(("fc00::1234", 789))
        )
