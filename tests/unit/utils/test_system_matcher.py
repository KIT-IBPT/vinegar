"""
Tests for `vinegar.utils.system_matcher`.
"""

import unittest

from vinegar.utils.system_matcher import match, matcher


class TestMatch(unittest.TestCase):
    """
    Tests for the `match` function.
    """

    def _test_data_expression(self, expression_type):
        # Most tests are the same for the data_glob, data_literal, and data_re
        # expressions, so we define them here.
        # By default, matching is case sensitive.
        self.assertTrue(
            match(
                f"@{expression_type}:mykey@some-value",
                system_data={"mykey": "some-value"},
            )
        )
        self.assertFalse(
            match(
                f"@{expression_type}:mykey@some-value",
                system_data={"mykey": "Some-value"},
            )
        )
        # The matching shall not be case sensitive, if the ignore-case flag is
        # set.
        self.assertTrue(
            match(
                f"@{expression_type}/i:mykey@Some-value",
                system_data={"mykey": "some-Value"},
            )
        )
        self.assertFalse(
            match(
                f"@{expression_type}/i:mykey@Some-value",
                system_data={"mykey": "other-value"},
            )
        )
        # If a key does not exist, this should be treated like if the value was
        # the empty string.
        self.assertTrue(
            match(
                f"@{expression_type}:mykey@''",
                system_data={"other-key": "some-value"},
            )
        )
        self.assertFalse(
            match(
                f"@{expression_type}:mykey@''",
                system_data={"mykey": "some-value"},
            )
        )
        # The same applies if the value for the key is None.
        self.assertTrue(
            match(
                f"@{expression_type}:mykey@''",
                system_data={"mykey": None},
            )
        )
        self.assertFalse(
            match(
                f"@{expression_type}:mykey@''",
                system_data={"mykey": "some-value"},
            )
        )
        # Values that are not strings should be converted to strings for
        # matching.
        self.assertTrue(
            match(
                f"@{expression_type}:mykey@15",
                system_data={"mykey": 15},
            )
        )
        self.assertFalse(
            match(
                f"@{expression_type}:mykey@23",
                system_data={"mykey": 15},
            )
        )
        # Keys can be quoted (and must be quoted if they contain whitespace or
        # other special characters). Both double and single quotes can be used.
        self.assertTrue(
            match(
                f'@{expression_type}:"@ ()\\"\\\\"@value',
                system_data={'@ ()"\\': "value"},
            )
        )
        self.assertTrue(
            match(
                f"@{expression_type}:'@ ()\\'\\\\'@value",
                system_data={"@ ()'\\": "value"},
            )
        )
        # The patten must not be empty if it is not quoted.
        with self.assertRaises(ValueError):
            match(
                f"@{expression_type}:mykey@",
            )
        # The key must not be empty even if it is quoted.
        with self.assertRaises(ValueError):
            match(
                f"@{expression_type}:@value",
            )
        with self.assertRaises(ValueError):
            match(
                f"@{expression_type}/i:@value",
            )
        with self.assertRaises(ValueError):
            match(
                f"@{expression_type}:''@value",
            )
        with self.assertRaises(ValueError):
            match(
                f'@{expression_type}:""@value',
            )
        # An unquoted key must not contain special characters (“@”, “(”, “)”,
        # and whitespace).
        with self.assertRaises(ValueError):
            match(
                f"@{expression_type}:a@b@value",
            )
        with self.assertRaises(ValueError):
            match(
                f"@{expression_type}:a(b@value",
            )
        with self.assertRaises(ValueError):
            match(
                f"@{expression_type}:a)b@value",
            )
        with self.assertRaises(ValueError):
            match(
                f"@{expression_type}:a b@value",
            )

    def _test_id_expression(self, expression_type):
        # Most tests are the same for the id_glob, id_literal, and id_re
        # expressions, so we define them here.
        # By default, matching is case sensitive.
        self.assertTrue(
            match(
                f"@{expression_type}@some-id",
                system_id="some-id",
            )
        )
        self.assertFalse(
            match(
                f"@{expression_type}@some-id",
                system_id="Some-id",
            )
        )
        # The matching shall not be case sensitive, if the ignore-case flag is
        # set.
        self.assertTrue(
            match(
                f"@{expression_type}/i@Some-id",
                system_id="some-Id",
            )
        )
        self.assertFalse(
            match(
                f"@{expression_type}/i@Some-id",
                system_id="other-id",
            )
        )
        # If the system ID is None, this should be treated like the empty
        # string.
        self.assertTrue(match(f"@{expression_type}@''"))
        self.assertFalse(
            match(
                f"@{expression_type}@''",
                system_id="some-id",
            )
        )
        # The patten must not be empty if it is not quoted.
        with self.assertRaises(ValueError):
            match(
                f"@{expression_type}@",
            )

    def test_compound_expression(self):
        """
        Test compound expressions.
        """
        pattern = "*.example.com or *.example.net"
        self.assertTrue(match(pattern, system_id="abc.example.com"))
        self.assertTrue(match(pattern, system_id="123.example.net"))
        self.assertFalse(match(pattern, system_id="def.example.org"))
        pattern = "*.example.com and not abc.*"
        self.assertTrue(match(pattern, system_id="def.example.com"))
        self.assertTrue(match(pattern, system_id="abc123.example.com"))
        self.assertFalse(match(pattern, system_id="abc.example.com"))
        pattern = "(*.example.com or *.example.net) and not abc.*"
        self.assertTrue(match(pattern, system_id="def.example.com"))
        self.assertTrue(match(pattern, system_id="def.example.net"))
        self.assertFalse(match(pattern, system_id="abc.example.com"))
        pattern = (
            "@data_glob:key1@abc* and @data_literal:key2@def or "
            "@data_re:key3@123 and @id_glob@ghi* or @id_literal@jkl or "
            "@id_re@456"
        )
        self.assertTrue(
            match(pattern, system_data={"key1": "abc1", "key2": "def"})
        )
        self.assertTrue(
            match(pattern, system_data={"key1": "abc2", "key2": "def"})
        )
        self.assertFalse(
            match(pattern, system_data={"key1": "bca", "key2": "def"})
        )
        self.assertFalse(
            match(pattern, system_data={"key1": "abc1", "key2": "def1"})
        )
        self.assertTrue(
            match(pattern, system_data={"key3": 123}, system_id="ghi1")
        )
        self.assertTrue(
            match(pattern, system_data={"key3": 123}, system_id="ghi2")
        )
        self.assertFalse(
            match(pattern, system_data={"key3": 456}, system_id="ghi1")
        )
        self.assertFalse(
            match(pattern, system_data={"key3": 123}, system_id="hig")
        )
        self.assertTrue(match(pattern, system_id="jkl"))
        self.assertFalse(match(pattern, system_id="klj"))
        self.assertTrue(match(pattern, system_id="456"))
        self.assertFalse(match(pattern, system_id="789"))

    def test_data_glob_expression(self):
        """
        Test that ``@data_glob`` expressions work as expected.
        """
        # Most of the tests are the same as the ones for the data_literal
        # expressions.
        self._test_data_expression("data_glob")
        # Glob patterns may contain wildcards.
        self.assertTrue(
            match(
                "@data_glob:mykey@some-*",
                system_data={"mykey": "some-value"},
            )
        )
        self.assertTrue(
            match(
                "@data_glob:mykey@*-value",
                system_data={"mykey": "some-value"},
            )
        )
        self.assertFalse(
            match(
                "@data_glob:mykey@*-val",
                system_data={"mykey": "some-value"},
            )
        )
        # Patterns can be quoted (and must be quoted if they contain whitespace
        # or other special characters). Both double and single quotes can be
        # used.
        self.assertTrue(
            match(
                '@data_glob:mykey@"@ ()\\"\\\\"',
                system_data={"mykey": '@ ()"\\'},
            )
        )
        self.assertTrue(
            match(
                "@data_glob:mykey@'@ ()\\'\\\\'",
                system_data={"mykey": "@ ()'\\"},
            )
        )
        # An unquoted pattern must not contain special characters (“@”, “(”,
        # “)”, and whitespace).
        with self.assertRaises(ValueError):
            match(
                "@data_glob:mykey@a@b",
            )
        with self.assertRaises(ValueError):
            match(
                "@data_glob:mykey@a(b",
            )
        with self.assertRaises(ValueError):
            match(
                "@data_glob:mykey@a)b",
            )
        with self.assertRaises(ValueError):
            match(
                "@data_glob:mykey@a b",
            )

    def test_data_literal_expression(self):
        """
        Test that ``@data_literal`` expressions work as expected.
        """
        # Most of the tests are the same as the ones for the data_glob and
        # data_re expressions.
        self._test_data_expression("data_literal")
        # Using literal expressions, we can easily match strings using special
        # characters.
        self.assertTrue(
            match(
                "@data_literal:mykey@{*}[a]",
                system_data={"mykey": "{*}[a]"},
            )
        )
        self.assertFalse(
            match(
                "@data_literal:mykey@{*}[a]",
                system_data={"mykey": "{x}[a]"},
            )
        )
        self.assertTrue(
            match(
                "@data_literal:mykey@' {}()@*'",
                system_data={"mykey": " {}()@*"},
            )
        )
        self.assertFalse(
            match(
                "@data_literal:mykey@' {}()@*'",
                system_data={"mykey": " {}()@*x"},
            )
        )
        # An unquoted comparions string must not contain special characters
        # (“@”, “(”, “)”, and whitespace).
        with self.assertRaises(ValueError):
            match(
                "@data_literal:mykey@a@b",
            )
        with self.assertRaises(ValueError):
            match(
                "@data_literal:mykey@a(b",
            )
        with self.assertRaises(ValueError):
            match(
                "@data_literal:mykey@a)b",
            )
        with self.assertRaises(ValueError):
            match(
                "@data_literal:mykey@a b",
            )

    def test_data_re_expression(self):
        """
        Test that ``@data_re`` expressions work as expected.
        """
        # Most of the tests are the same as the ones for the data_literal
        # expressions.
        self._test_data_expression("data_re")
        # Regular expressions may contain wildcards.
        self.assertTrue(
            match(
                "@data_re:mykey@some-.*",
                system_data={"mykey": "some-value"},
            )
        )
        self.assertTrue(
            match(
                "@data_re:mykey@.*-value",
                system_data={"mykey": "some-value"},
            )
        )
        self.assertFalse(
            match(
                "@data_re:mykey@.*-val",
                system_data={"mykey": "some-value"},
            )
        )
        # Patterns can be quoted (and must be quoted if they contain whitespace
        # or other special characters). Both double and single quotes can be
        # used.
        self.assertTrue(
            match(
                '@data_re:mykey@"@ \\\\(\\\\)\\"\\\\\\\\"',
                system_data={"mykey": '@ ()"\\'},
            )
        )
        self.assertTrue(
            match(
                "@data_re:mykey@'@ \\\\(\\\\)\\'\\\\\\\\'",
                system_data={"mykey": "@ ()'\\"},
            )
        )
        # An unquoted pattern must not contain special characters (“@”, “(”,
        # “)”, and whitespace).
        with self.assertRaises(ValueError):
            match(
                "@data_re:mykey@a@b",
            )
        with self.assertRaises(ValueError):
            match(
                "@data_re:mykey@a\\(b",
            )
        with self.assertRaises(ValueError):
            match(
                "@data_re:mykey@a\\)b",
            )
        with self.assertRaises(ValueError):
            match(
                "@data_re:mykey@a b",
            )

    def test_id_glob_expression(self):
        """
        Test that ``@id_glob`` expressions work as expected.
        """
        # Most of the tests are the same as the ones for the id_literal
        # expressions.
        self._test_id_expression("id_glob")
        # Glob patterns may contain wildcards.
        self.assertTrue(
            match(
                "@id_glob@some-*",
                system_id="some-id",
            )
        )
        self.assertTrue(
            match(
                "@id_glob@*-id",
                system_id="some-id",
            )
        )
        self.assertFalse(
            match(
                "@id_glob@*-i",
                system_id="some-id",
            )
        )
        # Patterns can be quoted (and must be quoted if they contain whitespace
        # or other special characters). Both double and single quotes can be
        # used.
        self.assertTrue(
            match(
                '@id_glob@"@ ()\\"\\\\"',
                system_id='@ ()"\\',
            )
        )
        self.assertTrue(
            match(
                "@id_glob@'@ ()\\'\\\\'",
                system_id="@ ()'\\",
            )
        )
        # An unquoted pattern must not contain special characters (“@”, “(”,
        # “)”, and whitespace).
        with self.assertRaises(ValueError):
            match(
                "@id_glob@a@b",
            )
        with self.assertRaises(ValueError):
            match(
                "@id_glob@a(b",
            )
        with self.assertRaises(ValueError):
            match(
                "@id_glob@a)b",
            )
        with self.assertRaises(ValueError):
            match(
                "@id_glob@a b",
            )

    def test_id_literal_expression(self):
        """
        Test that ``@id_literal`` expressions work as expected.
        """
        # Most of the tests are the same as the ones for the id_glob and id_re
        # expressions.
        self._test_id_expression("id_literal")
        # Using literal expressions, we can easily match strings using special
        # characters.
        self.assertTrue(
            match(
                "@id_literal@{*}[a]",
                system_id="{*}[a]",
            )
        )
        self.assertFalse(
            match(
                "@id_literal@{*}[a]",
                system_id="{x}[a]",
            )
        )
        self.assertTrue(
            match(
                "@id_literal@' {}()@*'",
                system_id=" {}()@*",
            )
        )
        self.assertFalse(
            match(
                "@id_literal@' {}()@*'",
                system_id=" {}()@*x",
            )
        )
        # An unquoted comparions string must not contain special characters
        # (“@”, “(”, “)”, and whitespace).
        with self.assertRaises(ValueError):
            match(
                "@id_literal:mykey@a@b",
            )
        with self.assertRaises(ValueError):
            match(
                "@id_literal:mykey@a(b",
            )
        with self.assertRaises(ValueError):
            match(
                "@id_literal:mykey@a)b",
            )
        with self.assertRaises(ValueError):
            match(
                "@id_literal:mykey@a b",
            )

    def test_id_re_expression(self):
        """
        Test that ``@id_re`` expressions work as expected.
        """
        # Most of the tests are the same as the ones for the id_literal
        # expressions.
        self._test_id_expression("id_re")
        # Regular expressions may contain wildcards.
        self.assertTrue(
            match(
                "@id_re@some-.*",
                system_id="some-id",
            )
        )
        self.assertTrue(
            match(
                "@id_re@.*-id",
                system_id="some-id",
            )
        )
        self.assertFalse(
            match(
                "@id_re@.*-i",
                system_id="some-id",
            )
        )
        # Patterns can be quoted (and must be quoted if they contain whitespace
        # or other special characters). Both double and single quotes can be
        # used.
        self.assertTrue(
            match(
                '@id_re@"@ \\\\(\\\\)\\"\\\\\\\\"',
                system_id='@ ()"\\',
            )
        )
        self.assertTrue(
            match(
                "@id_re@'@ \\\\(\\\\)\\'\\\\\\\\'",
                system_id="@ ()'\\",
            )
        )
        # An unquoted pattern must not contain special characters (“@”, “(”,
        # “)”, and whitespace).
        with self.assertRaises(ValueError):
            match(
                "@id_re@a@b",
            )
        with self.assertRaises(ValueError):
            match(
                "@id_re@a\\(b",
            )
        with self.assertRaises(ValueError):
            match(
                "@id_re@a\\)b",
            )
        with self.assertRaises(ValueError):
            match(
                "@id_re@a b",
            )

    def test_invalid_syntax(self):
        """
        Test that providing an invalid expression results in an exception.
        """
        with self.assertRaises(ValueError):
            match("")
        with self.assertRaises(ValueError):
            match("some-* or and abc")
        with self.assertRaises(ValueError):
            match("and some-*")
        with self.assertRaises(ValueError):
            match("some-* or")
        with self.assertRaises(ValueError):
            match("some-* or (abc")
        with self.assertRaises(ValueError):
            match("some-* or abc)")
        with self.assertRaises(ValueError):
            match("abc def)")
        with self.assertRaises(ValueError):
            match("'abc'or def")
        with self.assertRaises(ValueError):
            match('abc and"def"')
        with self.assertRaises(ValueError):
            match('a@b"')
        with self.assertRaises(ValueError):
            match('@id_literal:"a"or b')
        with self.assertRaises(ValueError):
            match("a or @data_glob:@val")
        with self.assertRaises(ValueError):
            match("@no_such_expression_type@value")
        with self.assertRaises(ValueError):
            match("and")
        with self.assertRaises(ValueError):
            match("not")
        with self.assertRaises(ValueError):
            match("or")

    def test_operator_precedence(self):
        """
        Test that the ``not`` operator takes precedence over the ``and``
        operator and the ``and`` operator takes precedence over the ``or``
        operator. Also test that that parentheses can be used to override
        precedence rules.
        """
        self.assertTrue(match("abc and abc or def", system_id="def"))
        self.assertTrue(match("(abc and abc) or def", system_id="def"))
        self.assertFalse(match("abc and (abc or def)", system_id="def"))
        self.assertTrue(match("abc or def and def", system_id="abc"))
        self.assertTrue(match("abc or (def and def)", system_id="abc"))
        self.assertFalse(match("(abc or def) and def", system_id="abc"))

    def test_unqualified_pattern(self):
        """
        Test pattern expressions that do not explicitly specify a type.

        These expressions are equivalent to ``@id_glob/i@…`` expressions.
        """
        # Test some wildcard expressions.
        pattern = "*.example.com"
        self.assertTrue(match(pattern, system_id="abc.example.com"))
        self.assertTrue(match(pattern, system_id="123.456.example.com"))
        self.assertFalse(match(pattern, system_id="abc.example.net"))
        pattern = "[0-9]*.example.com"
        self.assertTrue(match(pattern, system_id="1.example.com"))
        self.assertTrue(match(pattern, system_id="456abc.example.com"))
        self.assertFalse(match(pattern, system_id="abc.example.com"))
        self.assertFalse(match(pattern, system_id=".example.com"))
        pattern = "[0-9]?*.example.com"
        self.assertTrue(match(pattern, system_id="1a.example.com"))
        self.assertTrue(match(pattern, system_id="456abc.example.com"))
        self.assertFalse(match(pattern, system_id="abc.example.com"))
        self.assertFalse(match(pattern, system_id="1.example.com"))
        # The patterns are not case-sensitive.
        self.assertTrue(match("aBc", system_id="abc"))
        self.assertTrue(match("aBc", system_id="abc"))
        # Patterns can be quoted (and must be quoted, if they contain special
        # characters like “@”, “(”, “)”, or whitespace or if they are the same
        # as the keywords “and”, “not”, and “or”.
        pattern = "\"*.example.com\" or '*.example.net'"
        self.assertTrue(match(pattern, system_id="abc.example.com"))
        self.assertTrue(match(pattern, system_id="123.example.net"))
        self.assertFalse(match(pattern, system_id="def.example.org"))
        self.assertTrue(match('"and"', system_id="and"))
        self.assertTrue(match("'and'", system_id="and"))
        self.assertTrue(match('"not"', system_id="not"))
        self.assertTrue(match("'not'", system_id="not"))
        self.assertTrue(match('"or"', system_id="or"))
        self.assertTrue(match("'or'", system_id="or"))


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
        self.assertTrue(m.matches(system_id="aBc"))
        self.assertFalse(m.matches(system_id="def"))
        self.assertTrue(m.matches(system_id="abc"))
        m = matcher("@id_glob/i@abc")
        self.assertTrue(m.matches(system_id="aBc"))
        self.assertFalse(m.matches(system_id="def"))
        self.assertTrue(m.matches(system_id="abc"))
        m = matcher("@id_glob@abc")
        self.assertTrue(m.matches(system_id="abc"))
        self.assertFalse(m.matches(system_id="Abc"))
        m = matcher("@id_glob@aBc")
        self.assertTrue(m.matches(system_id="aBc"))
        self.assertFalse(m.matches(system_id="Abc"))
        self.assertFalse(m.matches(system_id="abc"))
