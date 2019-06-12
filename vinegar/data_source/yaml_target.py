"""
YAML-based source for configuration data, using pattern-based targeting.

This data source uses a flexible and powerful targeting mechanism. It works on a
directory tree where the file ``top.yaml`` in the root of the tree defines
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

A system with the ID ``my.example.com`` oh the other hand would only receive
data from the following files:

* common/file1.yaml
* common/file2.yaml

In order to make the file structure cleaner, instead of creating a file in a
directory, one can create a sub-directory with a file called ``init.yaml``.

For example, the reference to ``example`` would be resolved to
``example/init.yaml`` if ``example.yaml`` does not exist.

Keys in ``top.yaml`` can be system IDs or patterns matching system IDs, but they
can also be combinations of several such patterns using logical expressions.
Please refer to the documentation of the `vinegar.utils.system_matcher` for
details.

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
not merged but replaced, however this can be changed through the ``merge_lists``
configuration option.

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
`~vinegar.utils.smart_dict.SmartLookupOrderedDict` to make it easier to get
nested values.

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
    ``LRUCache`` so that the process of compiling the data for a specific system
    does not have to be repeated for every call to `~YamlTargetSource.get_data`.
    By default, this cache stores up to 64 entries. If set to zero, the cache is
    disabled completely. Please note that this will not disable the cache of the
    template engine that is used. Please refer to the documentation for the
    template engine in use to see whether it uses a cache and how it can be
    disabled.

:``merge_lists``:
    If ``True``, lists are merged when merging data from different data files.
    If ``False`` (the default), lists are not merged, but replaced. Please refer
    to the documentation for `~vinegar.data_source.merge_data_trees` for details
    about the effects of this option.

:``merge_sets``:
    If ``True`` (thedefault), sets are merged when merging data from different
    data files. If ``False``, sets are not merged, but replaced. Please refer
    to the documentation for `~vinegar.data_source.merge_data_trees` for details
    about the effects of this option.

:``template``:
    name of the template engine (as a ``str``) that shall be used for rending
    the ``top.yaml`` and the data files. The default is ``jinja``. This name is
    passed to `~vinegar.template.get_template_engine` in order to retrieve the
    template engine. If set to ``None`` templating is disabled.

:``template_config``:
    configuration for the template engine. The default is an empty dictionary
    (``{}``). This configuration is passed on to the template engine as is.
"""

import collections.abc
import os.path
import pathlib

import vinegar.template
import vinegar.utils.cache
import vinegar.utils.system_matcher

from typing import Any, Mapping, Tuple

