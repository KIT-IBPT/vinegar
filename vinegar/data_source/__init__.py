"""
Sources providing configuration information associated with each system.

Different sources can be used to fill retrieve configuration information for
systems. A very flexible one is `vinegar.data_source.yaml_target`, which fills
the configuration tree by parsing a central YAML file specifies target
information (which files apply to which system) and the YAML files specified by
this central file in order to retrieve the actual data.

Multiple data sources can easily be chained by using the
`get_composite_data_source` function.

All source implementations have in common that they must specify a
`get_instance` function that takes a ``dict`` with configuration data as its
only parameter. This function must return an instance of `data_source`. The key
``name`` in that configuration ``dict`` is reserved for use by the calling code
and should be ignored by the data source.

Data sources are thread safe.
"""

import abc
import collections
import importlib

from typing import Any, Mapping, Optional, Sequence, Tuple, Union

from vinegar.utils.odict import OrderedDict
from vinegar.utils.version import aggregate_version


class DataSource(abc.ABC):
    """
    Source that provides configuration information for a system.

    The information provided can (and typically will) be different for each
    targeted system.

    This information is then passed to the templating mechanism when generating
    files requested by a client. This way, different files can be generated for
    each system.

    Often, it can be useful to have more than one data source. In this case, the
    data returned by each of the sources should be merged with the data returned
    by the other sources. The `get_composite_data_source` function provides a
    convenient tool for such a setup.

    If possible, data sources should preserve the key order in dictionaries. The
    easiest way of achieving this is using the ``OrderedDictionary`` provided by
    `vinegar.utils.odict`.

    Each data source has to implement the `get_data` method. This method is used
    to collect the data for a system with a known identifier. It also has to
    implement the `find_system` method. This method is used to find the system
    identifier using a key and an associated value.

    It is perfectly legal for a data source to be able to provide data for a
    system, but not be able to find the system ID given the data. For example,
    a data source may provide the same data to a group of systems and in that
    case it it is impossible to identify a specific system using the data.

    Data source have to be implemented in a thread-safe manner, so that
    `get_data` and `find_system` can safely be used by different threads.
    """

    @abc.abstractmethod
    def find_system(self, lookup_key: str, lookup_value: Any) -> Optional[str]:
        """
        Find a system given the specified key and value.

        If no system can be found, the data source returns ``None``.

        :param lookup_key:
            key for which to look. The interpretation of the key is up to the
            data source. Some data sources might use a flat structure, while
            others might support hierarchical data-structures. In the latter
            case, the use of the colon (:) as a hierarchy separator in the key
            is encouraged, but not required.
        :param lookup_value:
            value for which to look. The interpreation of the value is up to the
            data source.
        :return:
            system identifier or ``None`` if no system could be identified using
            the specified key and value.
        """
        return None

    @abc.abstractmethod
    def get_data(
            self,
            system_id: str,
            preceding_data: Mapping[Any, Any],
            preceding_data_version: str) -> Tuple[Mapping[Any, Any], str]:
        """
        Return data associated with the specified system.

        If the data source does not have any information associated with the
        specified system ID, it should return an empty dictionary.

        The return value of this method is in fact a tuple of the configuration
        data and a version string. The version string can be used by the calling
        code to decide whether the data has changed and thus caches have to be
        discarded. For example, the results of rendering a template might be
        cached and the cached version might be used as long as the version
        string returned by this method does not change. This means that
        implementations have to be careful to never return the same version
        string when the data for a system has changed. The
        `vinegar.utils.version` provides utility functions for generating
        version strings in a way that makes accidental collisions unlikely.

        Please note that it is not the job of a data source to merge the
        ``preceding_data`` with the data provided by itself. The calling code
        takes care of this. Code wanting to use multiple data sources in a chain
        can use the `get_composite_data_source` function.

        Implementations are encouraged to use caching to improve performance
        when this method is repeatedly called for the same systems.

        :param system_id:
            ID of the system for which data is requested.
        :param preceding_data:
            Data provided by the data source(s) that come earlier in the chain.
            This may be empty if there are no preceding data sources or if they
            did not provide any data for the system.
        :param preceding_data_version:
            Version of the ``preceding_data``. This is an arbitrary string
            (typically a hash) that can be used to detect when the data provided
            by the preceding sources has changed.
        :return:
            tuple where the first element is the data associated with the
            specified system and the second element is a version string that
            changes whenver the returned data changes (for the same system).

        """
        raise NotImplementedError()


