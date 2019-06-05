"""
Tests for `vinegar.datasource`.
"""

import unittest
import unittest.mock

from typing import Any, Mapping, Tuple

from vinegar.datasource import (
    DataSource,
    DataSourceAware,
    get_composite_data_source,
    inject_data_source,
    merge_data_trees)

class TestDataSourceModule(unittest.TestCase):
    """
    Tests for the `vinegar.datasorce` module.
    """

    def test_get_composite_data_source(self):
        """
        Test the `get_composite_data_source` function.
        """
        data1 = {'a': 1, 'b': 2}
        data2 = {'a': 3, 'c': 4}
        system_id1 = 'system1'
        system_id2 = 'system2'
        sources = [
            _DummyDataSource(data1, system_id1),
            _DummyDataSource(data2, system_id2),
            _DummyDataSource(data2, system_id1),
            _DummyDataSource(data1, system_id2)]
        composite = get_composite_data_source(sources)
        # We test for system1 with different inputs.
        result_data1, result_version1 = composite.get_data(system_id1, {}, '0')
        self.assertEqual({'a': 3, 'b': 2, 'c': 4}, result_data1)
        result_data2, result_version2 = composite.get_data(
            system_id1, {'d': 5}, '1')
        self.assertEqual({'d': 5, 'a': 3, 'b': 2, 'c': 4}, result_data2)
        self.assertNotEqual(result_version1, result_version2)
        # We also test for system2 with different inputs.
        result_data1, result_version1 = composite.get_data(system_id2, {}, '0')
        self.assertEqual({'a': 1, 'c': 4, 'b': 2}, result_data1)
        result_data2, result_version2 = composite.get_data(
            system_id2, {'e': 6}, '1')
        self.assertEqual({'e': 6, 'a': 1, 'c': 4, 'b': 2}, result_data2)
        self.assertNotEqual(result_version1, result_version2)
        # Finally, we test find_system.
        # We find system1 for a == 1 because the respective data source comes
        # earliest in the chain.
        self.assertEqual(system_id1, composite.find_system('a', 1))
        # For a == 3, we find system2 for the same reason
        self.assertEqual(system_id2, composite.find_system('a', 3))
        # For a == 2, we do not find any system at all.
        self.assertIsNone(composite.find_system('a', 2))

    def test_inject_data_source(self):
        """
        Test the `inject_data_source` function.
        """
        # We need a mock data source that we can inject.
        data_source = unittest.mock.Mock(spec=DataSource)
        # First, we create an object that is not data-source aware. The
        # set_data_source method should not be called on this object.
        obj1 = unittest.mock.Mock()
        inject_data_source(obj1, data_source)
        obj1.set_data_source.assert_not_called()
        # Second we create an object that is data-source aware. The
        # set_data_source method should be called on this object, providing the
        # mock data source.
        obj2 = unittest.mock.Mock(spec=DataSourceAware)
        inject_data_source(obj2, data_source)
        obj2.set_data_source.assert_called_with(data_source)

    def test_merge_data_trees(self):
        """
        Test the `merge_data_trees` function.
        """
        # First we test a very simple merge. We primarily check that the key
        # order is preserved.
        d1 = {1: 1, 2: 2, 4: 4}
        d2 = {1: 5, 3: 6, 5: 7}
        expected_result = {1: 5, 2: 2, 4: 4, 3: 6, 5: 7}
        result = merge_data_trees(d1, d2)
        self.assertEqual(expected_result, result)
        self.assertEqual([1, 2, 4, 3, 5], list(result.keys()))
        # Next, we test that dictionary values are merged as well.
        self.assertEqual(
            {0: expected_result}, merge_data_trees({0: d1}, {0: d2}))
        # Now, we test that lists are not merged unless merge_lists is set to
        # True.
        d1 = {0: [1, 3, 4]}
        d2 = {0: [2, 4, 5]}
        expected_result = {0: [2, 4, 5]}
        result = merge_data_trees(d1, d2)
        self.assertEqual(expected_result, result)
        expected_result = {0: [1, 3, 4, 2, 5]}
        result = merge_data_trees(d1, d2, merge_lists=True)
        self.assertEqual(expected_result, result)

class _DummyDataSource(DataSource):
    """
    Dummy data source used in tests.

    This data source simply provides the data that is provided to it when it is
    created. If a system ID is specified, it only returns data for that system
    ID and it supports the `find_system_id` method.
    """

    def __init__(self, data, system_id=None):
        self._data = data
        self._system_id = system_id

    def find_system(self, lookup_key: str, lookup_value: Any) -> str:
        try:
            if self._data[lookup_key] == lookup_value:
                return self._system_id
            else:
                return None
        except KeyError:
            return None

    def get_data(
            self,
            system_id: str,
            preceding_data: Mapping[Any, Any],
            preceding_data_version: str) -> Tuple[Mapping[Any, Any], str]:
        # We can use an empty string for the version number because we know that
        # we always return the same data.
        if self._system_id is None or self._system_id == system_id:
            return self._data, ''
        else:
            return {}, ''
