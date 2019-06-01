"""
Data source backed by an SQLite database.

The data source provided by this module uses an instance of
`vinegar.utils.sqlite_store.DateStore` for retrieving configuration data. This
makes it most suitable for scenarios, where separate configuration values have
to be managed for each individual systems.

Due to the nature of the backing data store, concurrent updates of configuration
data are safely possible. This data source does not employ any caching
techniques because these techniques would collide with the goal of providing
safe, immediate updates in an environment where multiple processes might access
the database.

The data source provided by this module has a `~SQLiteSource.close()` method
that can be used to close the data store backing the source. In a regular
application, where a data source is created once and then used until the
application is shutdown, this typically is not necessary, so that method is
mainly intended for environments where a new data source instance is created
frequently (e.g. for tests).

Using ``find_system``
---------------------

Due to the lack of a cache, every call to `~SQLiteSource.find_system` or
`~SQLiteSource.get_data` will result in a lookup in the database and
consequently access to the file system. In order to limit the amount of lookups,
the ``find_system`` function can be disabled when it is not needed by setting
``find_system_enabled`` configuration option to ``False`` (see below).

When ``find_system`` is enabled, it will only return a system ID if that system
is a unique match, meaning that this is the only system in the data store that
has the specified value for the specified key. If multiple matching systems are
found, ``None`` is returned.

Specifying a key prefix
-----------------------

When the ``key_prefix`` configuration option is used, ``find_system`` only looks
for matching system when the ``key_prefix`` matches the specified key and
removes the prefix from the specified key before looking it up in the database.

For example, if ``key_prefix`` is set to ``abc:def`` and ``find_system`` is
called for the key ``abc:def:ghi``, the key ``ghi`` is used for the lookup in
the database.

The ``key_prefix`` option is also used by the ``get_data`` option. The actual
data retrieved from the database is wrapped in ``dict`` instances so that the
keys from the database effectively have the specified prefix.

For example, if ``key_prefix`` is set to ``abc:def`` and the data provided by
the database is ``{'123': '456', '789': 'abc'}``, the data returned by
``get_data`` is ``{'abc': {'def': {'123': '456', '789': 'abc'}}}``.

Configuration options
---------------------

This data source has several configuration options that can be used to control
its behavior. Of all these options, only the ``db_file`` option must be
specified. All other options have sensible default values.

:``db_file``:
    Path to the SQLite database file (as a ``str``). This path is passed on to
    the backing `~vinegar.utils.sqlite_store.DataStore`.

:``find_system_enabled``:
    If ``True`` (the default) the `~SQLiteSource.find_system` function is
    enabled. If set to ``False`` it is disabled completely. This makes sense for
    performance reasons if one knows that this data source will not make any
    meaningful contribution to a lookup through ``find_system``.

:``key_prefix``:
    Prefix to be used for data item keys (a ``str``). If this is the empty
    (the default), the keys from the database are used as is, both by
    ``find_system`` and ``get_data``. If it is set to a non-empty strings, the
    data is returned wrapped in a ``dict`` for each component in the
    ``key_prefix`` (the ``:`` character serves as the component separator). This
    can be useful to put the data from the database in a sub-structure of the
    hierarchy forming the data tree, as the backing data store only uses a flat
    key structure.
"""

import json

from typing import Any, Mapping, Tuple

from vinegar.datasource import DataSource
from vinegar.utils.sqlite_store import open_data_store
from vinegar.utils.version import version_for_str

class SQLiteSource(DataSource):
    """
    Data source that reads data from a SQLite database.

    This data source uses a `vinegar.utils.sqlite_store.DataStore` as its
    backend for retrieving data.

    For information about the configuration options supported by this data
    source, please refer to the
    `module documentation <vinegar.datasource.sqlite>`.
    """
    
    def __init__(self, config: Mapping[Any, Any]):
        """
        Create a SQLite data source using the specified configuration.

        :param config:
            configuration for this data source. Please refer to the
            `module documentation <vinegar.datasource.sqlite>` for a list of
            supported options.
        """
        db_file = config['db_file']
        self._data_store = open_data_store(db_file)
        self._find_system_enabled = config.get('find_system_enabled', True)
        self._key_prefix = config.get('key_prefix', '')

    def close(self):
        """
        Closes the data store backing this data source. All operations that
        involve the data store will fail by raising an exception after calling
        this method.

        For most applications, where data sources are long-lived, relying on
        Python's garbage collection is fine for closing the underlying data
        store. However, if an application rapidly creates and discards data
        source instances (e.g. for automated tests), closing the data source
        explicitly can be beneficial because it helps to release resources early
        on.
        """
        self._data_store.close()

    def find_system(self, lookup_key: str, lookup_value: str) -> str:
        if not self._find_system_enabled:
            return None
        if self._key_prefix:
            if lookup_key.startswith(self._key_prefix + ':'):
                lookup_key = lookup_key[(len(self._key_prefix) + 1):]
            else:
                return None
        systems = self._data_store.find_systems(lookup_key, lookup_value)
        if len(systems) == 1:
            return systems[0]
        else:
            return None

    def get_data(
            self,
            system_id: str,
            preceding_data: Mapping[Any, Any],
            preceding_data_version: str) -> Tuple[Mapping[Any, Any], str]:
        data = self._data_store.get_data(system_id)
        if self._key_prefix:
            prefix_components = self._key_prefix.split(':')
            prefix_components.reverse()
            for prefix_component in prefix_components:
                data = {prefix_component: data}
        version = version_for_str(json.dumps(data))
        return data, version

def get_instance(config: Mapping[Any, Any]) -> SQLiteSource:
    """
    Create a SQLite data source.

    For information about the configuration options supported by that source,
    please refer to the `module documentation <vinegar.datasource.sqlite>`.

    :param config:
        configuration for the data source.
    :return:
        sqlite data source using the specified configuration.
    """
    return SQLiteSource(config)
