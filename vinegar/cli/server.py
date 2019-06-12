"""
Vinegar server daemon.

If executed as a Python script, this module starts a Vinegar server, looking for
a configuration file in ``/etc/vinegar/vinegar-server.yaml``.

The path to the configuration file can be overridden through the
``--config-file`` command line argument.

Instead of executing this module as a script, it can be imported and its
`run_server` function can be used to start the server. In this case, the
configuration is expected to be passed to `run_server` in the form of a
dictionary.

The configuration file uses the YAML syntax and has the following keys (all of
them are optional):

:``data_sources``:
    List of data sources. Each item in the list must be a dictionary. This
    dictionary must have a key ``name`` that specifies the type of the data
    source. Please refer to the documentation of
    `vinegar.data_source.get_data_source` to learn more about how the name is
    resolved. All other keys are used for the configuration dictionary that is
    passed to the data source. It is perfectly legal to use multiple data
    sources with the same name, but having a different configuration. Please
    refer to the documentation of the data sources to learn more about the
    configuration options for each data sources. The resulting list of data
    sources is passed to `~vinegar.data_source.get_composite_datasource` in
    order to create a single data source that combines them all. The behavior
    of the compositve data source is also controlled by the
    ``data_sources_merge_lists`` option.

:``data_sources_merge_lists``:
    Flag controlling the behavior of the composite data source that is created
    for the list of ``data_sources``. The composite data source merges the data
    returned by each data source with the data from the previous data sources.
    This happens by merging mappings, preserving keys that are present in the
    previous data, but not in the data from the next data source. This process
    also applies to nested mappings. If ``data_sources_merge_lists`` is set to
    ``True``, sequences are also merged, meaning that elements that are not
    present in the list in the previous data are added to the list. If ``False``
    (the default), sequences replace each other, removing all elements that were
    only present in the previous data.

:``data_sources_merge_sets``:
    Flag controlling the behavior of the composite data source that is created
    for the list of ``data_sources``. The composite data source merges the data
    returned by each data source with the data from the previous data sources.
    This happens by merging mappings, preserving keys that are present in the
    previous data, but not in the data from the next data source. This process
    also applies to nested mappings. If ``data_sources_merge_sets`` is set to
    ``True`` (the default), sets are also merged, meaning that the resulting set
    is the union of the set in the previous data and the set returned by the
    data source. If ``False``, sets replace each other, removing all elements
    that were only present in the previous data.

:``http``:
    Dictionary of configuration options for the HTTP server. The options are
    passed on to `vinegar.server.http.create_http_server`. The only exception
    is the ``request_handlers`` option. That option expects a list, where each
    item is a dictionary. This dictionary must have a key ``name`` that
    specifies the type of the request handler. Please refer to the documentation
    of `vinegar.request_handler.get_http_request_handler` to learn more about
    how the name is resolved. All other keys are used for the configuration
    dictionary that is passed to the request handler. It is perfectly legal to
    use multiple request handlers with the same name, but having a different
    configuration. Please refer to the documentation of the request handlers to
    learn more about the configuration options for each request handler.

:``logging_config_file``:
    Path to a logging configuration file. This file must be in the
    `format <https://docs.python.org/3/library/logging.config.html#logging-config-fileformat>`_
    expected by ``logging.config.fileConfig``. This configuration option cannot
    be used together with the ``logging_level`` option.

:``logging_level``:
    Logging level to be used. Can be one of ``CRITICAL``, ``ERROR``, ``WARN``,
    ``INFO`` (the default), or ``DEBUG``. This configuration option cannot be
    used together with the ``logging_config_file`` option.

:``tftp``:
    Dictionary of configuration options for the TFTP server. The options are
    passed on to `vinegar.server.tftp.create_tftp_server`. The only exception
    is the ``request_handlers`` option. That option expects a list, where each
    item is a dictionary. This dictionary must have a key ``name`` that
    specifies the type of the request handler. Please refer to the documentation
    of `vinegar.request_handler.get_tftp_request_handler` to learn more about
    how the name is resolved. All other keys are used for the configuration
    dictionary that is passed to the request handler. It is perfectly legal to
    use multiple request handlers with the same name, but having a different
    configuration. Please refer to the documentation of the request handlers to
    learn more about the configuration options for each request handler.
"""