class DataSourceAware(abc.ABC):
    """
    Marker interface indicating that a component needs access to a `DataSource`.

    An object can implement this interface in order to indicate to the creating
    code that it wants a data source to be injected into it through the
    `set_data_source` method.

    This is useful when there are several different implementations of a
    component and some of them require a data source and others do not. The
    container creating the components can decouple the logic (and configuration)
    for creating them from the logic that injects the data source.

    In general, a component that implements this interface should still try to
    provide as much of its functionality as reasonably possible, if no data
    source has been injected into it.

    Code wanting to inject a data source into a component that might possibly
    need it can use the `inject_data_source` helper function.
    """

    def set_data_source(self, data_source: DataSource) -> None:
        """
        Set the data source to be used by this component.

        Calling `inject_data_source` might be preferable to calling this method
        directly.

        In general, code using this method should not assume that this method is
        thread safe, even if the object that implements it is considered safe in
        general. This means that this method should typically be called only
        once, directly after creating an object.

        :param data_source:
            data source to be injected.
        """
        pass


class _CompositeDataSource(DataSource):
    """
    Data source that chains multiple data sources.

    This data source is used by `get_composite_data_source`.
    """

    def __init__(self, data_sources, merge_lists):
        self._data_sources = data_sources
        self._merge_lists = merge_lists

    def find_system(self, lookup_key: str, lookup_value: str) -> Optional[str]:
        # We iterate over the data sources until we find one that returns a
        # successful lookup result or we reach the end of the list.
        for data_source in self._data_sources:
            result = data_source.find_system(lookup_key, lookup_value)
            if result is not None:
                return result
        return None

    def get_data(
            self,
            system_id: str,
            preceding_data: Mapping[Any, Any],
            preceding_data_version: str) -> Tuple[Mapping[Any, Any], str]:
        # We iterate over the data sources, providing the result of the previous
        # ones to the next one. We also merge the results in each step.
        for data_source in self._data_sources:
            new_data, new_data_version = data_source.get_data(
                system_id, preceding_data, preceding_data_version)
            preceding_data = merge_data_trees(preceding_data, new_data)
            preceding_data_version = aggregate_version(
                [preceding_data_version, new_data_version])
        return preceding_data, preceding_data_version


def get_composite_data_source(
        data_sources:
        Sequence[Union[Tuple[str, Mapping[Any, Any]], DataSource]],
        merge_lists: bool = False,
        merge_sets: bool = True) -> DataSource:
    """
    Return a data source that is a composite of the specified data sources.

    The returned data source takes the provided initial data and passes it to
    the first data source in the chain. It then takes the result of that data
    source, merges it with the initial data, and passes the merged data to the
    next data source in the chain. This process goes on until the last data
    source has been reached. At this point, the result of the last data source
    is merged with the result of the previous data source and returned.

    The data source returned by this function internally uses
    `merge_data_trees` to merge the data returned by a source with the
    preceding data. The ``merge_lists`` option is passed on to that function and
    defines whether lists are also merged. By default, only dictionaries are
    merged.

    :param data_sources:
        sequence of data sources that are chained together. Each item in the
        sequence can either be an instance of `DataSource` or a tuple. If it is
        a tuple, the first element must be the name of the data source (as
        passed to `get_data_source`) and the second one must be the
        corresponding configuration.
    :param merge_lists:
        defines whether lists are merged when merging data or whether a list in
        one dictionary replaces the list in the other dictionary. Please refer
        to the documentation for `merge_data_trees` for details.
    :return:
        composite data source that chains the specified data sources together.
    """
    data_source_objs = []
    for source in data_sources:
        if isinstance(source, DataSource):
            data_source_objs.append(source)
        else:
            data_source_objs.append(get_data_source(source[0], source[1]))
    return _CompositeDataSource(data_source_objs, merge_lists)


def get_data_source(name: str, config: Mapping[Any, Any]) -> DataSource:
    """
    Create the an instance of the data source with the specified name, using
    the specified configuration.

    :param name:
        name of the data source. If the name contains a dot, it is treated as an
        absolute module name. Otherwise it is treated as a name of one of the
        modules inside the `vinegar.data_source` module.
    :param: config:
        configuration data for the data source. The meaning of that data is up
        to the implementation of the data source.
    :return:
        newly created data source.
    """
    module_name = name if '.' in name else '{0}.{1}'.format(__name__, name)
    data_source_module = importlib.import_module(module_name)
    return data_source_module.get_instance(config)


def inject_data_source(obj: Any, data_source: DataSource) -> None:
    """
    Inject a data source into an object.

    This data source is only injected if ``obj`` is an instance of
    `DataSourceAware`, so it is safe to call this function for any object.

    In general, code using this function should not assume that it is thread
    safe, even if the object that is the target of the injection is considered
    thread safe in general. This means that this function should typically be
    called only once, directly after creating an object.

    :param obj:
        object that might or might not be an instance of `DataSourceAware`.
    :param data_source:
        data source to be injected. It is only injected if ``obj`` is
        `DataSourceAware`.
    """
    if isinstance(obj, DataSourceAware):
        obj.set_data_source(data_source)


