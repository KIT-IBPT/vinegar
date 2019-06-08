"""
Tests for `vinegar.data_source.sqlite`.
"""

import os.path
import unittest

import vinegar.data_source

from contextlib import contextmanager
from tempfile import TemporaryDirectory

from vinegar.data_source.sqlite import SQLiteSource

class TestSQLiteSource(unittest.TestCase):
    """
    Tests for the `SQLiteSource`.
    """

    def test_config_find_system_enabled(self):
        """
        Test the ``find_system_enabled`` configuration option.

        As it is enabled by default and this is already tested by
        `test_find_system`, we only test that disabling it has the expected
        effects.
        """
        config = {'find_system_enabled': False}
        with _temporary_data_source_and_store(config) as (ds, store):
            # First we fill the store with some data.
            system_id = 'system1'
            store.set_value(system_id, 'abc', 123)
            store.set_value(system_id, 'def', 'foo')
            # Now we can check that the data source does not find any systems,
            # even if we query using the correct data.
            self.assertIsNone(ds.find_system('abc', 123))
            self.assertIsNone(ds.find_system('def', 'foo'))

    def test_config_key_prefix(self):
        """
        Test the ``key_prefix`` configuration option.

        This tests for setting this option to a non-empty value, because an
        empty value is the default that is covered by other tests.
        """
        config = {'key_prefix': 'p1:p2'}
        with _temporary_data_source_and_store(config) as (ds, store):
            # First we fill the store with some data.
            system_id = 'system1'
            store.set_value(system_id, 'abc', 123)
            store.set_value(system_id, 'def', 'foo')
            # We expect the data source to return the data wrapped in dicts.
            expected_data = {'p1': {'p2': {'abc': 123, 'def': 'foo'}}}
            data, _ = ds.get_data(system_id, {}, '')
            self.assertEqual(expected_data, data)
            # We also expect that we have to specify the correct prefix when
            # trying to find a system.
            self.assertIsNone(ds.find_system('abc', 123))
            self.assertIsNone(ds.find_system('def', 'foo'))
            self.assertEqual(system_id, ds.find_system('p1:p2:abc', 123))
            self.assertEqual(system_id, ds.find_system('p1:p2:def', 'foo'))

    def test_find_system(self):
        """
        Test the `~SQLiteSource.find_system` method.
        """
        config = {}
        with _temporary_data_source_and_store(config) as (ds, store):
            # First we fill the store with some data.
            system_id1 = 'system1'
            system_id2 = 'system2'
            store.set_value(system_id1, 'abc', 123)
            store.set_value(system_id1, 'def', 'foo')
            store.set_value(system_id1, 'key', 'val')
            store.set_value(system_id2, 'abc', 456)
            store.set_value(system_id2, 'key', 'val')
            # Now we can check that the data source find the systems as
            # expected.
            self.assertIsNone(ds.find_system('abc', 789))
            self.assertIsNone(ds.find_system('def', 'bar'))
            self.assertEqual(system_id1, ds.find_system('abc', 123))
            self.assertEqual(system_id1, ds.find_system('def', 'foo'))
            self.assertEqual(system_id2, ds.find_system('abc', 456))
            self.assertIsNone(ds.find_system('key', 'val'))

    def test_get_data(self):
        """
        Test the `~SQLiteSource.get_data method.
        
        This mainly tests that data from the database is returned as expected.
        """
        config = {}
        with _temporary_data_source_and_store(config) as (ds, store):
            # First we fill the store with some data.
            system_id1 = 'system1'
            system_id2 = 'system2'
            system_id3 = 'system3'
            store.set_value(system_id1, 'abc', 123)
            store.set_value(system_id1, 'def', 'foo')
            store.set_value(system_id2, 'abc', 456)
            # Now we can check that the data source returns the expected data.
            self.assertEqual(
                {'abc': 123, 'def': 'foo'}, ds.get_data(system_id1, {}, '')[0])
            self.assertEqual({'abc': 456}, ds.get_data(system_id2, {}, '')[0])
            self.assertEqual({}, ds.get_data(system_id3, {}, '')[0])
            # We also check that the version string changes when the data
            # changes.
            _, version1 = ds.get_data(system_id2, {}, '')
            store.set_value(system_id2, 'abc', 789)
            data, version2 = ds.get_data(system_id2, {}, '')
            self.assertEqual({'abc': 789}, data)
            self.assertNotEqual(version1, version2)

@contextmanager
def _temporary_data_source_and_store(config):
    """
    Creates a data source and data store that store their database file in a
    temporary directory.

    The returned object is intended to be used as a context manager, so that the
    temporary directory is deleted when the data is not needed any longer.

    This object also takes care of closing the data source and data store before
    deleting the directory.
    """
    with TemporaryDirectory() as tmpdir:
        db_file = os.path.join(tmpdir, 'test.db')
        real_config = {'db_file': db_file}
        real_config.update(config)
        with vinegar.utils.sqlite_store.open_data_store(db_file) as store:
            source = SQLiteSource(real_config)
            try:
                yield source, store
            finally:
                source.close()
