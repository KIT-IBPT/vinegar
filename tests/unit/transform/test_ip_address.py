"""
Tests for `vinegar.transform.ip_address`.
"""

import unittest

from vinegar.transform import apply_transformation
from vinegar.transform.ip_address import net_address, normalize, strip_mask


class TestIPAddressModule(unittest.TestCase):
    """
    Tests for the `vinegar.transform.ip_address` module.
    """

    def test_net_address(self):
        """
        Test the `net_address` function.
        """
        # Test that the "net_address" function can be called via
        # apply_transformation.
        self.assertEqual(
            "192.168.0.0/24",
            apply_transformation("ip_address.net_address", "192.168.0.1/24"),
        )
        self.assertEqual(
            "2001:db8::/32",
            apply_transformation("ip_address.net_address", "2001:db8::1/32"),
        )
        # Test that an address is implicitly normalized
        self.assertEqual("192.168.0.0/24", net_address("192.168.000.1/24"))
        self.assertEqual("2001:db8::/32", net_address("2001:DB8::1/32"))
        # Test the raise_error_if_malformed option.
        self.assertEqual("192.168.0.0/24", net_address("192.168.000.1/24"))
        self.assertEqual(
            "192.168.0.0/24",
            net_address("192.168.000.1/24", raise_error_if_malformed=False),
        )
        self.assertEqual(
            "192.168.0.0/24",
            net_address("192.168.000.1/24", raise_error_if_malformed=True),
        )
        self.assertEqual("192.168.0.256/24", net_address("192.168.0.256/24"))
        self.assertEqual(
            "192.168.0.256/24",
            net_address("192.168.0.256/24", raise_error_if_malformed=False),
        )
        with self.assertRaises(ValueError):
            net_address("192.168.0.256/24", raise_error_if_malformed=True)
        self.assertEqual("2001:db8::/32", net_address("2001:db8:0::1/32"))
        self.assertEqual(
            "2001:db8::/32",
            net_address("2001:db8:0::1/32", raise_error_if_malformed=False),
        )
        self.assertEqual(
            "2001:db8::/32",
            net_address("2001:db8:0::1/32", raise_error_if_malformed=True),
        )
        self.assertEqual("2001:db8:0:::1/32", net_address("2001:db8:0:::1/32"))
        self.assertEqual(
            "2001:db8:0:::1/32",
            net_address("2001:db8:0:::1/32", raise_error_if_malformed=False),
        )
        with self.assertRaises(ValueError):
            net_address("2001:db8:0:::1/32", raise_error_if_malformed=True)
        # An address is also considered malformed if the mask is missing.
        with self.assertRaises(ValueError):
            net_address("192.168.0.1", raise_error_if_malformed=True)
        with self.assertRaises(ValueError):
            net_address("2001:db8::", raise_error_if_malformed=True)
        # We also want to test four corner cases.
        self.assertEqual("192.168.0.1/32", net_address("192.168.0.1/32"))
        self.assertEqual("0.0.0.0/0", net_address("192.168.0.1/0"))
        self.assertEqual("2001:db8::1/128", net_address("2001:db8::1/128"))
        self.assertEqual("::/0", net_address("2001:db8::1/0"))

    def test_normalize(self):
        """
        Test the `normalize` function.
        """
        # Test that the "normalize" function can be called via
        # apply_transformation.
        self.assertEqual(
            "192.168.0.1",
            apply_transformation("ip_address.normalize", "192.168.000.001"),
        )
        self.assertEqual(
            "2001:db8::1",
            apply_transformation("ip_address.normalize", "2001:0db8::1"),
        )
        # Test that leading zeros are removed.
        self.assertEqual("10.0.0.1", normalize("010.000.000000.1"))
        self.assertEqual("10.0.0.1/16", normalize("010.000.000000.1/016"))
        self.assertEqual("2001:db8::1", normalize("2001:0db8::0001"))
        self.assertEqual("2001:db8::1", normalize("2001:db8:0::1"))
        # Test the raise_error_if_malformed parameter.
        self.assertEqual("192.168.0.1", normalize("192.168.0.1"))
        self.assertEqual(
            "192.168.0.1",
            normalize("192.168.0.1", raise_error_if_malformed=False),
        )
        self.assertEqual(
            "192.168.0.1",
            normalize("192.168.0.1", raise_error_if_malformed=True),
        )
        self.assertEqual("not an IP address", normalize("not an IP address"))
        self.assertEqual(
            "not an IP address",
            normalize("not an IP address", raise_error_if_malformed=False),
        )
        with self.assertRaises(ValueError):
            normalize("not an IP address", raise_error_if_malformed=True)
        self.assertEqual("2001:db8::1", normalize("2001:db8::1"))
        self.assertEqual(
            "2001:db8::1",
            normalize("2001:db8::1", raise_error_if_malformed=False),
        )
        self.assertEqual(
            "2001:db8::1",
            normalize("2001:db8::1", raise_error_if_malformed=True),
        )
        self.assertEqual("not an IP address", normalize("not an IP address"))
        self.assertEqual(
            "not an IP address",
            normalize("not an IP address", raise_error_if_malformed=False),
        )
        with self.assertRaises(ValueError):
            normalize("not an IP address", raise_error_if_malformed=True)
        # Test the special case where an IPv4 address is embedded in an IPv6
        # address.
        self.assertEqual("10.0.0.1", normalize("::ffff:10.0.0.1"))
        # An address with a subnet mask should not be converted to an IPv4
        # address, because ::ffff:192.168.0.0/24 is not the same as
        # 192.168.0.0/24. In fact, 192.168.0.0/24 is the same as
        # ::ffff:192.168.0.0/120.
        self.assertEqual(
            "::ffff:192.168.0.15/24", normalize("::FFFF:192.168.0.15/24")
        )

    def test_strip_mask(self):
        """
        Test the `strip_mask` function.
        """
        # Test that the "strip_mask" function can be called via
        # apply_transformation.
        self.assertEqual(
            "192.168.0.1",
            apply_transformation("ip_address.strip_mask", "192.168.0.1/24"),
        )
        self.assertEqual(
            "2001:db8::1",
            apply_transformation("ip_address.strip_mask", "2001:db8::1/32"),
        )
        # Test that an address is not implicitly normalized
        self.assertEqual("192.168.000.1", strip_mask("192.168.000.1/24"))
        self.assertEqual("2001:db8:0::1", strip_mask("2001:db8:0::1/32"))
        # Test the raise_error_if_malformed option.
        self.assertEqual("192.168.0.1", strip_mask("192.168.0.1/24"))
        self.assertEqual(
            "192.168.0.1",
            strip_mask("192.168.0.1/24", raise_error_if_malformed=False),
        )
        self.assertEqual(
            "192.168.0.1",
            strip_mask("192.168.0.1/24", raise_error_if_malformed=True),
        )
        self.assertEqual("192.168.0.256/24", strip_mask("192.168.0.256/24"))
        self.assertEqual(
            "192.168.0.256/24",
            strip_mask("192.168.0.256/24", raise_error_if_malformed=False),
        )
        with self.assertRaises(ValueError):
            strip_mask("192.168.0.256/24", raise_error_if_malformed=True)
        self.assertEqual("2001:db8::1", strip_mask("2001:db8::1/32"))
        self.assertEqual(
            "2001:db8::1",
            strip_mask("2001:db8::1/32", raise_error_if_malformed=False),
        )
        self.assertEqual(
            "2001:db8::1",
            strip_mask("2001:db8::1/32", raise_error_if_malformed=True),
        )
        self.assertEqual("2001:db8:::1/32", strip_mask("2001:db8:::1/32"))
        self.assertEqual(
            "2001:db8:::1/32",
            strip_mask("2001:db8:::1/32", raise_error_if_malformed=False),
        )
        with self.assertRaises(ValueError):
            strip_mask("2001:db8:::1/32", raise_error_if_malformed=True)
        # Not having a mask should not result in an error.
        self.assertEqual(
            "192.168.0.1",
            strip_mask("192.168.0.1", raise_error_if_malformed=True),
        )
        self.assertEqual(
            "2001:db8::1",
            strip_mask("2001:db8::1", raise_error_if_malformed=True),
        )
