"""
Tests for `vinegar.transform.misc`.
"""

import unittest

from vinegar.transform import apply_transformation
from vinegar.transform.misc import to_int


class TestMiscModule(unittest.TestCase):
    """
    Tests for the `vinegar.transform.misc` module.
    """

    def test_to_int(self):
        """
        Test the `to_int` function.
        """
        # Test that the "to_int" function can be called via
        # apply_transformation.
        self.assertEqual(5, apply_transformation("misc.to_int", "5"))
        # Test the raise_error_if_malformed parameter.
        self.assertEqual(27, to_int("27"))
        self.assertEqual(27, to_int("27", raise_error_if_malformed=False))
        self.assertEqual(27, to_int("27", raise_error_if_malformed=True))
        self.assertEqual("foo", to_int("foo"))
        self.assertEqual("foo", to_int("foo", raise_error_if_malformed=False))
        with self.assertRaises(ValueError):
            to_int("foo", raise_error_if_malformed=True)
