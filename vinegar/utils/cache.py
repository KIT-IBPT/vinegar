"""
Caching utilities.

This module provides various `Cache` implementations that can be used to store
data that might be reused, while limiting the max. amount of memory that may be
consumed.

For a cache implementation implementing the LRU strategy, see `LRUCache`.
"""

import abc
import collections
import threading
import typing

KeyT = typing.TypeVar("KeyT")
ValueT = typing.TypeVar("ValueT")


class Cache(typing.Generic[KeyT, ValueT], abc.ABC):  # pylint: disable=E1136
    """
    Interface for cache implementations

    This interface is similar to a ``MutableMapping``, but it does not provide
    an iterator and it does not provide the methods ``keys()``, ``items()``,
    ``setdefault(...)``, ``update(...)``, and ``values()``. It does not support
    comparison either.

    In addition to that, code using a cache should not assume that accessing a
    key (be it by subscripts or through the `get` method) is a read-only
    operation, because the cache might internally keep track of which key has
    been accessed last.

    An obvious difference to regular mappings is that a cache is typically
    limited in size, so inserting a new key might have the side effect of
    removing another one.
    """

    @abc.abstractmethod
    def clear(self) -> None:
        """
        Clear cache (remove all items).
        """
        raise NotImplementedError()

    @typing.overload
    def get(self, key: KeyT) -> typing.Optional[ValueT]:
        ...

    @typing.overload
    def get(self, key: KeyT, default: ValueT) -> ValueT:
        ...

    @typing.overload
    def get(
        self, key: KeyT, default: typing.Optional[ValueT]
    ) -> typing.Optional[ValueT]:
        ...

    def get(
        self, key: KeyT, default: typing.Optional[ValueT] = None
    ) -> typing.Optional[ValueT]:
        """
        Return the item for the specified ``key`` or ``default`` if the key is
        not stored in this cache.

        :param key:
            key that identifies the entry in this cache.
        :param default:
            default value that is returned if the key is not found.
        :return:
            value for ``key`` or ``default`` if ``key`` is not found.
        """
        try:
            return self[key]
        except KeyError:
            return default

    @abc.abstractmethod
    def __contains__(self, item: KeyT) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def __delitem__(self, key: KeyT) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def __getitem__(self, key: KeyT) -> ValueT:
        raise NotImplementedError

    @abc.abstractmethod
    def __len__(self) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def __setitem__(self, key: KeyT, value: ValueT) -> None:
        raise NotImplementedError


class LRUCache(Cache[KeyT, ValueT]):
    """
    Cache using the last recently used (LRU) strategy.

    This cache implementation is not thread-safe. If it is supposed to be used
    from multiple threads, wrap it in a `SynchronizedCache`.
    """

    def __init__(self, cache_size: int = 16, mark_on_update: bool = True):
        """
        Create a LRU cache using the specified size.

        :param cache_size:
            max. number of items that is cached. When this size is reached and
            a new key is inserted, the key that has been least-recently used is
            removed from the cache. The default size is 16.
        :param mark_on_update:
            if ``True`` mark a key as recently used when its value is updated.
            If ``False`` updating the value for a key does not affect its
            position in the cache, so it might still be removed from the cache
            shortly after. The default is ``True``.
        """
        if cache_size < 1:
            raise ValueError("Cache size must be strictly positive.")
        self._cache_size = cache_size
        # We cannot use a regular dict here because we need the move_to_end
        # method.
        self._data = collections.OrderedDict()
        self._mark_on_update = mark_on_update

    def clear(self) -> None:
        self._data.clear()

    def __contains__(self, item: KeyT) -> bool:
        # We implement __contains__ because the default version uses
        # __getitem__, which changes the order of elements.
        return item in self._data

    def __delitem__(self, key: KeyT) -> None:
        del self._data[key]

    def __getitem__(self, key: KeyT) -> ValueT:
        value = self._data.__getitem__(key)
        self._data.move_to_end(key)
        return value

    def __len__(self) -> int:
        return len(self._data)

    def __setitem__(self, key: KeyT, value: ValueT) -> None:
        self._data.__setitem__(key, value)
        if self._mark_on_update:
            self._data.move_to_end(key)
        if len(self._data) > self._cache_size:
            self._data.popitem(last=False)


class NullCache(Cache[KeyT, ValueT]):
    """
    Cache that actually does not cache anything.

    This implementation is useful when code expects a cache to be present, but
    caching shall be disabled.
    """

    def clear(self) -> None:
        pass

    def __contains__(self, item: KeyT) -> bool:
        return False

    def __delitem__(self, key: KeyT) -> None:
        raise KeyError(key)

    def __getitem__(self, key: KeyT) -> ValueT:
        raise KeyError(key)

    def __len__(self) -> int:
        return 0

    def __setitem__(self, key: KeyT, value: ValueT) -> None:
        pass


class SynchronizedCache(Cache[KeyT, ValueT]):
    """
    Wrapper around a cache instance that makes it thread-safe.
    """

    def __init__(self, backing_cache: Cache[KeyT, ValueT]):
        """
        Creates a cache wrapped with a lock that protects all operations so
        that the cache can safely be used from multiple threads.

        :param backing_cache:
            Cache instance that actually implements the cache.
        """
        self._backing_cache = backing_cache
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock:
            self._backing_cache.clear()

    def __contains__(self, item: KeyT) -> bool:
        with self._lock:
            return item in self._backing_cache

    def __delitem__(self, key: KeyT) -> None:
        with self._lock:
            del self._backing_cache[key]

    def __getitem__(self, key: KeyT) -> ValueT:
        with self._lock:
            return self._backing_cache[key]

    def __len__(self) -> int:
        with self._lock:
            return len(self._backing_cache)

    def __setitem__(self, key: KeyT, value: ValueT) -> None:
        with self._lock:
            self._backing_cache[key] = value
