"""
Tests for `vinegar.transform.ipv4_address`.
"""

import unittest

from vinegar.transform import apply_transformation
from vinegar.transform.ipv4_address import (
    broadcast_address, net_address, normalize, strip_mask)

class TestIPv4AddressModule(unittest.TestCase):
    """
    Tests for the `vinegar.transform.ipv4_address` module.
    """

    def test_broadcast_address(self):
        """
        Test the `broadcast_address` function.
        """
        # Test that the "broadcast_address" function can be called via
        # apply_transformation.
        self.assertEqual(
            '192.168.0.255',
            apply_transformation(
                'ipv4_address.broadcast_address', '192.168.0.1/24'))
        # Test that an address is implicitly normalized
        self.assertEqual(
            '192.168.0.255', broadcast_address('192.168.000.1/24'))
        # Test the raise_error_if_malformed option.
        self.assertEqual(
            '192.168.0.255', broadcast_address('192.168.000.1/24'))
        self.assertEqual(
            '192.168.0.255',
            broadcast_address(
                '192.168.000.1/24', raise_error_if_malformed=False))
        self.assertEqual(
            '192.168.0.255',
            broadcast_address(
                '192.168.000.1/24', raise_error_if_malformed=True))
        self.assertEqual(
            '192.168.0.256/24',
            broadcast_address('192.168.0.256/24'))
        self.assertEqual(
            '192.168.0.256/24',
            broadcast_address(
                '192.168.0.256/24', raise_error_if_malformed=False))
        with self.assertRaises(ValueError):
            broadcast_address(
                '192.168.0.256/24', raise_error_if_malformed=True)
        # An address is also considered malformed if the mask is missing.
        with self.assertRaises(ValueError):
            broadcast_address(
                '192.168.0.1', raise_error_if_malformed=True)
        # We also want to test two corner cases.
        self.assertEqual(
            '192.168.0.1',
            broadcast_address('192.168.0.1/32'))
        self.assertEqual(
            '255.255.255.255',
            broadcast_address('192.168.0.1/0'))

    def test_net_address(self):
        """
        Test the `net_address` function.
        """
        # Test that the "broadcast_address" function can be called via
        # apply_transformation.
        self.assertEqual(
            '192.168.0.0/24',
            apply_transformation(
                'ipv4_address.net_address', '192.168.0.1/24'))
        # Test that an address is implicitly normalized
        self.assertEqual(
            '192.168.0.0/24', net_address('192.168.000.1/24'))
        # Test the raise_error_if_malformed option.
        self.assertEqual(
            '192.168.0.0/24', net_address('192.168.000.1/24'))
        self.assertEqual(
            '192.168.0.0/24',
            net_address('192.168.000.1/24', raise_error_if_malformed=False))
        self.assertEqual(
            '192.168.0.0/24',
            net_address('192.168.000.1/24', raise_error_if_malformed=True))
        self.assertEqual(
            '192.168.0.256/24', net_address('192.168.0.256/24'))
        self.assertEqual(
            '192.168.0.256/24',
            net_address('192.168.0.256/24', raise_error_if_malformed=False))
        with self.assertRaises(ValueError):
            net_address('192.168.0.256/24', raise_error_if_malformed=True)
        # An address is also considered malformed if the mask is missing.
        with self.assertRaises(ValueError):
            net_address('192.168.0.1', raise_error_if_malformed=True)
        # We also want to test two corner cases.
        self.assertEqual(
            '192.168.0.1/32', net_address('192.168.0.1/32'))
        self.assertEqual(
            '0.0.0.0/0', net_address('192.168.0.1/0'))

    def test_normalize(self):
        """
        Test the `normalize` function.
        """
        # Test that the "normalize" function can be called via
        # apply_transformation.
        self.assertEqual(
            '192.168.0.1',
            apply_transformation('ipv4_address.normalize', '192.168.000.001'))
        # Test that leading zeros are removed.
        self.assertEqual(
            '10.0.0.1',
            normalize('010.000.000000.1'))
        self.assertEqual(
            '10.0.0.1/16',
            normalize('010.000.000000.1/016'))
        # Test the raise_error_if_malformed parameter.
        self.assertEqual(
            '192.168.0.1',
            normalize('192.168.0.1'))
        self.assertEqual(
            '192.168.0.1',
            normalize('192.168.0.1', raise_error_if_malformed=False))
        self.assertEqual(
            '192.168.0.1',
            normalize('192.168.0.1', raise_error_if_malformed=True))
        self.assertEqual(
            'not an IP address',
            normalize('not an IP address'))
        self.assertEqual(
            'not an IP address',
            normalize('not an IP address', raise_error_if_malformed=False))
        with self.assertRaises(ValueError):
            normalize('not an IP address', raise_error_if_malformed=True)

    def test_strip_mask(self):
        """
        Test the `strip_mask` function.
        """
        # Test that the "strip_mask" function can be called via
        # apply_transformation.
        self.assertEqual(
            '192.168.0.1',
            apply_transformation('ipv4_address.strip_mask', '192.168.0.1/24'))
        # Test that an address is not implicitly normalized
        self.assertEqual('192.168.000.1', strip_mask('192.168.000.1/24'))
        # Test the raise_error_if_malformed option.
        self.assertEqual('192.168.0.1', strip_mask('192.168.0.1/24'))
        self.assertEqual(
            '192.168.0.1',
            strip_mask('192.168.0.1/24', raise_error_if_malformed=False))
        self.assertEqual(
            '192.168.0.1',
            strip_mask('192.168.0.1/24', raise_error_if_malformed=True))
        self.assertEqual('192.168.0.256/24', strip_mask('192.168.0.256/24'))
        self.assertEqual(
            '192.168.0.256/24',
            strip_mask('192.168.0.256/24', raise_error_if_malformed=False))
        with self.assertRaises(ValueError):
            strip_mask('192.168.0.256/24', raise_error_if_malformed=True)
        # Not having a mask should not result in an error.
        self.assertEqual(
            '192.168.0.1',
            strip_mask('192.168.0.1', raise_error_if_malformed=True))
