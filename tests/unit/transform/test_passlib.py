"""
Tests for `vinegar.transform.passlib`.
"""

import unittest

from vinegar.transform import apply_transformation


class TestPasslibModule(unittest.TestCase):
    """
    Tests for the `vinegar.transform.passlib` module.
    """

    def setUp(self):
        try:
            import passlib
        except ImportError:
            self.skipTest('passlib is not installed.')

    def test_hash(self):
        """
        Test the ``hash`` function.
        """
        # The sha512 method should be used by default.
        self.assertEqual(
            '$6$ER1w5uHGxSXlzqTs$SaPcEH603VqKUdnredBtfjY1lrTIcMJdwQc62yKWeXiY2'
            'vkSBinPQ3ZGaFtT1hN4hs3H4jmpGwVA0fwzAyauy0',
            apply_transformation(
                'passlib.hash',
                'test',
                rounds=5000,
                salt='ER1w5uHGxSXlzqTs'))
        # The sha256 method should also be available.
        self.assertEqual(
            '$5$4P5LdkrXcicslB.6$Ajx85AjQYx/MSDlgdFuoOyja2v0Cy7LqzHqAcqQ1ke.',
            apply_transformation(
                'passlib.hash',
                'test',
                'sha256_crypt',
                rounds=5000,
                salt='4P5LdkrXcicslB.6'))
