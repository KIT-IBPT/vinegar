"""
Data source backed by a text file.

This data source is designed to work with any text file, where there is a line
for each system. The exact format of the file can be configured through the use
of regular expressions.

This data source supports the `~DataSource.find_sytem` method, which makes it
perfect for being used as the root source that defines the list of existing
systems.

.. _specify_file_format:

Specifying the file format
--------------------------

This section only describes the options related to the file format. For a full
list of supported options, please refer to :ref:`config_options`. For an
example configuration, please refer to :ref:`config_example`.

The centerpiece of the file format configuration is a regular expression that
defines the format of a single line in the file. This regular expression is
specified through the ``regular_expression`` option. This regular expression
must match the *full* line (the pattern is matched using ``fullmatch``).
Consequently, there is no need to use start of string or end of string anchors.

This regular expression has to define groups that represent the various pieces
of data. Both regular groups (identified by their index) and named groups
(``(?P<...>`` syntax) can be used.

Often, it is desirable to ignore certain lines (e.g. empty lines or lines
representing comments). This can be achieved through the
``regular_expression_ignore`` option. If a line matches that expression, it is
ignored entirely, without even a warning message being logged. Again, the
regular expression has to match the full line.

For each line, the system ID has to be extracted and at least one associated
piece of data has to be extract. This both works through the same mechanism: A
configuration that refers to one of the groups defined in the regular expression
matching the line.

The configuration for extracting the system ID is specified through the
``system_id`` configuration option. The configuration for extracting pieces of
data is specified through the ``variables`` option.

There are two differences between the two: First, the ``variables`` option is
actually a ``dict`` where each key is the name of the corresponding key that is
included in the data tree and the value is the configuration for extract that
piece of data. Second, the configuration for the system ID must never result in
a value of ``None`` being extracted.

The keys in the ``dict`` of the ``variables`` option can define a hierarchy.
That hierarchy is specified by using the colon (``:``) in keys. Each key is
split at these colons and the components are used as keys into nested instances
of ``dict``.

Each of the configurations for extracting a piece of data is itself a ``dict``
that has the following keys:

:``source`` (mandatory):
    The name (as a ``str``) or index (as an ``int``) of the group in the regular
    expression that provides this piece of data.

:``transform`` (optional):
    A list defining the transformations that shall be applied to the string
    extracted through the regular expression. This list is passed to
    `vinegar.transform.apply_transformation_chain`. If this list is empty (the
    default), no transformations are applied and the string extracted by the
    regular expression is used as is.

:``transform_none_value`` (optional):
    A ``bool`` defining whether a value of ``None`` should still be transformed.
    As most transformation functions do not support ``None`` values, the default
    is ``False``. If setting this option to ``True`` one has to ensure that only
    transformation functions that can handle a value of ``None`` are used. The
    value extracted from a line can be ``None`` if the corresponding capturing
    group in the regular expression is optional.

:``use_none_value`` (optional):
    A ``bool`` defining whether a value of ``None`` (possibly as a result of the
    transformations) should still result in the corresponding key being added to
    the data tree. Usually, there is no sense in adding a key without a value,
    so this option has a default value of ``False``. Please note that his option
    does not have any effects when being specified in the configuration for the
    ``system_id``. The system ID is mandatory and thus a system ID of ``None``
    is treated as an error. This should be avoided by ensuring that the group
    capturing the system ID is non-optional.

It might be that a file contains some lines that do not match the expected
format (as specified by ``regular_expression``), but are not lines that shall be
ignored (as specified by ``regular_expression_ignore``) either. The
``mismatch_action`` option defines how to deal with those lines. By default, a
warning is logged when such a line is encountered. This can be changed to
raising an exception by setting ``mismatch_action`` to ``error``. Such lines can
also be ignored completely (without logging a warning), by setting
``mismatch_action`` to ``ignore``.

If there is more than one line specifying the same system ID, the behavior is
controlled by the ``duplicate_system_id_action`` option. By default, a warning
is logged and only the first line for the system ID is used (option value
``warn_ignore``). This can be changed to raising an exception by setting the
option to ``error``. If the option is set to ``ignore``, only the first line is
used, but no warning message is logged.

.. _config_example:

Configuration example
---------------------

In order to get a better understanding of how the various configuration options
work together, let us discuss the following example (in this example, we use
YAML for describing the configuration):

.. code-block:: yaml

    # The cache is enabled by default, so we only specify it here for
    # completeness.
    cache_enabled: True
    # The warn action is already the default, we only specify it here for
    # completeness.
    duplicate_system_id_action: warn
    # This is the path to the text file.
    file: /path/to/file.txt
    # Enabling find_first_match has the effect that if multiple systems use the
    # same value for a key (as defined in the variable dict), the first of the
    # systems (the first line) is returned by the find_system method when
    # looking for that specific key-value combination. If this option is not
    # enabled, no system is returned if there is no unique match.
    find_first_match: True
    # The warn action is already the default, we only specify it here for
    # completeness.
    mismatch_action: warn
    # This is the regular expression that matches the lines that we want to use.
    # We specify the X flag first (?x) so that we can use the multi-line syntax,
    # which makes the regular expression much more readable.
    regular_expression: |
        (?x)
        # We expect a CSV file with three columns that are separated by
        # semicolons.
        # The first column specifies the MAC address.
        (?P<mac>[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5});
        # The second column specifies the IP address.
        (?P<ip>[0-9]{1,3}(?:\.[0-9]{1,3}){3});
        # The third column specifies the hostname and an optional list
        # of additional names.
        (?P<hostname>[^,]+)
        (,(?P<extra_names>.+))?
    # We want to ignore empty lines and lines starting with a "#".
    regular_expression_ignore: "|(?:#.*)"
    # We build the system ID from the hostname by adding a domain name and
    # ensuring that everything is in lower case.
    system_id:
        source: hostname:
        transform:
            - string.add_suffix: .mydomain.example.com
            - string.to_lower
    # We define a couple of variables that will be available in the data tree
    # for each system.
    variables:
        'info:extra_names':
            source: extra_names
            transform:
                - string.to_lower
                # Please not that we could also write this shorter as
                # "- string.split: ." because "sep" is the first argument (after
                # the value) and "maxsplit" defaults to -1.
                - string.split:
                    sep: .
                    maxsplit: -1
        'net:fqdn':
            source: hostname
            transform:
                - string.add_suffix: .mydomain.example.com
                - string.to_lower
        'net:hostname':
            source: hostname
            transform:
                - string.to_lower
        'net:ipv4_addr':
            source: ip
            transform:
                - ipv4_address.normalize
        'net:mac_addr':
            source: mac
            transform:
                # The colon is the default delimiter, so we could also simply
                # write "- mac_address.normalize" without specifying any
                # options.
                - mac_address.normalize:
                    delimiter: colon

Now, let us assume we have the following text file::

    02:00:00:00:00:01;192.168.0.1;System1
    02:00:00:00:00:02;192.168.0.2;system2,alias1,Alias2
    02:00:00:00:00:0a;192.168.000.3;system3
    02:00:00:00:00:0A;192.168.0.4;system4

Parsing this file with the configuration specified earlier, would result in the
following data for the systems (we list the data in YAML format and use the
system IDs as the keys in the top ``dict``):

.. code-block:: yaml

    system1.mydomain.example.com:
        net:
            fqdn: system1.mydomain.example.com:
            hostname: system1
            ipv4_addr: 192.168.0.1
            mac_addr: '02:00:00:00:00:01'

    system2.mydomain.example.com:
        info:
            extra_names:
                - alias1
                - alias2
        net:
            fqdn: system2.mydomain.example.com:
            hostname: system2
            ipv4_addr: 192.168.0.2
            mac_addr: '02:00:00:00:00:02'

    system3.mydomain.example.com:
        net:
            fqdn: system3.mydomain.example.com:
            hostname: system3
            ipv4_addr: 192.168.0.3
            mac_addr: '02:00:00:00:00:0A'

    system4.mydomain.example.com:
        net:
            fqdn: system4.mydomain.example.com:
            hostname: system4
            ipv4_addr: 192.168.0.4
            mac_addr: '02:00:00:00:00:0A'

Thanks to the transformations, all names have been converted to lower case and
IP and MAC addresses have been normalized.

With this data, it is possible to look up systems through
`~TextFileDataSource.find_system`. For example
``find_system('net:mac_addr', '02:00:00:00:00:0A')``, will return
``system3.mydomain.example.com``. This works because the look-up is done on the
final (transformed) data and the ``find_first_match`` configuration option has
been enabled. If it had not been enabled, the result would be ``None`` because
``system4.mydomain.example.com`` has the same MAC address.

.. _config_options:

Configuration options
---------------------

This data source has several configuration options that can be used to control
its behavior. This section only gives an overview of the available options. For
a more detailed discussion about the options controlling the file format, please
refer to :ref:`specify_file_format` and :ref:`config_example`.

:``file`` (mandatory):
    Path to the text file (as a ``str``).

:``regular_expression`` (mandatory):
    Regular expression (as a ``str``) matching the data lines in the file. This
    regular expression must match the *full* line (the pattern is matched using
    ``fullmatch``). Consequently, there is no need to use start of string or end
    of string anchors. The regular expression must define catching groups that
    can then be referenced from the ``system_id`` and ``variables``
    configuration. See :ref:`specify_file_format` for details.

:``system_id`` (mandatory):
    Configuration describing how the system ID is extracted from a line.
    This configuration refers to a catching group of ``regular_expression``
    through its ``source`` option. See :ref:`specify_file_format` for details.

:``variables`` (mandatory):
    Configuration describing how the various data itmes are extracted from a
    line. This configuration option expects a ``dict`` where each key-value pair
    refers to one data item, using the key as the key in the data tree generated
    for the system and the value as the configuration for that data item. See
    :ref:`specify_file_format` for details.

:``cache_enabled`` (optional):
    If ``True`` (the default), the contents of the text file are read once and
    cached until the file changes. File changes are detected through the
    time-stamp of the file. If ``False`` the file is read and parsed every time
    `~TextFileDataSource.find_system()` or `~TextFileDataSource.get_data()` is
    called.

:``duplicate_system_id_action`` (optional):
    If ``warn`` (the default), a warning message is logged when a line
    specifying the same system ID as an earlier line is encountered and the
    second line is ignored. If ``error`` a ``ValueError`` is raised instead. If
    ``ignore`` the second line is ignored without logging a warning.

:``find_first_match`` (optional):
    If ``True`` and there are multiple matches in a call to
    `~TextFileDataSource.find_system()`, the first system ID (this is the ID
    of the first system in the file that matches the specified query) is
    returned. If ``False`` (the default), no system ID is returned if there are
    multiple matches, so a system ID is only returned if there is only one
    system matching the query.

:``mismatch_action`` (optional):
    Controls the behavior when a line that matches neither
    ``regular_expression`` nor ``regular_expression_ignore`` is encountered. If
    ``warn`` (the default), a warning message is logged. If ``error`` a
    ``ValueError`` is raised instead. If``ignore`` the line is ignored without
    logging a warning.

:``regular_expression_ignore`` (optional):
    Regular expression (as a ``str``) matching the lines in the file that shall
    be ignored. This regular expression must match the *full* line (the pattern
    is matched using ``fullmatch``). Consequently, there is no need to use start
    of string or end of string anchors. If ``None`` (the default), no lines are
    ignored.
"""