from vinegar.data_source import DataSource, merge_data_trees
from vinegar.utils import oyaml as yaml
from vinegar.utils.odict import OrderedDict
from vinegar.utils.smart_dict import SmartLookupOrderedDict
from vinegar.utils.version import aggregate_version, version_for_file_path

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
        self._allow_empty_top = config.get('allow_empty_top', False)
        self._root_dir_path = pathlib.Path(config['root_dir'])
        self._merge_lists = config.get('merge_lists', False)
        self._merge_sets = config.get('merge_sets', True)
        # We need the path to the top file frequently, so it makes sense to keep
        # it as an instance variable. We use absolute paths everywhere in this
        # class so that we can detect it more easily when two path names refer
        # to the same file.
        self._top_file = os.path.abspath(
            (self._root_dir_path / 'top.yaml').as_posix())
        # We create a cache where we can save results of earlier calls to
        # get_data(...). As the data source has to be thread safe, the cache has
        # to be thread safe. If the cache size is zero or negative, we disable
        # caching.
        cache_size = config.get('cache_size', 64)
        if cache_size <= 0:
            self._cache = vinegar.utils.cache.NullCache()
        else:
            self._cache = vinegar.utils.cache.SynchronizedCache(
                vinegar.utils.cache.LRUCache(cache_size=cache_size))
        # Create the template engine.
        template_engine_name = config.get('template', 'jinja')
        if template_engine_name is None:
            self._template_engine = None
        else:
            self._template_engine = vinegar.template.get_template_engine(
                config.get('template', 'jinja'),
                config.get('template_config', {}))

    def find_system(self, lookup_key: str, lookup_value: Any) -> str:
        # Due to the fact that we use patterns to identify systems, there is
        # absolutely now way to find a system given a key and a value, so we
        # always return None.
        return None

    def get_data(
            self,
            system_id: str,
            preceding_data: Mapping[Any, Any],
            preceding_data_version: str) -> Tuple[Mapping[Any, Any], str]:
        cache_item = self._cache.get(system_id, None)
        if cache_item is not None and self._is_cache_item_current(
                cache_item, preceding_data_version):
            return cache_item['data'], cache_item['data_version']
        data, sources = self._compile_data(system_id, preceding_data)
        # Our data depends on the preceding data and the files that have been
        # used to compile it, so we have to calculate the aggregate version.
        # sources is a dictionary where each key is a filename and each value
        # is the version corresponding to that file, so for calculating the
        # aggregate version, we are only interested in the values.
        data_version = aggregate_version(
            [preceding_data_version] + list(sources.values()))
        cache_item = {
            'data': data,
            'data_version': data_version,
            'preceding_data_version': preceding_data_version,
            'sources': sources,
        }
        self._cache[system_id] = cache_item
        return data, data_version

    @staticmethod
    def _add_to_sources(sources, file_path):
        # When adding a file to the list of sources, we have to check whether it
        # is already in that list. If it is not, we add it. If it is and has the
        # same version there, everything is fine. However, if it is and has a
        # different version, the file has changed during the process. Using
        # either version would be wrong, so we set the version to the empty
        # string. This will have the consequence that the result will be
        # considered out of date when it is checked next time and a rebuild will
        # be triggered.
        file_version = version_for_file_path(file_path)
        try:
            existing_file_version = sources[file_path]
            if file_version != existing_file_version:
                sources[file_path] = ''
        except KeyError:
            sources[file_path] = file_version

    def _compile_data(self, system_id, preceding_data):
        data = {}
        sources = {}
        # First, we have to process the top file to find the initial list of
        # files that we have to process.
        self._add_to_sources(sources, self._top_file)
        data_files = self._process_top(system_id, preceding_data)
        # We process each of the files that were listed in top.yaml.
        data = self._process_data_files(
            sources, ['top file'], data_files, system_id, preceding_data)
        return (data, sources)

    def _expression_matches(self, target_expression, system_id):
        if not isinstance(target_expression, str):
            raise TypeError(
                'Invalid target expression in {0}: Expected a string, but got '
                'an object of type {1}.'.format(
                    self._top_file, type(target_expression).__name__))
        return vinegar.utils.system_matcher.match(system_id, target_expression)

    def _is_cache_item_current(self, cache_item, preceding_data_version):
        # If the supplied preceding data has changed, we have to recompile.
        if cache_item['preceding_data_version'] != preceding_data_version:
            return False
        # We check whether one of the source files has changed. We can only use
        # the data from the cache if all source files are still the same.
        for source_file, source_version in cache_item['sources'].items():
            if (version_for_file_path(source_file) != source_version):
                return False
        return True

    def _process_data_file(
            self,
            sources,
            parent_files,
            file_name,
            file_path,
            system_id,
            preceding_data):
        # If a file recursively includes itself (directly or indirectly), we end
        # up in an infinite loop, so we have to detect such a situation.
        if file_name in parent_files:
            file_index = parent_files.index(file_name)
            include_chain = ' -> '.join(parent_files[file_index:] + [file_name])
            raise RuntimeError(
                'Recursion loop detected in file {0}: The file is included by '
                'itself through the following chain: {1}'.format(
                    file_name, include_chain))
        self._add_to_sources(sources, file_path)
        try:
            file_yaml = self._render(file_path, system_id, preceding_data)
            file_data = yaml.safe_load(file_yaml)
        except Exception as e:
            raise RuntimeError(
                'Error processing data file {0}.'.format(file_name)) from e
        if not isinstance(file_data, collections.abc.Mapping):
            raise TypeError(
                'File {0} does not contain a dictionary as its top '
                'structure.'.format(file_name))
        # If the file does not include any other files, we can simply return its
        # data.
        if not 'include' in file_data:
            return file_data
        # If the includes come first, we can use a simplified approach for the
        # merging.
        if next(iter(file_data.keys())) == 'include':
            include_files = file_data['include']
            include_data = self._process_data_files(
                sources,
                parent_files + [file_name],
                include_files,
                system_id,
                preceding_data)
            # We have to remove the "include" key so that it does not appear in
            # the merge data.
            del file_data['include']
            return merge_data_trees(
                include_data,
                file_data,
                merge_lists=self._merge_lists,
                merge_sets=self._merge_sets)
        # If the includes come somewhere in the middle of the file, we have to
        # split the data between the part that comes before the includes and the
        # part that comes after the includes.
        data_before = OrderedDict()
        data_after = OrderedDict()
        before_include = True
        for key, value in file_data.items():
            if key == 'include':
                include_data = self._process_data_files(
                    sources,
                    parent_files + [file_name],
                    value,
                    system_id,
                    preceding_data)
                data_before = merge_data_trees(
                    data_before,
                    include_data,
                    merge_lists=self._merge_lists,
                    merge_sets=self._merge_sets)
                before_include = False
            elif before_include:
                data_before[key] = value
            else:
                data_after[key] = value
        return merge_data_trees(
            data_before,
            data_after,
            merge_lists=self._merge_lists,
            merge_sets=self._merge_sets)

    def _process_data_files(
            self,
            sources,
            parent_files,
            file_list,
            system_id,
            preceding_data):
        if not isinstance(file_list, collections.abc.Sequence):
            raise TypeError(
                'Malformed file list in {0}: Found an object of type {1} '
                'where a list was expected.'.format(
                    parent_files[-1], type(file_list).__name__))
        data_files = []
        for file_name in file_list:
            if not isinstance(file_name, str):
                raise TypeError(
                    'Malformed file list in {0}: Found an object of type {1} '
                    'where a string was expected.'.format(
                        parent_files[-1], type(file_name).__name__))
            # Files are specified in the form module1.module2.file, which has
            # to be translated to a path in the form
            # ${root}/module1/module2/file.yaml. However, the same specification
            # could also refer to ${root}/module1/module2/file/init.yaml, we try
            # the first one first and if that is not found, we look for the
            # second one.
            file_path_segments = file_name.split('.')
            file_path = self._root_dir_path
            while file_path_segments:
                file_path = file_path / file_path_segments.pop(0)
            # Look for a YAML file with the name:
            file_path_yaml = file_path.with_suffix('.yaml')
            if file_path_yaml.exists():
                data_files.append(
                    (file_name, os.path.abspath(file_path_yaml.as_posix())))
            else:
                file_path_init_yaml = file_path / 'init.yaml'
                if file_path_init_yaml.exists():
                    data_files.append(
                        (file_name,
                            os.path.abspath(file_path_init_yaml.as_posix())))
                else:
                    raise FileNotFoundError(
                        'File {0} included by {1} could not be found.'
                        .format(file_name, parent_files[-1]))
        data = {}
        for data_file_name, data_file in data_files:
            # When processing the data file, we get the data provided by the
            # file. We pass the list of source files so that additional files
            # included by the data file can be added to the list.
            data_file_data = self._process_data_file(
                sources,
                parent_files,
                data_file_name,
                data_file,
                system_id,
                preceding_data)
            # We merge the file's data into the data that we already have from
            # processing earlier files.
            data = merge_data_trees(
                data,
                data_file_data,
                merge_lists=self._merge_lists,
                merge_sets=self._merge_sets)
        return data

    def _process_top(self, system_id, preceding_data):
        if not pathlib.Path(self._top_file).exists():
            raise FileNotFoundError(
                'Could not find top.yaml in {0}.'.format(
                    self._root_dir_path.as_posix()))
        try:
            top_yaml = self._render(self._top_file, system_id, preceding_data)
            top_data = yaml.safe_load(top_yaml)
        except Exception as e:
            raise RuntimeError('Error processing top file.') from e
        if top_data is None:
            # If the top data is empty, this is most likely an error, however
            # when using Jinja in the top file, it could be that it is by
            # intention, so we allow to disable this error through a
            # configuration option.
            if self._allow_empty_top:
                return []
            else:
                raise TypeError(
                    'Top file is empty. This is most likely an error. If not, '
                    'set the allow_empty_top configuration option to True, to '
                    'disable this exception.')
        if not isinstance(top_data, collections.abc.Mapping):
            raise TypeError(
                'Top file does not contain a dictionary as its top structure.')
        data_files = []
        for target_expression, file_list in top_data.items():
            if not isinstance(file_list, collections.abc.Sequence):
                raise TypeError(
                    'Malformed file list in {0}: Found an object of type {1} '
                    'where a list was expected.'.format(
                        self._top_file, type(file_list).__name__))
            if self._expression_matches(target_expression, system_id):
                data_files += file_list
            pass
        return data_files

    def _render(self, template_path, system_id, preceding_data):
        context = {
            'id': system_id,
            'data': SmartLookupOrderedDict(preceding_data)}
        if self._template_engine is None:
            with open(template_path, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            return self._template_engine.render(template_path, context)

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
