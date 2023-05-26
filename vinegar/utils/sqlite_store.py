"""
Data store used by the `~vinegar.data_source.sqlite` data source.

This data store uses the ``sqlite3`` package for accessing a database file that
stores information associated with systems.

The data store provided by this module is primarily intended to serve as the
backend of the `~vinegar.data_source.sqlite` data source. This means that the
storage structure used by this data store has been designed with that use in
mind and is probably not very useful for other applications.

However, it is still provided by a separate package because other modules might
find it useful to be able to access and modify the database used by a data
source.

The data store is implemented in a way, so that it is safe to access the same
database concurrently from multiple threads or even processes. This means that
many `DataStore` instances may be created for the same database file and that a
single `DataStore` instance may be shared by different threads.

A `DataStore` instance is created by calling `open_data_store`.
"""

import json
import sqlite3
import threading

from typing import Any, Mapping, Sequence


class DataStore:
    """
    Data store that is backed by an SQLite database.

    When a program is done with using an instance of this class, it should call
    its `close` method. Alternatively, an instance of this class can be used as
    a context manager like in the following example::

        with open_data_store(db_file) as data_store:
            data_store.set_value('system_id', 'key', 'value')
            print(data_store.get_data('system_id'))

    Instances of this class are safe for use by multiple threads.
    """

    def __init__(self, db_file: str, strict_value_checking=True):
        """
        Create a data store that is backed by the specified database file.
        If the database file does not exist yet, create it.

        The `strict_value_checking` option controls the behavior of the
        `set_value` method. If the option is set to ``True`` (the default),
        `set_value` raises an exception if the specified value cannot be
        safely serialized as JSON (see that method for details about which
        types can be serialized safely).

        A data store that has been created should be closed when it is not
        needed any longer by calling its `close` method. This ensures that
        resources associated with the database connection are released
        immediately instead of when the data store object is eventually garbage
        collected.

        :param db_file:
            path to the database file that stores the catual data.
        :param strict_value_checking:
            ``True`` if inserted values shall be checked strictly, ``False`` if
            the checks shall be more relaxed. See `set_value` for details.
        """
        # There is no way to find out whether the SQLite library has been
        # compiled with thread support as Python does not expose the
        # sqlite3_threadsafe() API and does not allow passing the
        # SQLITE_OPEN_FULLMUTEX flag to sqlite3_open_v2() or sqlite3_config()
        # either, so we have to assume that SQLite is not thread safe, even
        # though on most systems it probably is. This means that we protect
        # access to the connection with our own mutex.
        self._strict_value_checking = strict_value_checking
        self._connection = sqlite3.connect(
            db_file, isolation_level=None, check_same_thread=False
        )
        self._lock = threading.Lock()
        self._create_tables()

    def close(self) -> None:
        """
        Close this data store. This closes the underlying database connection.

        A data store should be closed when it is not going to be used any
        longer.

        Using the data store after closing it will result in an exception being
        raised.
        """
        with self._lock:
            self._connection.close()

    def delete_data(self, system_id: str) -> None:
        """
        Delete all data associated with a system ID.

        :param system_id:
            system_id for which all data (all keys) shall be deleted.
        """
        with self._lock:
            self._connection.execute(
                "DELETE FROM system_data WHERE system_id=?;", (system_id,)
            )

    def delete_value(self, system_id: str, key: str) -> None:
        """
        Delete data associated with a system ID and a specific key.

        :param system_id:
            system_id for which the piece of data identified by ``key`` shall
            be deleted.
        :param key:
            key which shall be deleted. Data stored under different keys is not
            affected by this operation.
        """
        with self._lock:
            self._connection.execute(
                "DELETE FROM system_data WHERE system_id=? and key=?;",
                (system_id, key),
            )

    def find_systems(self, key: str, value: Any) -> Sequence:
        """
        Find system IDs associated with a certain key value pair.

        This returns those system IDs for which the specified ``key`` has the
        specified ``value``.

        :param key:
            key that shall be tested.
        :param value:
            data that is expected for the specified key. A system is only
            included in the returned list if the data stored for it under the
            specified key matches this value.
        :return:
            list of system IDs that match the predicate.
        """
        with self._lock:
            cursor = self._connection.execute(
                "SELECT system_id FROM system_data WHERE key=? AND value=? "
                "ORDER BY system_id;",
                (key, json.dumps(value)),
            )
            try:
                cursor.arraysize = 16
                rows = cursor.fetchall()
            finally:
                cursor.close()
        systems = [row[0] for row in rows]
        return systems

    def get_data(self, system_id: str) -> Mapping[str, Any]:
        """
        Return all data associated with a specific system ID.

        The data is returned as a ``dict`` where each key is one of the keys
        that has been stored for the system and each value is the value stored
        for that key.

        If there is no data for the specified system ID, an empty ``dict`` is
        returned.

        :param system_id:
            system ID of the system for which the data shall be retrieved.
        :return:
            dictionary containing all data for the specified system ID.
        """
        with self._lock:
            cursor = self._connection.execute(
                "SELECT key, value FROM system_data WHERE system_id=? ORDER "
                "BY key;",
                (system_id,),
            )
            try:
                cursor.arraysize = 16
                rows = cursor.fetchall()
            finally:
                cursor.close()
        data = {row[0]: json.loads(row[1]) for row in rows}
        return data

    def get_value(self, system_id: str, key: str) -> Any:
        """
        Return the value associated with a specific system ID and key.

        If the specified key does not exist for the specified system ID, a
        ``KeyError`` is raised.

        :param system_id:
            system_id for which the piece of data identified by ``key`` shall
            be retrieved.
        :param key:
            key for which the value shall be retrieved.
        :return:
            value associated with the specified system ID and key.
        """
        with self._lock:
            cursor = self._connection.execute(
                "SELECT value FROM system_data WHERE system_id=? AND "
                "KEY=?;",
                (system_id, key),
            )
            try:
                row = cursor.fetchone()
            finally:
                cursor.close()
        if row is None:
            raise KeyError(key)
        return json.loads(row[0])

    def list_systems(self) -> Sequence[str]:
        """
        Return a list of all system IDs.

        The returned list contains every system ID for which at least one piece
        of data is stored.

        :return:
            list of system IDs that are known by this data store.
        """
        with self._lock:
            cursor = self._connection.execute(
                "SELECT DISTINCT system_id FROM system_data "
                "ORDER BY system_id;"
            )
            try:
                cursor.arraysize = 16
                rows = cursor.fetchall()
            finally:
                cursor.close()
        systems = [row[0] for row in rows]
        return systems

    def set_value(self, system_id: str, key: str, value: Any) -> None:
        """
        Store a value for the specified system ID and key.

        The data store internally uses JSON to serialize the value, so there
        are some restrictions on which kind of values are supported.

        In general, only objects that can be serialized by ``json.dumps`` are
        supported. In particular, passing an object that has a circular
        reference (e.g. a ``dict`` that refers back to itself through one of
        its values) results in a ``ValueError`` being raised. Passing another
        kind of object that cannot be serialized by ``json.dumps`` results in a
        ``TypeError`` being raised.

        If the ``strict_value_checking`` option is enabled for this data store
        (see `open_data_store`) some additional checks apply. JSON natively
        only supports the elementary data types ``bool``, ``float``, ``int``
        and ``str`` as well as ``list`` and ``dict`` instances using these
        types. The values stored in a ``list`` or a ``dict`` must also be of
        one of these types. The keys of a ``dict`` are further constrained:
        They must be instances of ``str``. In additon to the aforementioned
        types, the special value ``None`` is also supported (but not as a
        ``dict`` key).

        Enforcing these limitations has the advantage that values will be
        deserialized to their original representations. For example,
        ``json.dumps`` supports serializing a ``dict`` that has ``int`` keys,
        but those keys will be instances of ``str`` when deserializing the
        ``dict`` again. Similar considerations apply to instances of ``tuple``
        and ``set``: ``json.dumps`` could serialize those, but they would be
        implicitly converted to instances of ``list``.

        For those reasons, keeping ``strict_value_checking`` set to ``True`` is
        recommended. There is a small but mostly insignificant performance
        benefit in disabling ``strict_value_checking``. Therefore, code that
        knows that it only passes conforming values might want to choose to
        disable the check.

        :param system_id:
            system_id for which the value shall be stored.
        :param key:
            key for which the value shall be stored.
        :param value:
            value that shall be stored.
        """
        if self._strict_value_checking:
            self._check_value(value)
        json_value = json.dumps(value)
        with self._lock:
            self._connection.execute(
                "INSERT OR REPLACE INTO system_data (system_id, key, value) "
                "VALUES (?, ?, ?);",
                (system_id, key, json_value),
            )

    def _check_value(self, value, parents=None):
        if value is None:
            return
        if parents is None:
            parents = []
        if isinstance(value, (bool, float, int, str)):
            return
        # Before checking dicts and lists, we have to ensure that there is no
        # reference loop, otherwise the checks would continue until we run out
        # of stack space.
        for parent_val in parents:
            if parent_val is value:
                raise ValueError("Circular reference detected.")
        if isinstance(value, dict):
            for key, dict_val in value.items():
                if not isinstance(key, str):
                    raise TypeError(
                        "Object of type {0} is not strictly JSON serializable "
                        "when used as the key of a dict.".format(
                            type(key).__name__
                        )
                    )
                self._check_value(dict_val, parents + [value])
            return
        if isinstance(value, list):
            for list_val in value:
                self._check_value(list_val, parents + [value])
            return
        raise TypeError(
            "Object of type {0} is not strictly JSON serializable.".format(
                type(value).__name__
            )
        )

    def _create_tables(self):
        # We store the data in a single table. In addition to the implicit
        # index that is created on the primary key, we create an index that
        # allows us to quickly find all rows for a certain systen and an index
        # that allows us to quickly find all rows with certain key value pairs.
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS system_data (
                    system_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (system_id, key)) WITHOUT ROWID;
                CREATE INDEX IF NOT EXISTS system_id_index
                    ON system_data (system_id);
                CREATE INDEX IF NOT EXISTS key_value_index
                    ON system_data (key, value);
                """
            )

    def __enter__(self):
        # We do not have to do anything here because we already opened the
        # connection in __init__.
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Close the database connection.
        self.close()


def open_data_store(db_file: str, strict_value_checking=True) -> DataStore:
    """
    Open a data store that is backed by the specified database file. If the
    database file does not exist yet, create it.

    The `strict_value_checking` option controls the behavior of the
    `~DataStore.set_value` method. If the option is set to ``True`` (the
    default), ``set_value`` raises an exception if the specified value cannot
    be safely serialized as JSON (see that method for details about which types
    can be serialized safely).

    A data store that has been created should be closed when it is not
    needed any longer by calling its `close` method. This ensures that
    resources associated with the database connection are released
    immediately instead of when the data store object is eventually garbage
    collected.

    The object returned by this function can be used as a context manager to
    simplify resource management. Please refer to the class documentation of
    `DataStore` for an example.

    :param db_file:
        path to the database file that stores the catual data.
    :param strict_value_checking:
        ``True`` if inserted values shall be checked strictly, ``False`` if the
        checks shall be more relaxed. See `~DataStore.set_value` for details.
    :return:
        data store backed by ``db_file``.
    """
    return DataStore(db_file, strict_value_checking)
