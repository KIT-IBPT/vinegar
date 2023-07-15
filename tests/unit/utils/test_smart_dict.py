"""
Tests for `vinegar.utils.smart_dict`.
"""

import unittest

from vinegar.utils.smart_dict import SmartLookupDict


class TestSmartLookupDict(unittest.TestCase):
    """
    Tests for the `SmartLookupDict` class.
    """

    def test_get(self):
        """
        Test the ``get`` method.
        """
        d = SmartLookupDict()
        # get raises a KeyError if a key cannot be found and no default value
        # is given. If a default value is given, that value is returned
        # instead.
        test_value = object()
        test_value2 = object()
        with self.assertRaises(KeyError):
            d.get("key")
        self.assertEqual(test_value, d.get("key", test_value))
        # This also applies when the key is nested.
        with self.assertRaises(KeyError):
            d.get("key:test")
        self.assertEqual(test_value, d.get("key:test", test_value))
        # And it also applies when the key is not found inside the nested dict.
        d["key"] = {}
        with self.assertRaises(KeyError):
            d.get("key:test")
        self.assertEqual(test_value, d.get("key:test", test_value))
        # If the key exists, it should be returned, regardless of whether we
        # give a default value or not.
        d["key"]["test"] = test_value2
        self.assertEqual(test_value2, d.get("key:test"))
        self.assertEqual(test_value2, d.get("key:test"), test_value)
        # A default value can also be given in the form of a keyword argument.
        self.assertEqual(
            test_value, d.get("key2:test:test2", default=test_value)
        )
        # But it cannot be given both as a positional and a keyword argument.
        with self.assertRaises(TypeError):
            d.get("key", test_value, default=test_value)
        # We can choose a different separator.
        self.assertEqual(test_value2, d.get("key_test", test_value, "_"))
        self.assertEqual(test_value, d.get("key_test2", test_value, "_"))
        # That can also be specified as a keyword argument.
        self.assertEqual(test_value2, d.get("key_test", sep="_"))
        # And it can be mixed with the default argument.
        self.assertEqual(test_value2, d.get("key_test", test_value, sep="_"))
        self.assertEqual(test_value, d.get("key_test2", test_value, sep="_"))
        self.assertEqual(
            test_value2, d.get("key_test", default=test_value, sep="_")
        )
        self.assertEqual(
            test_value, d.get("key_test2", default=test_value, sep="_")
        )
        # But it cannot be specified as both a positional and a keyword
        # argument.
        with self.assertRaises(TypeError):
            d.get("key_test", test_value, "_", sep="_")
        # The get method still works for a key that does not contain a
        # separator.
        d["abc"] = 123
        self.assertEqual(123, d.get("abc"))
        # Even if the key contains the default separator.
        d["abc:def"] = 456
        self.assertEqual(456, d.get("abc:def", sep="_"))
        self.assertEqual(456, d.get("abc:def", sep=None))
        # We should not be able to look into a non-mapping object using a
        # nested key, not even if a default value is specified.
        with self.assertRaises(TypeError):
            d.get("abc:def")
        with self.assertRaises(TypeError):
            d.get("abc:def", test_value)
        # The method does not take more than three positional arguments.
        with self.assertRaises(TypeError):
            d.get("key_test", test_value, "_", "dummy")
        # And it does not accept unknown keyword arguments.
        with self.assertRaises(TypeError):
            d.get("key_test", dummy="dummy")

    def test_get_numeric_keys(self):
        """
        Test the ``get`` method with numeric keys.

        This tests that nested lists are handled correctly in addition to
        nested dicts.
        """
        d = SmartLookupDict(
            {
                "key1": [
                    "a",
                    "b",
                    {
                        "123": "abc",
                        "456": "def",
                    },
                ],
                "key2": 123,
            }
        )
        self.assertEqual("a", d.get("key1:0"))
        self.assertEqual("b", d.get("key1:1"))
        self.assertEqual("abc", d.get("key1:2:123"))
        self.assertEqual("def", d.get("key1:2:456"))
        # An invalid index into a sequence should result in a key error.
        with self.assertRaises(KeyError):
            d.get("key:3")
        # We should not be able to access an item of a string-like object.
        d = SmartLookupDict(
            {
                "key": [
                    "abc",
                    b"def",
                    bytearray(b"ghi"),
                ],
            }
        )
        self.assertEqual("abc", d.get("key:0"))
        self.assertEqual(b"def", d.get("key:1"))
        self.assertEqual(b"ghi", d.get("key:2"))
        with self.assertRaises(TypeError):
            d.get("key:0:0")
        with self.assertRaises(TypeError):
            d.get("key:1:0")
        with self.assertRaises(TypeError):
            d.get("key:2:0")

    def test_setdefault(self):
        """
        Test the ``setdefault`` method.
        """
        d = SmartLookupDict()
        test_value = object()
        test_value2 = object()
        # setdefault should insert a value if the key does not exist yet.
        self.assertEqual(test_value, d.setdefault("abc", test_value))
        self.assertEqual(test_value, d["abc"])
        # But it should not overwrite existing values.
        self.assertEqual(test_value, d.setdefault("abc", test_value2))
        self.assertEqual(test_value, d["abc"])
        # If we specify a nested key, nested dicts should be created as
        # necessary.
        self.assertEqual(test_value, d.setdefault("def:ghi:123", test_value))
        self.assertEqual(test_value, d["def"]["ghi"]["123"])
        # If nested dicts already exist, they should be reused.
        self.assertEqual(test_value, d.setdefault("def:456", test_value))
        self.assertEqual(
            {"ghi": {"123": test_value}, "456": test_value}, d["def"]
        )
        # But this should not work if one of the key components refers to a
        # value that is not a dict.
        with self.assertRaises(TypeError):
            d.setdefault("abc:def", test_value)
        # We should be able to use a different separator.
        self.assertEqual(
            test_value, d.setdefault("def_ghi_123", test_value2, sep="_")
        )
        self.assertEqual(
            test_value2, d.setdefault("def_ghi_456", test_value2, sep="_")
        )
        self.assertEqual(test_value2, d["def"]["ghi"]["456"])

    def test_setdefault_numeric(self):
        """
        Test the ``setdefault`` method with numeric keys.

        This tests that nested lists are handled correctly in addition to
        nested dicts.
        """
        d = SmartLookupDict(
            {
                "key1": [
                    "a",
                    "b",
                    {
                        "123": "abc",
                        "456": "def",
                    },
                ],
                "key2": 123,
            }
        )
        test_value = object()
        # setdefault should be able to traverse lists.
        self.assertEqual("abc", d.setdefault("key1:2:123", test_value))
        self.assertEqual("abc", d["key1"][2]["123"])
        self.assertEqual(test_value, d.setdefault("key1:2:789", test_value))
        self.assertEqual(test_value, d["key1"][2]["789"])
        # But it cannot insert a new item into a list.
        with self.assertRaises(TypeError):
            d.setdefault("key1:3", "test1")
        with self.assertRaises(TypeError):
            d.setdefault("key1:3:nested_key", "test2")
