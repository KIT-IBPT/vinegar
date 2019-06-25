"""
Tests for `vinegar.utils.sqlite_store`.
"""

import os.path
import unittest

from contextlib import contextmanager
from tempfile import TemporaryDirectory

from vinegar.utils.sqlite_store import DataStore, open_data_store


class TestDataStore(unittest.TestCase):
    """
    Tests for the `DataStore`.
    """

    def test_delete_data(self):
        """
        Test the `~DataStore.delete_data` method.
        """
        with _temporary_data_store() as store:
            system_id1 = 'system1'
            system_id2 = 'system2'
            store.set_value(system_id1, 'a', 123)
            store.set_value(system_id1, 'b', 456)
            store.set_value(system_id2, 'a', 789)
            store.set_value(system_id2, 'b', 1234)
            store.delete_data(system_id1)
            # The data for system_id1 should be gone, but the data for
            # system_id2 should still be present.
            self.assertEqual({}, store.get_data(system_id1))
            self.assertEqual({'a': 789, 'b': 1234}, store.get_data(system_id2))
            # After deleting the data for system_id2, it should also be
            # gone.
            store.delete_data(system_id2)
            self.assertEqual({}, store.get_data(system_id2))

    def test_delete_value(self):
        """
        Test the `~DataStore.delete_value` method.
        """
        with _temporary_data_store() as store:
            system_id1 = 'system1'
            system_id2 = 'system2'
            store.set_value(system_id1, 'a', 123)
            store.set_value(system_id1, 'b', 456)
            store.set_value(system_id2, 'a', 789)
            store.set_value(system_id2, 'b', 1234)
            store.delete_value(system_id1, 'a')
            # system1 should still have the key 'b' and system2 should not be
            # affected:
            self.assertEqual({'b': 456}, store.get_data(system_id1))
            self.assertEqual({'a': 789, 'b': 1234}, store.get_data(system_id2))
            # Now we delete key 'b' for system_id2, and check again.
            store.delete_value(system_id2, 'b')
            self.assertEqual({'b': 456}, store.get_data(system_id1))
            self.assertEqual({'a': 789}, store.get_data(system_id2))

    def test_find_systems(self):
        """
        Test the `~DataStore.find_systems` method.
        """
        with _temporary_data_store() as store:
            system_id1 = 'system1'
            system_id2 = 'system2'
            store.set_value(system_id1, 'a', 123)
            store.set_value(system_id1, 'b', 456)
            store.set_value(system_id1, 'c', 'abc')
            store.set_value(system_id2, 'a', 123)
            store.set_value(system_id2, 'b', 1234)
            # We should not find any system for key 'c', as there is no such key
            # in any of the systems.
            self.assertEqual([], store.find_systems('c', 123))
            # We should not find anything for key 'a' and a value of 456 either,
            # because all systems have a different value for that key.
            self.assertEqual([], store.find_systems('a', 456))
            # Looking for key 'a' and a value of 123 should return both systems.
            self.assertEqual(
                [system_id1, system_id2], store.find_systems('a', 123))
            # Looking for key 'b' and a value of 456 should only return
            # system_id1.
            self.assertEqual(
                [system_id1], store.find_systems('b', 456))
            # Looking for key 'c' and a value of 'abc' should only return
            # system_id1.
            self.assertEqual(
                [system_id1], store.find_systems('c', 'abc'))
            # Looking for key 'b' and a value of 1234 should only return
            # system_id2.
            self.assertEqual(
                [system_id2], store.find_systems('b', 1234))

    def test_get_data(self):
        """
        Test the `~DataStore.get_data` method.
        """
        with _temporary_data_store() as store:
            system_id1 = 'system1'
            system_id2 = 'system2'
            store.set_value(system_id1, 'a', 123)
            store.set_value(system_id1, 'b', 456)
            store.set_value(system_id2, 'a', 789)
            store.set_value(system_id2, 'b', 1234)
            # We check that we get the expected data for both systems. We also
            # check that we get no data for a different system ID.
            self.assertEqual({'a': 123, 'b': 456}, store.get_data(system_id1))
            self.assertEqual({'a': 789, 'b': 1234}, store.get_data(system_id2))
            self.assertEqual({}, store.get_data('system3'))

    def test_get_value(self):
        """
        Test the `~DataStore.get_value` method.
        """
        with _temporary_data_store() as store:
            system_id1 = 'system1'
            system_id2 = 'system2'
            store.set_value(system_id1, 'a', 123)
            store.set_value(system_id1, 'b', '456')
            store.set_value(system_id2, 'a', [789])
            store.set_value(system_id2, 'b', {'abc': 0})
            # We check that we get the expected data for both systems.
            self.assertEqual(123, store.get_value(system_id1, 'a'))
            self.assertEqual('456', store.get_value(system_id1, 'b'))
            self.assertEqual([789], store.get_value(system_id2, 'a'))
            self.assertEqual({'abc': 0}, store.get_value(system_id2, 'b'))
            # We expect a KeyError when using a key that does not exist or a
            # system ID that does not exist.
            with self.assertRaises(KeyError):
                store.get_value(system_id1, 'c')
            with self.assertRaises(KeyError):
                store.get_value('system3', 'a')

    def test_list_systems(self):
        """
        Test the `~DataStore.list_systems` method.
        """
        with _temporary_data_store() as store:
            system_id1 = 'system1'
            system_id2 = 'system2'
            store.set_value(system_id1, 'a', 123)
            store.set_value(system_id1, 'b', 456)
            store.set_value(system_id2, 'a', 789)
            # We check that each system is returned exactly once, regardless of
            # how many keys there are stored for it.
            self.assertEqual([system_id1, system_id2], store.list_systems())

    def test_set_value(self):
        """
        Test the `~DataStore.set_value` method.
        """
        with _temporary_data_store() as store:
            system_id1 = 'system1'
            system_id2 = 'system2'
            # There should not be any data for any systems.
            self.assertEqual([], store.list_systems())
            self.assertEqual({}, store.get_data(system_id1))
            self.assertEqual({}, store.get_data(system_id2))
            # After setting a value, this system should appear.
            store.set_value(system_id1, 'a', 123)
            self.assertEqual([system_id1], store.list_systems())
            self.assertEqual({'a': 123}, store.get_data(system_id1))
            self.assertEqual({}, store.get_data(system_id2))
            # After setting a value for another system, that system should
            # appear, too.
            store.set_value(system_id2, 'a', [789])
            self.assertEqual([system_id1, system_id2], store.list_systems())
            self.assertEqual({'a': 123}, store.get_data(system_id1))
            self.assertEqual({'a': [789]}, store.get_data(system_id2))
            # When we add a value to a system, we should see it in the data
            # for that system
            store.set_value(system_id1, 'b', '456')
            self.assertEqual({'a': 123, 'b': '456'}, store.get_data(system_id1))
            # We should be able to use complex values like dicts, lists, dicts
            # in lists, etc. This also tests that overwriting values works.
            system_id = 'system3'
            key = 'key'
            value = {'abc': [1, 'def', {'a': None}]}
            store.set_value(system_id, key, value)
            self.assertEqual(value, store.get_value(system_id, key))
            value = ['abc', [-3.0, 'def', {'a': None}]]
            store.set_value(system_id, key, value)
            self.assertEqual(value, store.get_value(system_id, key))
            # There are some limitations to what is accepted as a value.
            # For example, a value might not refer to itself recursively.
            value = []
            value.append({'x': value})
            with self.assertRaises(ValueError):
                store.set_value(system_id, key, value)
            value = {}
            value['x'] = [value]
            with self.assertRaises(ValueError):
                store.set_value(system_id, key, value)
            # There are also limitations regarding the allowed types. We only
            # allow values of type bool, int, float, dict (if the keys are of
            # type str and values are one of the supported types), list (if the
            # values are one of the supported types), and str. We also allow the
            # special value None.
            with self.assertRaises(TypeError):
                store.set_value(system_id, key, complex(0, 1))
            with self.assertRaises(TypeError):
                store.set_value(system_id, key, {'abc': {123: 456}})
        # If we disable strict value checking, we should be able to insert
        # dicts that use non-string keys, but they will silently be converted.
        # Other crazy stuff should still fail.
        with _temporary_data_store(strict_value_checking=False) as store:
            system_id = 'system3'
            key = 'key'
            store.set_value(system_id, key, {'abc': {123: 456}})
            self.assertEqual(
                {'abc': {'123': 456}}, store.get_value(system_id, key))
            value = []
            value.append({'x': value})
            with self.assertRaises(ValueError):
                store.set_value(system_id, key, value)
            value = {}
            value['x'] = [value]
            with self.assertRaises(ValueError):
                store.set_value(system_id, key, value)
            with self.assertRaises(TypeError):
                store.set_value(system_id, key, complex(0, 1))


@contextmanager
def _temporary_data_store(*args, **kwargs):
    """
    Creates a data store that stores its database file in a temporary directory.

    The returned object is intended to be used as a context manager, so that the
    temporary directory is deleted when the data is not needed any longer.

    This object also takes care of closing the data store before deleting the
    directory.
    """
    with TemporaryDirectory() as tmpdir:
        with open_data_store(
                os.path.join(tmpdir, 'test.db'), *args, **kwargs) as store:
            yield store
