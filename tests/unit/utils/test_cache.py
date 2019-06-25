"""
Tests for `vinegar.utils.cache`.
"""

import unittest

from vinegar.utils.cache import LRUCache


class TestLRUCache(unittest.TestCase):
    """
    Tests for the `LRUCache`.
    """

    def test_eviction(self):
        """
        Test that keys are evicted in the right order when the cache size is
        exceeded.
        """
        cache = LRUCache(cache_size=3)
        cache['a'] = 'a'
        # Cache content should now be a
        self.assertIn('a', cache)
        cache['b'] = 'b'
        # Cache content should now be a, b
        self.assertIn('a', cache)
        self.assertIn('b', cache)
        # Cache content should now be a, b, c
        cache['c'] = 'c'
        self.assertIn('a', cache)
        self.assertIn('b', cache)
        self.assertIn('c', cache)
        cache['d'] = 'd'
        # Cache content should now be b, c, d
        self.assertNotIn('a', cache)
        self.assertIn('b', cache)
        self.assertIn('c', cache)
        self.assertIn('d', cache)
        # Reading b should mark it as used.
        self.assertEqual(cache['b'], 'b')
        # Cache content should now be c, d, b
        cache['a'] = 'a'
        # Cache content should now be d, b, a
        self.assertIn('a', cache)
        self.assertIn('b', cache)
        self.assertNotIn('c', cache)
        self.assertIn('d', cache)
        # Updating d should also mark it as used.
        cache['d'] = 'd'
        # Cache content should now be b, a, d
        cache['c'] = 'c'
        # Cache content should now be a, d, c
        self.assertIn('a', cache)
        self.assertNotIn('b', cache)
        self.assertIn('c', cache)
        self.assertIn('d', cache)

    def test_delete(self):
        """
        Test that keys can be deleted explicitly.
        """
        cache = LRUCache(cache_size=3)
        cache['a'] = 'a'
        cache['b'] = 'b'
        cache['c'] = 'c'
        self.assertIn('a', cache)
        self.assertIn('b', cache)
        self.assertIn('c', cache)
        self.assertEqual(3, len(cache))
        del cache['b']
        self.assertIn('a', cache)
        self.assertNotIn('b', cache)
        self.assertIn('c', cache)
        self.assertEqual(2, len(cache))
