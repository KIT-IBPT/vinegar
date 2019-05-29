"""
Tests for `vinegar.utils.odict`.
"""

import unittest

from vinegar.utils.odict import OrderedDict

class TestOdictModule(unittest.TestCase):
    """
    Tests for the `vingear.utils.odict` module.
    """

    def test_preserves_order(self):
        """
        Test that the ``OrderedDict`` provided by the module does in fact
        preserve the insertion order.
        """
        d = OrderedDict()
        l = [5, 1, 12, 2, 3, 6, 4]
        for i in l:
            d[i] = i
        self.assertEqual(l, list(d.keys()))
        self.assertEqual(l, list(d.values()))