import argparse
import collections.abc
import logging
import logging.config
import os.path
import signal
import sys
import threading
import typing

import vinegar.data_source
import vinegar.http.server
import vinegar.request_handler
import vinegar.tftp.server
import vinegar.version

from vinegar.utils import oyaml as yaml

def main():
    """
    Run Vinegar server.

    This function parses the command-line arguments, calls
    `reader_server_config`, and subsequently calls `run_server`.
    """
    parser = argparse.ArgumentParser(description='Run the Vinegar server.')
    parser.add_argument(
        '--config-file',
        dest='config_file',
        help='path to the configuration file')
    parser.add_argument(
        '--version',
        action='store_true',
        dest='version',
        help='show program\'s version number and exit')
    args = parser.parse_args()
    if args.version:
        print('Vinegar server %s' % vinegar.version.version_string)
        sys.exit(0)
    config_file = args.config_file
    config = read_server_config(config_file)
    run_server(config)

def read_server_config(
        config_file: str = None) -> typing.Mapping[str, typing.Any]:
    """
    Read the server configuration.

    If the configurtion file cannot be read (because it does not exist,
    permissions are insufficient, or it is not a valid YAML file), an exception
    is raised.

    The returned object can then be passed to `run_server`.

    :param config_file:
        path to the configuration file. If ``None`` a platform specifc default
        value is used.
    :return:
        configuration read from the file.
    """
    if (config_file == None):
        if sys.platform == 'win32':
            config_file = 'C:\\Vinegar\\conf\\vinegar-server.yaml'
        else:
            config_file = '/etc/vinegar/vinegar-server.yaml'
    with open(config_file, mode='r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    if config is None:
        config = {}
    return config

def run_server(config: typing.Mapping[str, typing.Any]) -> None:
    """
    Run the Vinegar server.

    This function only returns when it is interrupted from the keyboard or when
    the process receives a ``SIGTERM``.

    This function raises an exception if the configuration object is invalid or
    if the server cannot be started.

    :param config:
        configuration object used by the server. Please refer to the
        `module documentation <vinegar.cli.server>` for a description of the
        structure of the configuration object.
    """
    # We configure the logging first. This way, we can log any error that
    # occurs during startup.
    if 'logging_config_file' in config:
        if 'logging_level' in config:
            raise ValueError(
                'Only one of the logging_config_file and logging_level option '
                'can be used.')
        logging.config.fileConfig(
            config['logging_config_file'], disable_existing_loggers=False)
    else:
        logging_level = config.get('logging_level', 'INFO')
        if logging_level not in (
                'CRITICAL', 'DEBUG', 'ERROR', 'INFO', 'WARNING'):
            raise ValueError(
                'Invalid logging_level "%s". Must be one of CRITICAL, DEBUG, '
                'ERROR, INFO, WARNING.' % logging_level)
        logging_level = getattr(logging, logging_level)
        logging.basicConfig(level=logging_level)
    try:
        _run_server_internal(config)
    except:
        logging.getLogger(__name__).exception('Server startup failed.')
        # We still raise the exception so that it is printed to the output.
        raise

def _run_server_internal(config):
    """
    Actually starts the server.

    This has been separated into its own function called by run_server so that
    exceptions during startup can be caught and logged.
    """
    if not isinstance(config, collections.abc.Mapping):
        raise TypeError(
            'Configuration object must be a mapping, but got an object of type '
            '\'%s\'.' % type(config).__name__)
    # Configure data sources.
    data_sources = []
    data_source_configs = config.get('data_sources', [])
    if not isinstance(data_source_configs, collections.abc.Sequence):
        raise TypeError(
            'Expected a list for the data_sources key, but found an object of '
            'type \'%s\'.' % type(data_source_configs).__name__)
    for data_source_config in data_source_configs:
        if not isinstance(data_source_config, collections.abc.Mapping):
            raise TypeError(
                'Expected a dictionary for the items in the data_sources list, '
                'but found an object of type \'%s\'.'
                % type(data_source_configs).__name__)
        if 'name' not in data_source_config:
            raise KeyError('Data source configuration must have a name.')
        data_sources.append(
            vinegar.data_source.get_data_source(
                data_source_config['name'], data_source_config))
    data_sources_merge_lists = config.get('data_sources_merge_lists', False)
    data_sources_merge_sets = config.get('data_sources_merge_sets', True)
    data_source = vinegar.data_source.get_composite_data_source(
        data_sources, data_sources_merge_lists, data_sources_merge_sets)
    # Configure the HTTP server.
    http_config = config.get('http', {})
    if not isinstance(http_config, collections.abc.Mapping):
        raise TypeError(
            'Expected a dictionary for the http key, but found an object of '
            'type \'%s\'.' % type(http_config).__name__)
    http_request_handlers = []
    request_handler_configs = http_config.get('request_handlers', [])
    if not isinstance(request_handler_configs, collections.abc.Sequence):
        raise TypeError(
            'Expected a list for the http:request_handlers key, but found an '
            'object of type \'%s\'.' % type(request_handler_configs).__name__)
    for request_handler_config in request_handler_configs:
        if not 'name' in request_handler_config:
            raise KeyError('Request handler configuration must specify a name.')
        request_handler = vinegar.request_handler.get_http_request_handler(
            request_handler_config['name'],
            request_handler_config)
        # A request handler might be DataSourceAware.
        vinegar.data_source.inject_data_source(request_handler, data_source)
        http_request_handlers.append(request_handler)
    # We want to use every option except for the request_handlers as an argument
    # to create_http_server. It is not an error if there is no request_handlers
    # key at all.
    try:
        del http_config['request_handlers']
    except KeyError:
        pass
    http_server = vinegar.http.server.create_http_server(
        http_request_handlers, **http_config)
    # Configure the TFTP server.
    tftp_config = config.get('tftp', {})
    if not isinstance(tftp_config, collections.abc.Mapping):
        raise TypeError(
            'Expected a dictionary for the tftp key, but found an object of '
            'type \'\'.' % type(tftp_config).__name__)
    tftp_request_handlers = []
    request_handler_configs = tftp_config.get('request_handlers', [])
    if not isinstance(request_handler_configs, collections.abc.Sequence):
        raise TypeError(
            'Expected a list for the tftp:request_handlers key, but found an '
            'object of type \'\'.' % type(request_handler_configs).__name__)
    for request_handler_config in request_handler_configs:
        if not 'name' in request_handler_config:
            raise KeyError('Request handler configuration must specify a name.')
        request_handler = vinegar.request_handler.get_tftp_request_handler(
            request_handler_config['name'],
            request_handler_config)
        # A request handler might be DataSourceAware.
        vinegar.data_source.inject_data_source(request_handler, data_source)
        tftp_request_handlers.append(request_handler)
    # We want to use every option except for the request_handlers as an argument
    # to create_tftp_server. It is not an error if there is no request_handlers
    # key at all.
    try:
        del tftp_config['request_handlers']
    except KeyError:
        pass
    tftp_server = vinegar.tftp.server.create_tftp_server(
        tftp_request_handlers, **tftp_config)
    # We want to shut the server down when we receive a keyboard interrupt
    # (triggered by hitting Ctrl+C / SIGINT) or a SIGTERM.
    shutdown_event = threading.Event()
    signal.signal(signal.SIGTERM, lambda signum, frame: shutdown_event.set())
    print('Press Ctrl+C to stop the server.', file=sys.stderr)
    try:
        # Start the servers.
        http_server.start()
        tftp_server.start()
        shutdown_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        http_server.stop()
        tftp_server.stop()

if __name__ == '__main__':
    main()