def merge_data_trees(
        tree1: Mapping[Any, Any],
        tree2: Mapping[Any, Any],
        merge_lists: bool = False,
        merge_sets: bool = True) -> Mapping[Any, Any]:
    """
    Merge two mappings, returning the resulting dictionary.

    In general, the resulting dictionary is formed by taking the key-value pairs
    from both mappings and putting them into a single dictionary. If the same
    key is present in both dictionaries, the value from the second dictionary
    takes precedence.

    If the value is itself a mapping, the merge process is applied recursively.

    If the value is a sequence, the process depends on the ``merge_lists``
    option. If it is set to ``True``, the resulting list is created by first
    adding all elements from the first sequence and then appending all elements
    from the second sequence, except for those elements that were already
    present in the first sequence. If ``merge_lists`` is set to ``False``, the
    second sequence simply replaces the first one (like for non-sequence types).

    If the value is a set, the process depends on the ``merge_sets`` option. If
    it is set to ``True`` (the default), the resulting set is created by
    calculating the union of both sets (``set1 | set2``). If it is set to
    ``False``, the second set simply replaces the first one (like for non-set
    types).

    In this context, the ``str``, ``bytes``, ``bytearray``, and ``memoryview``
    types are not treated as sequences. Values of this type always replace each
    other and are not merged.

    If the value associated with a key is a mapping in one mapping, but not in
    the other one, an exception is thrown. The same applies when ``merge_lists``
    is ``True`` and the value associated with a key is a sequence in one
    mapping, but not in the other one.

    The resulting dictionary preserves key order. This means that it first
    contains all keys from the first mapping and then those keys from the second
    mapping that were not also present in the first mapping. It achieves this by
    using an instance of the ``OrderedDict`` provided by `vinegar.utils.odict`.
    Please note that this is not necessarily an instance of
    ``collections.OrderedDict``, but just a dictionary that preserves insertion
    order.

    :param tree1:
        mapping that shall be used as a base for the merge process.
    :param tree2:
        mapping that is merged into the data from ``tree1``, taking precedence
        in case of key collisions.
    :param merge_lists:
        ``True`` if sequences in the mappings shall be merged, too, ``False``
        if they shall replace each other. The default is ``False``.
    :param merge_sets:
        ``True`` if sets in the mappings shall be merged, too, ``False`` if they
        shall replace each other. The default is ``True``.
    :return:
        insertion-order preserving dictionary that contains the merged data from
        ``tree1`` and ``tree2``.
    """
    return _merge_data_trees(tree1, tree2, merge_lists, merge_sets, None)


def _merge_data_trees(tree1, tree2, merge_lists, merge_sets, parent_key):
    """
    Merge two dictionaries (or other kind of mappings). This is the internal
    implementation for `merge_data_trees`.
    """
    # We explicitly create a new ordered dict so that we will preserve the order
    # if either of the two dicts has an order.
    merged = OrderedDict()
    for key, value in tree1.items():
        if key in tree2:
            override_value = tree2[key]
            val_is_mapping = isinstance(value, collections.abc.Mapping)
            val_is_set = isinstance(value, collections.abc.Set)
            val_is_seq = (
                isinstance(value, collections.abc.Sequence)
                and not isinstance(value, (bytearray, bytes, memoryview, str)))
            oval_is_mapping = isinstance(
                override_value, collections.abc.Mapping)
            oval_is_set = isinstance(override_value, collections.abc.Set)
            oval_is_seq = (
                isinstance(override_value, collections.abc.Sequence)
                and not isinstance(
                    override_value, (bytearray, bytes, memoryview, str)))
            if parent_key is None:
                absolute_key = key
            else:
                absolute_key = '{0}:{1}'.format(parent_key, key)
            if val_is_mapping and oval_is_mapping:
                merged[key] = _merge_data_trees(
                    value,
                    override_value,
                    merge_lists,
                    merge_sets,
                    absolute_key)
            elif merge_lists and val_is_seq and oval_is_seq:
                merged_list = list(value)
                for element in override_value:
                    if element not in merged_list:
                        merged_list += [element]
                merged[key] = merged_list
            elif merge_sets and val_is_set and oval_is_set:
                merged[key] = value | override_value
            elif val_is_mapping or oval_is_mapping:
                raise TypeError(
                    'Cannot merge mapping type with non-mapping type while '
                    'trying to merge value for key {0}.'.format(absolute_key))
            elif merge_sets and (val_is_set or oval_is_set):
                raise TypeError(
                    'Cannot merge set type with non-set type while '
                    'trying to merge value for key {0}.'.format(absolute_key))
            elif merge_lists and (val_is_seq or oval_is_seq):
                raise TypeError(
                    'Cannot merge sequence type with non-sequence type while '
                    'trying to merge value for key {0}.'.format(absolute_key))
            else:
                merged[key] = override_value
        else:
            merged[key] = value
    for key, value in tree2.items():
        if key not in merged:
            merged[key] = value
    return merged
