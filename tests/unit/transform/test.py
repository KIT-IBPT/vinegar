"""
Tests for `vinegar.transform`.
"""

import unittest

from vinegar.transform import apply_transformation, apply_transformation_chain

class TestTransformModule(unittest.TestCase):
    """
    Tests for the `vinegar.transform` module.
    """

    def test_apply_transformation(self):
        """
        Test the `apply_transformation` function.
        """
        self.assertEqual(
            'ABC',
            apply_transformation('string.to_upper', 'aBc'))
        # Test that multiple positional arguments are passed correctly.
        self.assertEqual(
            'aBcdeF',
            apply_transformation('string.add_suffix', 'aBc', 'deF'))
        # Test that mixed of positional and keyword arguments are passed
        # correctly.
        self.assertEqual(
            'aBcdeF',
            apply_transformation('string.add_suffix', 'aBc', suffix='deF'))
        # Test that multiple keyword arugments are passed correctly.
        self.assertEqual(
            'aBcdeF',
            apply_transformation(
                'string.add_suffix', value='aBc', suffix='deF'))

    def test_apply_transformation_chain(self):
        """
        Test the `apply_transformation_chain` function.
        """
        # We test that the various ways of specifying a function and the
        # functiion configuration work.
        chain = [
            'string.to_upper',
            {'string.add_suffix': '.def'}]
        self.assertEqual('ABC.def', apply_transformation_chain(chain, 'abc'))
        chain = [
            {'string.to_upper': []},
            {'string.add_suffix': ['.def']}]
        self.assertEqual('ABC.def', apply_transformation_chain(chain, 'abc'))
        chain = [
            {'string.to_upper': {}},
            {'string.add_suffix': {'suffix': '.def'}}]
        self.assertEqual('ABC.def', apply_transformation_chain(chain, 'abc'))
