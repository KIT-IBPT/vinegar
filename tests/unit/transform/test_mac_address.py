"""
Tests for `vinegar.transform.mac_address`.
"""

import unittest

from vinegar.transform import apply_transformation
from vinegar.transform.mac_address import normalize


class TestMacAddressModule(unittest.TestCase):
    """
    Tests for the `vinegar.transform.mac_address` module.
    """

    def test_normalize(self):
        """
        Test the `normalize` function.
        """
        # Test that the "normalize" function can be called via
        # apply_transformation.
        self.assertEqual(
            "0A:0B:0C:0D:0E:1F",
            apply_transformation("mac_address.normalize", "0a:0B:0c:d:0E:1f"),
        )
        # Test the delimiter parameter.
        self.assertEqual("0A:0B:0C:0D:0E:1F", normalize("0a:0B:0c:d:0E:1f"))
        self.assertEqual(
            "0A:0B:0C:0D:0E:1F", normalize("0a:0B:0c:d:0E:1f", delimiter=":")
        )
        self.assertEqual(
            "0A:0B:0C:0D:0E:1F",
            normalize("0a:0B:0c:d:0E:1f", delimiter="colon"),
        )
        self.assertEqual(
            "0A-0B-0C-0D-0E-1F", normalize("0a:0B:0c:d:0E:1f", delimiter="-")
        )
        self.assertEqual(
            "0A-0B-0C-0D-0E-1F",
            normalize("0a:0B:0c:d:0E:1f", delimiter="dash"),
        )
        self.assertEqual(
            "0A-0B-0C-0D-0E-1F",
            normalize("0a:0B:0c:d:0E:1f", delimiter="minus"),
        )
        # Test the target_case parameter.
        self.assertEqual("0A:0B:0C:0D:0E:1F", normalize("0a:0B:0c:d:0E:1f"))
        self.assertEqual(
            "0A:0B:0C:0D:0E:1F",
            normalize("0a:0B:0c:d:0E:1f", target_case="upper"),
        )
        self.assertEqual(
            "0a:0b:0c:0d:0e:1f",
            normalize("0a:0B:0c:d:0E:1f", target_case="lower"),
        )
        # Test the raise_error_if_malformed parameter.
        self.assertEqual("0A:0B:0C:0D:0E:1F", normalize("0a:0B:0c:d:0E:1f"))
        self.assertEqual(
            "0A:0B:0C:0D:0E:1F",
            normalize("0a:0B:0c:d:0E:1f", raise_error_if_malformed=False),
        )
        self.assertEqual(
            "0A:0B:0C:0D:0E:1F",
            normalize("0a:0B:0c:d:0E:1f", raise_error_if_malformed=True),
        )
        self.assertEqual("not a MAC address", normalize("not a MAC address"))
        self.assertEqual(
            "not a MAC address",
            normalize("not a MAC address", raise_error_if_malformed=False),
        )
        with self.assertRaises(ValueError):
            normalize("not a MAC address", raise_error_if_malformed=True)
