"""
Tests for `vinegar.utils.system_matcher`.
"""

import unittest

from vinegar.utils.system_matcher import match, matcher


class TestMatch(unittest.TestCase):
    """
    Tests for the `match` function.
    """

    def test_case_sensitive(self):
        """
        Test that the ``case_sensitive`` option has the expected results.
        """
        self.assertTrue(match("aBc", "abc"))
        self.assertTrue(match("aBc", "abc", False))
        self.assertFalse(match("aBc", "abc", True))
        self.assertTrue(match("aBc", "aBc", True))

    def test_invalid_syntax(self):
        """
        Test that providing an invalid expression results in an exception.
        """
        with self.assertRaises(ValueError):
            match("some-name", "")
        with self.assertRaises(ValueError):
            match("some-name", "some-* or and abc")
        with self.assertRaises(ValueError):
            match("some-name", "and some-*")
        with self.assertRaises(ValueError):
            match("some-name", "some-* or")
        with self.assertRaises(ValueError):
            match("some-name", "some-* or (abc")
        with self.assertRaises(ValueError):
            match("some-name", "some-* or abc)")

    def test_operator_precedence(self):
        """
        Test that the ``not`` operator takes precedence over the ``and``
        operator and the ``and`` operator takes precedence over the ``or``
        operator. Also test that that parentheses can be used to override
        precedence rules.
        """
        self.assertTrue(match("def", "abc and abc or def"))
        self.assertTrue(match("def", "(abc and abc) or def"))
        self.assertFalse(match("def", "abc and (abc or def)"))
        self.assertTrue(match("abc", "abc or def and def"))
        self.assertTrue(match("abc", "abc or (def and def)"))
        self.assertFalse(match("abc", "(abc or def) and def"))

    def test_wildcards(self):
        """
        Test wildcard expressions.
        """
        pattern = "*.example.com"
        self.assertTrue(match("abc.example.com", pattern))
        self.assertTrue(match("123.456.example.com", pattern))
        self.assertFalse(match("abc.example.net", pattern))
        pattern = "*.example.com or *.example.net"
        self.assertTrue(match("abc.example.com", pattern))
        self.assertTrue(match("123.example.net", pattern))
        self.assertFalse(match("def.example.org", pattern))
        pattern = "*.example.com and not abc.*"
        self.assertTrue(match("def.example.com", pattern))
        self.assertTrue(match("abc123.example.com", pattern))
        self.assertFalse(match("abc.example.com", pattern))
        pattern = "(*.example.com or *.example.net) and not abc.*"
        self.assertTrue(match("def.example.com", pattern))
        self.assertTrue(match("def.example.net", pattern))
        self.assertFalse(match("abc.example.com", pattern))
        pattern = "[0-9]*.example.com"
        self.assertTrue(match("1.example.com", pattern))
        self.assertTrue(match("456abc.example.com", pattern))
        self.assertFalse(match("abc.example.com", pattern))
        self.assertFalse(match(".example.com", pattern))
        pattern = "[0-9]?*.example.com"
        self.assertTrue(match("1a.example.com", pattern))
        self.assertTrue(match("456abc.example.com", pattern))
        self.assertFalse(match("abc.example.com", pattern))
        self.assertFalse(match("1.example.com", pattern))


class TestMatcher(unittest.TestCase):
    """
    Tests for the `matcher` function.
    """

    def test_basic_usage(self):
        """
        Test basic functions like creating a matcher. All the low-level details
        are identical to the `match` function, so that we do not have to test
        them. We also test case-sensitivity because in theory, this information
        could get lost if the paremeter is not passed on.
        """
        m = matcher("abc")
        self.assertTrue(m.matches("aBc"))
        self.assertFalse(m.matches("def"))
        self.assertTrue(m.matches("abc"))
        m = matcher("abc", False)
        self.assertTrue(m.matches("aBc"))
        self.assertFalse(m.matches("def"))
        self.assertTrue(m.matches("abc"))
        m = matcher("abc", True)
        self.assertTrue(m.matches("abc"))
        self.assertFalse(m.matches("Abc"))
        self.assertTrue(m.matches("abc"))
        m = matcher("aBc", True)
        self.assertTrue(m.matches("aBc"))
        self.assertFalse(m.matches("Abc"))
        self.assertFalse(m.matches("abc"))
        self.assertTrue(m.matches("aBc"))