import logging
import re
import threading

from typing import Any, Mapping, Tuple

from vinegar.data_source import DataSource
from vinegar.transform import apply_transformation_chain
from vinegar.utils.odict import OrderedDict
from vinegar.utils.version import version_for_file_path, version_for_str

# Logger used by this module.
logger = logging.getLogger(__name__)

class TextFileSource(DataSource):
    """
    Data source that reads data from a text file.

    For information about the configuration options supported by this data
    source, please refer to the
    `module documentation <vinegar.data_source.text_file>`.
    """
    
    def __init__(self, config: Mapping[Any, Any]):
        """
        Create a text file data source using the specified configuration.

        :param config:
            configuration for this data source. Please refer to the
            `module documentation <vinegar.data_source.text_file>` for a list of
            supported options.
        """
        self._cache_enabled = config.get('cache_enabled', True)
        self._duplicate_system_id_action = config.get(
            'duplicate_system_id_action', 'warn')
        if self._duplicate_system_id_action not in ('error', 'ignore', 'warn'):
            raise ValueError(
                'Invalid value "{0}" for option duplicate_system_id_action. '
                'Allowed values are "error", "ignore" and "warn".'.format(
                    self._duplicate_system_id_action))
        self._file = config['file']
        self._find_first_match = config.get('find_first_match', False)
        self._mismatch_action = config.get('mismatch_action', 'warn')
        if self._mismatch_action not in ('error', 'ignore', 'warn'):
            raise ValueError(
                'Invalid value "{0}" for option mismatch_action. Allowed '
                'values are "error", "ignore", and "warn".'.format(
                    self._mismatch_action))
        self._regular_expression = re.compile(config['regular_expression'])
        regular_expression_ignore_text = config.get(
            'regular_expression_ignore', None)
        if regular_expression_ignore_text is None:
            self._regular_expression_ignore = None
        else:
            self._regular_expression_ignore = re.compile(
                regular_expression_ignore_text)
        self._system_id_config = config['system_id']
        self._variables_config = config['variables']
        self._file_version = ''
        self._lock = threading.Lock()

    def find_system(self, lookup_key: str, lookup_value: Any) -> str:
        # We need the lock to ensure that we do not access the data while
        # another thread updates it.
        with self._lock:
            self._update_data()
            # We have to deal with non-hashable values differently. We expect
            # that look-ups for such values are rare, so that we can live with
            # a less efficient implementation.
            try:
                hash(lookup_value)
                value_hashable = True
            except TypeError:
                value_hashable = False
            if value_hashable:
                system_list = self._key_value_index.get(
                    (lookup_key, lookup_value), None)
            else:
                potential_system_list = \
                    self._key_value_not_hashable_index.get(lookup_key)
                system_list = [
                    system_id
                    for system_id, value in potential_system_list
                    if value == lookup_value]
            # If there key/value combination is not in the index, there is no
            # matching system.
            if system_list is None:
                return None
            # If the combination is in the index, there is at least one system,
            # but there could be more than one. In the latter case, we only
            # return the first system if the find_first_match configuration
            # option is set.
            if len(system_list) == 1 or self._find_first_match:
                return system_list[0]
            else:
                return None

    def get_data(
            self,
            system_id: str,
            preceding_data: Mapping[Any, Any],
            preceding_data_version: str) -> Tuple[Mapping[Any, Any], str]:
        with self._lock:
            self._update_data()
            data = self._system_data.get(system_id, {})
            version = self._system_version.get(system_id, '')
        return data, version

    def _process_variable(self, config, match, optional=True):
        # The group index can be an integer number or a name.
        group_index = config['source']
        value = match.group(group_index)
        if value is None:
            transform_none_value = config.get('transform_none_value', False)
            if not optional and not transform_none_value:
                raise ValueError(
                    'Regular expression group {0} has no value.'.format(
                        group_index))
            # Usually, we do not transform a value of None, unless it is
            # requested explicitly.
            if not transform_none_value:
                return None
        # Now we apply the transformations.
        transformations = config.get('transform', [])
        value = apply_transformation_chain(transformations, value)
        if value is None and not optional:
            raise ValueError(
                'Regular expression group {0} has no value.'.format(
                    group_index))
        return value

    def _update_data(self):
        # This method is only called while holding the lock.
        # If the cache is enabled and the file has not been changed since we
        # read it the last time, we consider the data up to date and return.
        if self._cache_enabled:
            current_file_version = version_for_file_path(self._file)
            if current_file_version == self._file_version:
                return
        # Before reading the new data, we have to clear our internal cache of
        # the data.
        self._file_version = ''
        self._system_data = {}
        self._system_version = {}
        self._key_value_index = {}
        self._key_value_not_hashable_index = {}
        # We keep the line number for each system locally so that we can
        # generate a better error message in case the same system ID is used
        # more than once.
        system_line_no = {}
        with open(self._file, newline='') as file:
            line_no = 0
            for line in file:
                line_no += 1
                # We trim the trailing end of line characters (but no other
                # whitespace characters).
                while line.endswith('\r') or line.endswith('\n'):
                    line = line[:-1]
                # If an ignore regular expression is configured and it matches
                # the line, we ignore that line.
                if (self._regular_expression_ignore is not None
                        and self._regular_expression_ignore.fullmatch(line)
                        is not None):
                    continue
                match = self._regular_expression.fullmatch(line)
                # If the line does match the regular expression, the next action
                # depends on the configured mismatch_action.
                if match is None:
                    if self._mismatch_action == 'error':
                        raise ValueError(
                            'Error while parsing file {0} line {1}: "{2}" does '
                            'not match the specified format.'.format(
                                self._file, line_no, line))
                    elif self._mismatch_action == 'ignore':
                        continue
                    elif self._mismatch_action == 'warn':
                        logger.warning(
                            'Error while parsing file %s line %d: "%s" does '
                            'not match the specified format.',
                            self._file,
                            line_no,
                            line)
                        continue
                    else:
                        raise RuntimeError(
                            'Invalid mismatch action: {0}'.format(
                                self._mismatch_action))
                # First, we process the system ID. The system ID is always
                # needed, so it has a separate configuration.
                system_id = self._process_variable(
                    self._system_id_config, match, optional=False)
                if system_id is None:
                    raise ValueError(
                        'Error while parsing {0} line {1}: Line does not '
                        'specify a system ID: {2}'.format(
                            self._file, line_no, line))
                if system_id in self._system_data:
                    if self._duplicate_system_id_action == 'error':
                        raise ValueError(
                            'Error while parsing file {0} line {1}: System ID '
                            '"{2}" is already specified in line {3}.'.format(
                                self._file,
                                line_no,
                                system_id,
                                system_line_no[system_id]))
                    elif self._duplicate_system_id_action == 'ignore':
                        continue
                    elif self._duplicate_system_id_action == 'warn':
                        logger.warning(
                            'Duplicate system ID in file %s line %d: System ID '
                            '"%s" is already specified in line %d. Ignoring line %d',
                            self._file,
                            line_no,
                            system_id,
                            system_line_no[system_id],
                            line_no)
                        continue
                    else:
                        raise RuntimeError(
                            'Invalid mismatch action: {0}'.format(
                                self._mismatch_action))
                # Next we generate the data for the system by processing each
                # of the specified variable definitions.
                data = OrderedDict()
                for key, var_config in self._variables_config.items():
                    value = self._process_variable(var_config, match)
                    # If the variable does not specify add_none_value = True, we
                    # do not add such a value.
                    if (value is None
                            and not var_config.get('use_none_value', False)):
                        continue
                    # The key can have multiple hierarchy levels that are
                    # separated by colons. In this case, we generate dicts for
                    # each but the last level in the hierarchy.
                    target_dict = data
                    key_components = key.split(':')
                    for key_component in key_components[:-1]:
                        target_dict = target_dict.setdefault(
                            key_component, OrderedDict())
                    target_dict[key_components[-1]] = value
                    # We also add the key-value pair to the index, so that the
                    # system can be found.
                    # We have to deal with values that are not hashable
                    # (e.g. lists). We assume that such values will rarely be
                    # used in look-ups, so we simply use a separate dict for
                    # them where we iterate over all possible values.
                    try:
                        hash(value)
                        value_hashable = True
                    except TypeError:
                        value_hashable = False
                    if value_hashable:
                        key_value_system_list = \
                            self._key_value_index.setdefault(
                                (key, value), [])
                        key_value_system_list.append(system_id)
                    else:
                        key_value_system_list = \
                            self._key_value_not_hashable_index.setdefault(
                                key, [])
                        key_value_system_list.append((system_id, value))
                self._system_data[system_id] = data
                self._system_version[system_id] = version_for_str(line)
                system_line_no[system_id] = line_no
        # If the cache is enabled, we remember the file version for which we
        # read the data. We do this after reading the data because if there is
        # an error, we do not want the cache check to succeed on the next run of
        # this function.
        if self._cache_enabled:
            self._file_version = current_file_version

def get_instance(config: Mapping[Any, Any]) -> TextFileSource:
    """
    Create a text file data source.

    For information about the configuration options supported by that source,
    please refer to the `module documentation <vinegar.data_source.text_file>`.

    :param config:
        configuration for the data source.
    :return:
        text file data source using the specified configuration.
    """
    return TextFileSource(config)
