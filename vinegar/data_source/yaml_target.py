"""
YAML-based source for configuration data, using pattern-based targeting.

This data source uses a flexible and powerful targeting mechanism. It works on
a directory tree where the file ``top.yaml`` in the root of the tree defines
targeting rules that specify which systems receive which configuration data.

Due to this flexible architecture, this data source cannot identify a system
given a key and an associated value, so its `~DataSource.find_system` method
will always return ``None``.

File syntax
-----------

For example, the file ``top.yaml`` might look like this::

    # Files applied to all systems:
    '*':
        - common.file1
        - common.file2

    # Files applied to systems that have an ID starting with "mysys-"
    'mysys-*':
        - example

    # Files applied to all systems that have an ID that ends with
    # ".a.example.com" or ".b.example.com".
    '*.a.example.com or *.b.example.com':
        - other.example

In this example, a system named ``mysys-x.b.example.com`` would receive data
from the following files in the directory tree:

* common/file1.yaml
* common/file2.yaml
* example.yaml
* other/example.yaml

A system with the ID ``my.example.com``, on the other hand, would only receive
data from the following files:

* common/file1.yaml
* common/file2.yaml

In order to make the file structure cleaner, instead of creating a file in a
directory, one can create a sub-directory with a file called ``init.yaml``.

For example, the reference to ``example`` would be resolved to
``example/init.yaml`` if ``example.yaml`` does not exist.

Keys in ``top.yaml`` can be system IDs or patterns matching system IDs, but
they can also be combinations of several such patterns using logical
expressions. Please refer to the documentation of the
`vinegar.utils.system_matcher` for details.

Each data file (e.g. ``common/file1.yaml`` in the example above) is a simple
YAML file that provides configuration data.

Such a file might look like this::

  boot_files:
    kernel: vmlinuz-4.4.0-148-generic
    initrd: initrd.img-4.4.0-148-generic

A data file can include other data files by listing the under the ``include``
key::

  include:
    - some.otherfile
    - example.more

This has the same effect as if the content of that file was pasted at the
position of the include, with one difference: Duplicate keys will not cause a
parsing errors. Instead, they are going to be merged (see below).

Merging multiple data files
---------------------------

More than one data file can apply to a single system through several ways:

* A key in the ``top.yaml`` file can list more than one file.
* A system ID might match multiple keys (patterns) in ``top.yaml``.
* A data file that is included through ``top.yaml`` might itself include other
  data files.

In all these cases, the data provided by the different files is merged. When
merging data, values from files that are listed later, take precedence over
files that are listed earlier.

When using ``include:`` in a data file, data from the included files overrides
data that precedes the ``include:`` block, but not data that follows the block.

Dictionaries that are part of the data tree are merged. By default, lists are
not merged but replaced, however this can be changed through the
``merge_lists`` configuration option.

Please note that this data source does never merge the data passed to its
`~YamlTargetSource.get_data` method (through the ``preceding_data`` argument)
into the resulting data. If this is desired, a composite data source (see
`vinegar.data_source.get_composite_data_source`) should be used.

Using Templating
----------------

The YAML files that are used by this data source can contain template code.
By default, the `~vinegar.template.jinja` template engine is used. Please
refer to the documentation of that engine for details about the syntax.

Another template engine can be selected through the ``template`` configuration
option, or templating can be disabled completely by setting that option to
``None``.

The data source provides two context objects to the template engine: The ``id``
object contains the system ID (as a ``str``) and the ``data`` objects contains
the data that has been passed to the `~YamlTargetSource.get_data` method as
``preceding_data``. The ``data`` object is passed as a
`~vinegar.utils.smart_dict.SmartLookupDict` to make it easier to get nested
values.

Configuration options
---------------------

This data source has several configuration options that can be used to control
its behavior. Of all these options, only the ``root_dir`` option must be
specified. All other options have default values.

:``root_dir``:
    path to the directory that contains ``top.yaml`` (as a ``str``). All other
    files are also resolved relative to this directory.

:``allow_empty_top``:
    If set to ``True`` having a ``top.yaml`` file that is empty does not result
    in an exception being raised. This can be useful when templating code is
    used to selectively generate content in ``top.yaml``. The default is
    ``False`` which means that an exception is raised if ``top.yaml`` does not
    contain at least one key-value pair.

:``cache_size``:
    Maximum number of data trees that are cached. This data source uses an
    ``LRUCache`` so that the process of compiling the data for a specific
    system does not have to be repeated for every call to
    `~YamlTargetSource.get_data`. By default, this cache stores up to
    64 entries. If set to zero, the cache is disabled completely. Please note
    that this will not disable the cache of the template engine that is used.
    Please refer to the documentation for the template engine in use to see
    whether it uses a cache and how it can be disabled.

:``merge_lists``:
    If ``True``, lists are merged when merging data from different data files.
    If ``False`` (the default), lists are not merged, but replaced. Please
    refer to the documentation for `~vinegar.data_source.merge_data_trees` for
    details about the effects of this option.

:``merge_sets``:
    If ``True`` (the default), sets are merged when merging data from different
    data files. If ``False``, sets are not merged, but replaced. Please refer
    to the documentation for `~vinegar.data_source.merge_data_trees` for
    details about the effects of this option.

:``template``:
    name of the template engine (as a ``str``) that shall be used for rending
    the ``top.yaml`` and the data files. The default is ``jinja``. This name is
    passed to `~vinegar.template.get_template_engine` in order to retrieve the
    template engine. If set to ``None`` templating is disabled.

:``template_config``:
    configuration for the template engine. The default is an empty dictionary
    (``{}``). This configuration is passed on to the template engine as is.
"""

import collections
import collections.abc
import copy
import os.path
import pathlib

from typing import Any, Mapping, Optional, Tuple

import yaml

import vinegar.template
import vinegar.utils.cache
import vinegar.utils.system_matcher

from vinegar.data_source import DataSource, merge_data_trees
from vinegar.utils.smart_dict import SmartLookupDict
from vinegar.utils.version import (
    aggregate_version,
    version_for_str,
)


class YamlTargetSource(DataSource):
    """
    Data source that constructs a configuration tree through a flexible
    targeting mechanism.

    For information about the configuration options supported by this data
    source, please refer to the
    `module documentation <vinegar.data_source.yaml_target>`.
    """

    def __init__(self, config: Mapping[Any, Any]):
        """
        Create a YAML data source using the specified configuration.

        :param config:
            configuration for this data source. Please refer to the
            `module documentation <vinegar.data_source.yaml_target>` for a list
            of supported options.
        """
        self._allow_empty_top = config.get("allow_empty_top", False)
        self._root_dir_path = pathlib.Path(config["root_dir"])
        self._merge_lists = config.get("merge_lists", False)
        self._merge_sets = config.get("merge_sets", True)
        # We need the path to the top file frequently, so it makes sense to
        # keep it as an instance variable. We use absolute paths everywhere in
        # this class so that we can detect it more easily when two path names
        # refer to the same file.
        self._top_file = os.path.abspath(str(self._root_dir_path / "top.yaml"))
        # We create a cache where we can save results of earlier calls to
        # get_data(...). As the data source has to be thread safe, the cache
        # has to be thread safe. If the cache size is zero or negative, we
        # disable caching.
        cache_size = config.get("cache_size", 64)
        if cache_size <= 0:
            self._cache = vinegar.utils.cache.NullCache()
        else:
            self._cache = vinegar.utils.cache.SynchronizedCache(
                vinegar.utils.cache.LRUCache(cache_size=cache_size)
            )
        # Create the template engine.
        template_engine_name = config.get("template", "jinja")
        if template_engine_name is None:
            self._template_engine = None
        else:
            self._template_engine = vinegar.template.get_template_engine(
                config.get("template", "jinja"),
                config.get("template_config", {}),
            )

    def find_system(self, lookup_key: str, lookup_value: Any) -> Optional[str]:
        # Due to the fact that we use patterns to identify systems, there is
        # absolutely now way to find a system given a key and a value, so we
        # always return None.
        return None

    def get_data(
        self,
        system_id: str,
        preceding_data: Mapping[Any, Any],
        preceding_data_version: str,
    ) -> Tuple[Mapping[Any, Any], str]:
        data_compiler = _DataCompiler(
            self._allow_empty_top,
            self._merge_lists,
            self._merge_sets,
            self._root_dir_path,
            self._template_engine,
            self._top_file,
        )
        old_cache_item = self._cache.get(system_id, None)
        data, data_version, new_cache_item = data_compiler.compile_data(
            system_id, preceding_data, old_cache_item
        )
        # If we have a new version of the cache item, we have to update the
        # cache. Obviously, there is a race condition when updating the cache,
        # but this does not matter. If we update the cache with an older
        # version, this is going to be detected and fixed on the next call to
        # this method.
        if new_cache_item and (new_cache_item is not old_cache_item):
            self._cache[system_id] = new_cache_item
        # We make a deep copy of the data before returning it. This way, we can
        # avoid a situation in which the calling code makes modifications to
        # the returned dictionary (or a data structure included in it) and this
        # affects later calls.
        return copy.deepcopy(data), data_version


# Each value in the cache item for a system is in instance of this type.
_CachedData = collections.namedtuple("_CachedData", ("data", "version"))


# pylint: disable=too-few-public-methods
class _DataCompiler:
    """
    Compiles data for a system.

    A new instance of this class is created for each call to
    `YamlTargetSource.get_data`.

    Objects of this type are not thread safe.
    """

    def __init__(
        self,
        allow_empty_top,
        merge_lists,
        merge_sets,
        root_dir_path,
        template_engine,
        top_file,
    ):
        self._allow_empty_top = allow_empty_top
        self._merge_lists = merge_lists
        self._merge_sets = merge_sets
        self._root_dir_path = root_dir_path
        self._template_engine = template_engine
        self._top_file = top_file

    # We create some attributes here instead of in __init__. This is okay
    # because this is the only public method of this class, so all other
    # methods can still be sure that these attributes exist.
    #
    # pylint: disable=attribute-defined-outside-init
    def compile_data(self, system_id, preceding_data, old_cache):
        """
        Compiles the data for the specified system ID and preceding data.

        :param system_id:
            system for which the data shall be compiled.
        :param preceding_data:
            data supplied by the preceding data sources. This data is passed as
            part of the context when rendering templates.
        :param old_cache:
            cache returned by an earlier call to this function or ``None`` if
            this is the first call to this function for the specified system
            ID, or the data from the last call is not in the cache any longer.
        :return:
            tuple of the compiled data, the associated version, and the updated
            cache.
        """
        # We create a new cache object on each iteration because if there are
        # changes, they might result in files not being part of the tree any
        # longer and if we simply updated the old cache, the data for these
        # files would never be removed.
        self._context = {
            "id": system_id,
            "data": SmartLookupDict(preceding_data),
        }
        self._new_cache = {}
        if old_cache is None:
            self._old_cache = {}
        else:
            self._old_cache = old_cache
        self._system_id = system_id
        data_files = self._process_top()
        # We process each of the files that were listed in top.yaml.
        if data_files:
            data_list = self._process_data_files(["top file"], data_files)
            data_items, data_versions = zip(*data_list)
        else:
            data_items = tuple()
            data_versions = tuple()
        # The result version is an aggregate of the versions of the involved
        # files. We do not have to consider the version of the top file,
        # because changes in the top file only matter if they lead to a
        # different set or order of data files and this will be reflected in
        # the list of versions.
        data_version = aggregate_version(data_versions)
        cached_result = self._old_cache.get("result", None)
        if cached_result and (cached_result.version == data_version):
            return cached_result.data, cached_result.version, self._old_cache
        data = {}
        for data_item in data_items:
            data = merge_data_trees(
                data,
                data_item,
                merge_lists=self._merge_lists,
                merge_sets=self._merge_sets,
            )
        self._new_cache["result"] = _CachedData(data, data_version)
        return data, data_version, self._new_cache

    def _expression_matches(self, target_expression):
        if not isinstance(target_expression, str):
            raise TypeError(
                f"Invalid target expression in { self._top_file}: Expected a "
                "string, but got an object of type "
                f"{type(target_expression).__name__}."
            )
        return vinegar.utils.system_matcher.match(
            self._system_id, target_expression
        )

    def _process_data_file(self, parent_files, file_name, file_path):
        # If a file recursively includes itself (directly or indirectly), we
        # end up in an infinite loop, so we have to detect such a situation.
        if file_name in parent_files:
            file_index = parent_files.index(file_name)
            include_chain = " -> ".join(
                parent_files[file_index:] + [file_name]
            )
            raise RuntimeError(
                f"Recursion loop detected in file {file_name}: The file is "
                "included by itself through the following chain: "
                f"{include_chain}"
            )
        # The same file might already have been processed because it is
        # referenced in more than one place. In this case, we prefer the
        # version in the new cache over the version in the old cache, because
        # the version in the new cache might be newer.
        cache_key = "data_file_" + file_name
        try:
            cached_file = self._new_cache[cache_key]
        except KeyError:
            try:
                cached_file = self._old_cache[cache_key]
            except KeyError:
                cached_file = None
        try:
            file_yaml = self._render(file_path)
            file_version = version_for_str(file_yaml)
            # If the file has not changed, we can use the cached data. We still
            # have to process the included files because they might have
            # changed.
            if cached_file and (file_version == cached_file.version):
                cache_valid = True
            else:
                cache_valid = False
                file_data = yaml.safe_load(file_yaml)
        except Exception as err:
            raise RuntimeError(
                f"Error processing data file {file_name}."
            ) from err
        # If the data from the cache is valid, we can simply use it. Otherwise,
        # we have to process the file content.
        if cache_valid:
            # cached_file.data is a tuple of three items: The data preceding
            # the include block, the list stored inside the include block, and
            # the data following the include block.
            (
                preceding_data,
                include_files,
                following_data,
            ) = cached_file.data  # type: ignore
            # We might have gotten the data from the old cache, so we have to
            # copy it to the new cache.
            self._new_cache[cache_key] = cached_file
        else:
            if not isinstance(
                file_data, collections.abc.Mapping  # type: ignore
            ):
                raise TypeError(
                    f"File {file_name} does not contain a dictionary as its "
                    "top structure."
                )
            (
                preceding_data,
                include_files,
                following_data,
            ) = self._process_data_file_content(file_data)
            self._new_cache[cache_key] = _CachedData(
                (preceding_data, include_files, following_data), file_version
            )
        data_list = []
        if preceding_data:
            data_list += [(preceding_data, file_version)]
        if include_files:
            data_list += self._process_data_files(
                parent_files + [file_name], include_files
            )
        if following_data:
            data_list += [(following_data, file_version)]
        return data_list

    @staticmethod
    def _process_data_file_content(file_data):
        # If the file does not include any other files, we can simply use its
        # data as the preceding data.
        if "include" not in file_data:
            return file_data, None, None
        # If the includes come first, we can use a simplified approach for the
        # merging.
        if next(iter(file_data.keys())) == "include":
            include_files = file_data["include"]
            del file_data["include"]
            return None, include_files, file_data
        # If the includes come somewhere in the middle of the file, we have to
        # split the data between the part that comes before the includes and
        # the part that comes after the includes.
        preceding_data = {}
        following_data = {}
        before_include = True
        for key, value in file_data.items():
            if key == "include":
                include_files = value
                before_include = False
            elif before_include:
                preceding_data[key] = value
            else:
                following_data[key] = value
        # Some linters may think that include_files could be uninitialized
        # here. However, we checked earlier that file_data contains the
        # "include" key, so the loop must have set include_files.
        return preceding_data, include_files, following_data  # type: ignore

    def _process_data_files(self, parent_files, file_list):
        if not isinstance(file_list, collections.abc.Sequence):
            raise TypeError(
                f"Malformed file list in {parent_files[-1]}: Found an object "
                f"of type {type(file_list).__name__} where a list was "
                "expected."
            )
        data_files = []
        for file_name in file_list:
            if not isinstance(file_name, str):
                raise TypeError(
                    f"Malformed file list in {parent_files[-1]}: Found an "
                    f"object of type {type(file_name).__name__} where a "
                    "string was expected."
                )
            # Files are specified in the form module1.module2.file, which has
            # to be translated to a path in the form
            # ${root}/module1/module2/file.yaml. However, the same
            # specification could also refer to
            # ${root}/module1/module2/file/init.yaml, we try the first one
            # first and if that is not found, we look for the second one.
            file_path_segments = file_name.split(".")
            file_path = self._root_dir_path
            while file_path_segments:
                file_path = file_path / file_path_segments.pop(0)
            # Look for a YAML file with the name:
            file_path_yaml = file_path.with_suffix(".yaml")
            if file_path_yaml.exists():
                data_files.append(
                    (file_name, os.path.abspath(str(file_path_yaml)))
                )
            else:
                file_path_init_yaml = file_path / "init.yaml"
                if file_path_init_yaml.exists():
                    data_files.append(
                        (file_name, os.path.abspath(str(file_path_init_yaml)))
                    )
                else:
                    raise FileNotFoundError(
                        f"File {file_name} included by {parent_files[-1]} "
                        "could not be found."
                    )
        data_list = []
        for data_file_name, data_file in data_files:
            # _process_data_file returns a list of tuples. Each of this tuples
            # contains the data that shall later be merged into the result and
            # the version of the file that provided that data.
            data_file_data_list = self._process_data_file(
                parent_files, data_file_name, data_file
            )
            data_list += data_file_data_list
        return data_list

    def _process_top(self):
        if not pathlib.Path(self._top_file).exists():
            raise FileNotFoundError(
                f"Could not find top.yaml in {self._root_dir_path}."
            )
        try:
            top_yaml = self._render(self._top_file)
            top_version = version_for_str(top_yaml)
            # If we have a cache entry for top.yaml and the version has not
            # changed, we can simply use the cached data instead of parsing the
            # YAML again.
            cached_top = self._old_cache.get("top", None)
            if cached_top and (cached_top.version == top_version):
                self._new_cache["top"] = cached_top
                return cached_top.data
            top_data = yaml.safe_load(top_yaml)
        except Exception as err:
            raise RuntimeError("Error processing top file.") from err
        if top_data is None:
            # If the top data is empty, this is most likely an error, however
            # when using Jinja in the top file, it could be that it is by
            # intention, so we allow to disable this error through a
            # configuration option.
            if self._allow_empty_top:
                self._new_cache["top"] = _CachedData(None, top_version)
                return None
            raise TypeError(
                "Top file is empty. This is most likely an error. If not, set "
                "the allow_empty_top configuration option to True, to disable "
                "this exception."
            )
        if not isinstance(top_data, collections.abc.Mapping):
            raise TypeError(
                "Top file does not contain a dictionary as its top structure."
            )
        data_files = []
        for target_expression, file_list in top_data.items():
            if not isinstance(file_list, collections.abc.Sequence):
                raise TypeError(
                    f"Malformed file list in {self._top_file}: Found an object "
                    f"of type {type(file_list).__name__} where a list was "
                    "expected."
                )
            if self._expression_matches(target_expression):
                data_files += file_list
        self._new_cache["top"] = _CachedData(data_files, top_version)
        return data_files

    def _render(self, template_path):
        if self._template_engine is None:
            with open(template_path, "r", encoding="utf-8") as file:
                return file.read()
        else:
            return self._template_engine.render(
                template_path, copy.deepcopy(self._context)
            )


def get_instance(config: Mapping[Any, Any]) -> YamlTargetSource:
    """
    Create a YAML data source supporting targeting.

    For information about the configuration options supported by that source,
    please refer to the
    `module documentation <vinegar.data_source.yaml_target>`.

    :param config:
        configuration for the data source.
    :return:
        YAML data source using the specified configuration.
    """
    return YamlTargetSource(config)
