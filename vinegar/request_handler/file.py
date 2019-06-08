"""
Request handler that serves files from the file systems.

The files can either be served as is or they can be processed through a template
engine. The handler can either work with a single file or with a whole directory
of files.

Optionally, this handler can supply system data from a `DataSource` when
rendering templates. In this case, the request path has to contain a piece of
information that allows for identifying the system. This can either be the
system ID, or a value that allows for looking up the system ID through the
data source's `~DataSource.find_system` method. This is configured through the
`lookup_key` configuration option.

The request handler classes provided by this module implement the
`DataSourceAware` interface in order to get access to the data source. When
using the request handlers in a container context, the container will usually
take care of injecting the data source. When using the classes directly, the
using code has to take care of that. However, a `DataSource` is only needed when
using the ``lookup_key`` configuration option. If that option is empty (the
default), no data source is needed and it is not even used if it is available.

This module provides request handlers for both HTTP and TFTP. These two handlers
are almost identical in their behavior with only a few minor differences:

* The options related to the ``Content-Type`` header are only available in the
  HTTP version. TFTP does not have any equivalent of the ``Content-Type`` header
  in HTTP.
* The TFTP version of the handler allows request paths that do not start with a
  forward slash (``/``). In this case, the forward slash is added automatically.
  The HTTP version of the handler, in contrast, does not do anything like this
  because request paths not starting with a forward slash are rejected by the
  HTTP server component.

By default, this request handler does not process files as templates and treats
them as binary files. However, when enabling templating through the ``template``
option, files are read as text files and decoded as UTF-8. The result of the
rendering process of the template engine is then encoded as UTF-8 before sending
it to the client.

This means that the default value of the ``content_type`` option (only available
in the HTTP version of the handler) depends on whether a template engine is used
or not.

.. _request_path_matching:

Request path matching
---------------------

The request paths for which a handler is used are configured through its
``request_path`` option. The configured request path must always start with a
``/`` and must not end with a ``/`` (the exception being the case where the
whole path just consists of a single ``/``).

When operating in file mode (if the ``file`` configuration option is used), the
request path must be an exact match. For example, the configured request path
``/my/file`` matches the actual request path ``/my/file`` (and ``my/file`` for
TFTP), but it does not match ``/my/file/`` or ``/my/file/abc``. In file mode,
the special request path ``/`` can only be used for the HTTP version of the
handler, not the TFTP one. The reason is that TFTP has no notion of index files
and due to a missing ``/`` being added automatically, such a configuration would
actually match requests with an empty path.

When operating in directory mode (if the ``root_dir`` configuration option is
used), the configured request path specifies the prefix that must match. Extra
portions of the actual request path are treated as the path of the requested
file relative to the ``root_dir``. For example, if ``request_path`` is set to
``/myprefix`` and ``root_dir`` is set to ``/path/on/fs``, a request specifying
the path ``/myprefix/some/file`` would result in the file
``/path/on/fs/some/file`` being served.

A request handler operating in directory mode will catch all requests that start
with the specified prefix, even if the file does not actually exist. This means
that a request handler serving a more specific path prefix has to come earlier
in the chain of request handlers or it will never be asked whether it can handle
a request.

When using the ``lookup_key`` configuration option, the configured request path
has to contain exactly one placeholder. The default placeholder string is
``...``, but this can be changed through the ``lookup_value_placeholder``
configuration option.

When such a configuration is used, the placeholder marks a portion of the
request path that might be different from request to request. For example, a
configured ``request_path`` of ``/prefix/file-...`` will match an actual request
path of ``/prefix/file-abc``, ``/prefix/file-def``, etc. The placeholder will
not match an empty string, so the request path will not match ``/prefix/file-``.

The value that replaces the placeholder in the actual request path is
transformed according to the configuration set through the
``lookup_value_transform`` configuration option and then used to find a system
ID through `DataSource.find_system`. This is most useful when also using a
template engine (see :ref:`using_templates`). If no matching system can be
found, the request file is treated as not existing (unless
``lookup_no_result_action`` is set to ``continue``).

Placeholders do not necessarily have to appear at the end of a request path. For
example, a ``request_path`` of ``/prefix/.../suffix``` will match
``/prefix/abc/suffix``

Placeholders can be used in file mode as well as in directory mode. Like request
paths that do not use place holders, the extra portion of the path will be used
as the path of the file inside the directory, when operating in directory mode.

.. _using_templates:

Using templates
---------------

Optionally, files served by the request handlers can be treated as templates.
This behavior is enabled by setting the ``template`` configuration option to the
name of one of the template engines supported by
`~vinegar.template.get_template_engine`. One good choice might be the ``jinja``
template engine.

If the ``lookup_key`` configuration option is also set, the request handler
provides two context objects to the template engine: The ``id`` object contains
the system ID (as a ``str``) and the ``data`` object contains the data that has
been returned from the data source's `~DataSource.get_data` method. The ``data``
object is passed as a `~vinegar.utils.smart_dict.SmartLookupOrderedDict` to make
it easier to get nested values.

The ``data`` object is not available if the data source's ``get_data`` method
raised an exception. Usually, this will cause the template not even to be
rendered, but this can be overridden through the ``data_source_error_action``
configuration option.

If the data source's `~DataSource.find_system` method returns ``None`` and
``lookup_no_result_action`` is set to ``continue``, neither ``id`` nor ``data``
are available. The same applies if ``find_system`` raises an exception and
``lookup_no_result_action`` is set to ``continue`` and
``data_source_error_action`` is set to ``ignore`` or ``warn``.

.. _config_example:

Configuration example
---------------------

In order to understand how the various configuration options work together, we
look at an example configuration (expressed in YAML):

.. code-block:: yaml

    lookup_key: 'net:mac_addr'
    lookup_no_result_action: continue
    lookup_value_transform:
        - mac_address.normalize
    request_path: '/prefix/...'
    root_dir: '/path/to/the/directory'
    template: jinja

We also assume that there is a file ``/path/to/the/directory/myconf.txt`` with
the following content:

.. code-block:: jinja

    {%- if id is not defined -%}
    This content is for systems which we do not know.
    {%- else -%}
    This system has the ID {{ id }} and the MAC address
    {{ data.get('net:mac_addr') }}.
    {%- endif -%}

When a request for ``/prefix/02-03-04-05-06-0a/myconf.txt`` arrives, the MAC
address in the URL will be extracted and normalized (the ``-`` characters will
be replaced by ``:`` and letters will be converted to upper case). The resulting
value (``02:03:04:05:06:0A``) will be used as a lookup value together and passed
to the data source's ``find_system`` method along with the lookup key
(``net:mac_addr``). Assuming that the data source can resolve this key-value
combination, the returned system ID is used in a call to ``get_data`` and both
the system ID and the data are passed to the template engine when rendering
``myconf.txt``.

As we have set the ``lookup_no_result_action`` to ``continue`` a MAC address
that is not known by the data source will not result in a "not found" error
(status code 404 in the case of HTTP). Instead, the template is rendered without
a system ID and system data, so that some default content is returned.

Configuration options
---------------------

The ``file`` request handlers have several configuration options that can be
used to control their behavior. Most of them apply both the HTTP and TFTP
handler, but some are specific to only one of the two.

For a more detailed discussion about the options controlling request path
matching, please refer to :ref:`request_path_matching`. More information about
the templating mechanism can be found in :ref:`using_templates` and a example
making use of some of the options an be found in :ref:`config_example`.

The common options are:

:``file`` (mandatory):
    Path to the file that is served by the request handler. Either this option
    or the ``root_dir`` option must be set. Both options cannot be used
    together. If this option is set, the request handler only answers requests
    that specify the exact ``request_path`` and it does not serve any other
    files.

:``request_path`` (mandatory):
    request path for which this request handler should be used. The specified
    path must start with a ``/`` and it must not end with a ``/`` (unless the
    ``/`` is the only character in the whole path). When operating in directory
    mode, the value of this option is treated as a prefix. If the ``lookup_key``
    option is set, the specified path must contain a placeholder (which is
    configured through the ``lookup_value_placeholder`` option). Please refer to
    :ref:`request_path_matching` for a more thorough discussion of request path
    matching.

:``root_dir`` (mandatory):
    Path to the directory that contains the files that are served by the request
    handler. Either this option or the ``file`` option must be set. Both options
    cannot be used together. If this option is set, the request handler answers
    all requests that specify a path that starts with the ``request_path``. The
    parts of the request path after that prefix are interpreted as the path of
    the file to be served, relative to the ``root_dir``.

:``data_source_error_action`` (optional):
    Action to be taken if the data source's ``find_system`` or ``get_data``
    method raises an exception. If set to ``error`` (the default), the request
    handler lets this exception bubble up, typically resulting in the exception
    being logged and an error message being returned to the client. If set to
    ``ignore`` the exception is caught and process continues without the data
    from the data source (depending on the ``lookup_no_result_action`` if
    ``find_system`` raised the exception). If set to ``warn``, the same actions
    as for the the ``ignore`` action are taken, but the exception is also
    logged.

:``lookup_key`` (optional):
    Name of the lookup key that shall be used when calling ``find_system``. If
    ``None`` or empty (the default), no system-specifc data is retrieved and the
    ``request_path`` is not expected to contain a placeholder. If set to the
    special value ``:system_id:``, the value extracted from the request path is
    not passed to ``find_system``, but used as a system ID directly.

:``lookup_no_result_action`` (optional):
    Action to be taken if no system ID can be determined. This can happen if
    ``find_system`` returns ``None`` or if it raises an exception and
    ``data_source_error_action`` is set to ``ignore`` or ``warn``. If set to
    ``continue`` the code proceeds without information about the system, so
    neither the ``id`` nor the ``data`` object are available when rendering the
    template. If set to ``not_found`` (the default), a "not found" error (error
    code 404 in the case of HTTP) os returned to the client.

:``lookup_value_placeholder`` (optional):
    Placeholder that is used for the lookup value in the ``request_path``
    option. The default placeholder is ``...``. This option has no effect unless
    ``lookup_key`` is set.

:``lookup_value_transform`` (optional):
    Transformations to be applied to the lookup value. This is a list of
    transformations that are applied to the value extracted from the request
    path and being passed to ``find_system`` or being used as a system ID
    directly. This list is passed to
    `vinegar.transform.apply_transformation_chain`. If this list is empty (the
    default), no transformations are applied and the string extracted from the
    request path is used as is.

:``template`` (optional):
    name of the template engine (as a ``str``) that shall be used for rending
    the files. This name is passed to `~vinegar.template.get_template_engine` in
    order to retrieve the template engine. If empty or set to ``None`` (the
    default), templating is disabled.

:``template_config`` (optional):
    configuration for the template engine. The default is an empty dictionary
    (``{}``). This configuration is passed on to the template engine as is.

The configuration options specific to the HTTP version of the request handler
are:

:``content_type`` (optional):
    Value to use for the ``Content-Type`` header that is sent to the client.
    If ``None`` or empty (the default), the content_type is guessed based on the
    ``template`` option. If no template engine is used, the value
    ``application/octet-stream`` is used. If a template engine is used, the
    value ``text/plain; charset=UTF-8`` is used. When specifying a different
    type, the value should include a ``charset`` specification for text types.
    The output of a template engine is always encoded as ``UTF-8``, so typically
    this charset should be specified.

:``content_type_map`` (optional):
    Dictionary of filenames and file extensions to ``Content-Type``
    specifications. This option is similar to the ``content_type`` option, but
    it allows for using different values for different files served by the same
    handler. When serving a file, the handler first looks for a key that exactly
    matches the filename (without any preceding path components). If no such key
    is found, it looks for a key that matches the file extension. If no such key
    is found either, it uses the value of the ``content_type`` option. For
    example, when serving the file ``/path/to/my.html``, the handler first looks
    for ``my.html`` and, if that key does not exist, tries ``.html``.
    This option can only be used in directory mode. In file mode, using this
    option does not make sense because there only is a single file and thus
    using the ``content_type`` option is simpler.
"""

import http.client
import io
import logging
import os.path
import urllib.parse

from http import HTTPStatus
from typing import Any, Mapping, Tuple

from vinegar.data_source import DataSource, DataSourceAware
from vinegar.http.server import HttpRequestHandler
from vinegar.template import get_template_engine
from vinegar.tftp.protocol import ErrorCode as TftpErrorCode
from vinegar.tftp.server import TftpError, TftpRequestHandler
from vinegar.transform import apply_transformation_chain
from vinegar.utils.smart_dict import SmartLookupOrderedDict

# Logger used by this module.
logger = logging.getLogger(__name__)

class FileRequestHandlerBase(DataSourceAware):
    """
    Base class for the `HttpFileRequestHandler` and `TftpFileRequestHandler`.

    This class implements most of the functionality of both handlers. The
    separate classes only exist due to the slightly different APIs for the two
    handler types.

    For information about the configuration options supported by this request
    handler, please refer to the
    `module documentation <vinegar.request_handler.file>`.
    """

    def __init__(self, config: Mapping[Any, Any]):
        """
        Initialize the base class.

        :param config:
            configuration for this request handler. Please refer to the
            `module documentation <vinegar.request_handler.file>` for a list of
            supported options.
        """
        # The data source is injected later by calling set_data_source.
        self._data_source = None
        self._data_source_error_action = config.get(
            'data_source_error_action', 'error')
        if self._data_source_error_action not in ('error', 'ignore', 'warn'):
            raise ValueError(
                'Invalid data_source_error_action "{0}". Action must be one of '
                '"error", "ignore", "warn".'.format(
                    self._data_source_error_action))
        self._file = config.get('file', None)
        self._lookup_no_result_action = config.get(
            'lookup_no_result_action', 'not_found')
        if self._lookup_no_result_action not in ('continue', 'not_found'):
            raise ValueError(
                'Invalid lookup_no_result action "{0}". Action must be one of '
                '"continue", "not_found".'.format(
                    self._lookup_no_result_action))
        self._root_dir = config.get('root_dir', None)
        # When neither the "file" nor the "root_dir" key are present in the
        # configuration, we raise a KeyError. This way, we are consistent with
        # the behavior for other missing configuration keys.
        if ('file' not in config) and ('root_dir' not in config):
            raise KeyError('file or root_dir key must be present.')
        if (not self._file) and (not self._root_dir):
            raise ValueError(
                'Either the file or the root_dir configuration option needs to '
                'be set.')
        if self._file and self._root_dir:
            raise ValueError(
                'Only one of the file and the root_dir configuration options '
                'must be set.')
        template = config.get('template', None)
        template_config = config.get('template_config', {})
        if template:
            self._template_engine = get_template_engine(template, template_config)
        else:
            self._template_engine = None
        # Initializing the variables that are related to the request path is
        # rather complex, so we do it in a separate method.
        self._init_request_path(config)

    def can_handle(self, filename: str, context: Any) -> bool:
        return context['matches']

    def prepare_context(self, filename: str) -> Any:
        # We initialize the context so that it signals a mismatch if returned
        # without changing it.
        context = {
            'extra_path': None,
            'lookup_raw_value': None,
            'matches': False,
        }
        # If the original filename contains a null byte, someone is trying
        # something nasty and we do not consider the path to match. The same is
        # true if the null byte is present in URL encoded form.
        if '\0' in filename or '%00' in filename:
            return context
        # We do not use urllib.parse.urlsplit beause that function produces
        # unexpected results if the filename is not well-formed.
        path, _, _ = filename.partition('?')
        path = urllib.parse.unquote(path)
        # We need special handling for the case where both the configured and
        # the actual request path is "/" and this handler is registered for a
        # file. In this case, the regular logic would fail, because we would
        # generate two empty segments for the actual request path, but only
        # have one empty segment for the configured request path. Please note
        # that this only applies when we do not expect a lookup value and we
        # operate in file mode.
        if ((path == '/')
                and (self._request_path_prefix_segments == [''])
                and (not self._extract_lookup_value)
                and self._file):
            context['matches'] = True
            return context
        path_segments = path.split('/')
        # If the path has fewer segments than our prefix, it cannot match.
        if len(path_segments) < len(self._request_path_prefix_segments):
            return context
        for expected_segment, actual_segment in zip(
                self._request_path_prefix_segments, path_segments):
            if expected_segment != actual_segment:
                return context
        # We know that the path matches the prefix, so we can cut all the
        # segments that we just checked.
        path_segments = path_segments[len(self._request_path_prefix_segments):]
        # If we have to extract a lookup value, the next path segment must
        # contain that value.
        if self._extract_lookup_value:
            # If there are no remaining path segments, but we need a lookup
            # value, the path does not match.
            if not path_segments:
                return context
            path_lookup_value_segment = path_segments[0]
            # The segment must start with the segment prefix and end with the
            # segment suffix.
            if not (
                    path_lookup_value_segment.startswith(
                        self._request_path_placeholder_segment_prefix)
                    and path_lookup_value_segment.endswith(
                        self._request_path_placeholder_segment_suffix)):
                return context
            # We remove the segment that contains the lookup value and check
            # that the rest actually matches the suffix.
            del path_segments[0]
            # If the path has fewer segments than our suffix, it cannot match.
            if len(path_segments) < len(self._request_path_suffix_segments):
                return context
            for expected_segment, actual_segment in zip(
                    self._request_path_suffix_segments, path_segments):
                if expected_segment != actual_segment:
                    return context
            # Now we know that the suffix matches, so we can remove if from the
            # path as well.
            path_segments = path_segments[
                len(self._request_path_suffix_segments):]
            # In order to extract the lookup value, we simply remove the prefix
            # and suffix.
            lookup_raw_value = path_lookup_value_segment[
                len(self._request_path_placeholder_segment_prefix):]
            if self._request_path_placeholder_segment_suffix:
                lookup_raw_value = lookup_raw_value[
                    :-len(self._request_path_placeholder_segment_suffix)]
            # If the lookup value is empty, we do not consider this a match.
            if not lookup_raw_value:
                return context
            context['lookup_raw_value'] = lookup_raw_value
        # The extra path is defined by the remaining segments. We removed the
        # leading "/" of the extra path when removing the prefix, so we have to
        # make sure that it is added again when converting back to a string. We
        # only have to add the "/" if there are any extra segments at all.
        if path_segments:
            # In file mode, there should not be any extra path segments. if
            # there are, we do not consider this a match.
            if self._file:
                return context
            context['extra_path'] = '/'.join([''] + path_segments)
        else:
            # In directory mode, we need extra path segments, otherwise we
            # cannot handle the request.
            if self._root_dir:
                return context
        context['matches'] = True
        return context

    def set_data_source(self, data_source: DataSource) -> None:
        self._data_source = data_source

    def _handle(self, filename: str, context: Any) -> io.BufferedIOBase:
        extra_path = context['extra_path']
        # When we are operating in directory mode, we have to find out whether
        # the extra path matches a file in the root_dir.
        if self._root_dir:
            file = self._translate_path(self._root_dir, extra_path)
        else:
            file = self._file
        # If the file could not be resolved, we treat it like it does not exist.
        if file is None:
            return (None, None)
        # We might have to do a lookup.
        if self._extract_lookup_value:
            lookup_key = self._lookup_key
            lookup_raw_value = context['lookup_raw_value']
            lookup_value = apply_transformation_chain(
                self._lookup_value_transform, lookup_raw_value)
            # If the lookup key is set to ":system_id", we treat the value as
            # the system ID instead of trying to look it up.
            if lookup_key == ':system_id:':
                system_id = lookup_value
            else:
                # If the data source is not available, we 
                try:
                    system_id = self._data_source.find_system(
                        lookup_key, lookup_value)
                except:
                    if self._data_source_error_action == 'error':
                        raise
                    elif self._data_source_error_action == 'warn':
                        logger.warning(
                            'The data_source.find_system("%s", "%s") method '
                            'raised an exception. This is treated as a lookup '
                            'failure (system_id == None).',
                            lookup_key, lookup_value)
                    system_id = None
            if system_id is None:
                if self._lookup_no_result_action == 'not_found':
                    return (None, None)
                data = None
            else:
                # If there is no template engine, there is no sense in
                # retrieving the system data because it would not be used
                # anyway.
                if self._template_engine is not None:
                    try:
                        data, _ = self._data_source.get_data(system_id, {}, '')
                    except:
                        if self._data_source_error_action == 'error':
                            raise
                        elif self._data_source_error_action == 'warn':
                            logger.warning(
                                'The data_source.get_data("%s", ...) method '
                                'raised an exception. Continuing without '
                                'system data.',
                                system_id)
                            pass
                        data = None
        else:
            # If we have no lookup key, the system ID and data are always None.
            system_id = None
            data = None
        try:
            if self._template_engine is not None:
                # Please note that we do not cache the result of the rendering
                # process. It is unlikely that the same file is repeatedly
                # requested for the same system, so caching would probably not
                # bring much benefit.
                template_context = {}
                if system_id is not None:
                    template_context['id'] = system_id
                if data is not None:
                    template_context['data'] = SmartLookupOrderedDict(data)
                render_result = self._template_engine.render(
                    file, template_context)
                return (io.BytesIO(render_result.encode()), file)
            else:
                return (open(file, mode='rb'), file)
        except (FileNotFoundError, IsADirectoryError):
            # We treat a request to a file that is actually a directory like a
            # request to a file that does not exist. This is consistent with our
            # behavior that we do not allow a request with an extra path that
            # has a trailing slash.
            return None, file

    def _init_request_path(self, config):
        request_path = config['request_path']
        # Every valid request path must start with a forward slash.
        if not request_path.startswith('/'):
            raise ValueError(
                'Invalid request path "{0}": The request path must start with '
                'a "/".'.format(request_path))
        # The special request path "/" is replaced with the empty string. That
        # has the effect that the first "/" of an actual request is added to the
        # extra path. One could argue that the configured request path for this
        # case should actually be the empty string, but this would make it more
        # likely to create such a configuration by accident.
        if request_path == '/':
            request_path = ''
        # The request path must not end with a forward slash.
        if request_path.endswith('/') and request_path != '/':
            raise ValueError(
                'Invalid request path "{0}": The request path must not end '
                'with a "/".'.format(request_path))
        self._lookup_key = config.get('lookup_key', None)
        self._lookup_value_placeholder = config.get(
            'lookup_value_placeholder', '...')
        self._lookup_value_transform = config.get('lookup_value_transform', [])
        # If a lookup key is defined, the request path must contain a
        # placeholder. That placeholder defines which part of the path contains
        # the value to be looked up.
        if self._lookup_key:
            self._extract_lookup_value = True
            # We split the path into its segments. We expect that the lookup
            # value does not contain any slashes (if it did, there would be some
            # ambiguity regarding what is part of the value and what is part of
            # the path).
            request_path_segments = request_path.split('/')
            placeholder_index = None
            placeholder = self._lookup_value_placeholder
            for index in range(0, len(request_path_segments)):
                if placeholder in request_path_segments[index]:
                    if placeholder_index is None:
                        placeholder_index = index
                    else:
                        raise ValueError(
                            'Request path "{0}" contains placeholder "{1}" '
                            'more than once.'.format(request_path, placeholder))
            if placeholder_index is None:
                raise ValueError(
                    'Request path "{0}" does not contain placeholder '
                    '"{1}".'.format(request_path, placeholder))
            # The path segment
            request_path_placeholder_segment = \
                request_path_segments[placeholder_index]
            placeholder_segment_sub_components = \
                request_path_placeholder_segment.split(placeholder)
            # We know that the component contains the placeholder, so know that
            # the split cannot result in less than two components.
            if len(placeholder_segment_sub_components) > 2:
                raise ValueError(
                    'Request path "{0}" contains placeholder "{1}" more than '
                    'once.'.format(request_path, placeholder))
            self._request_path_prefix_segments = \
                request_path_segments[:placeholder_index]
            self._request_path_placeholder_segment_prefix = \
                placeholder_segment_sub_components[0]
            self._request_path_placeholder_segment_suffix = \
                placeholder_segment_sub_components[1]
            self._request_path_suffix_segments = \
                request_path_segments[(placeholder_index + 1):]
        else:
            self._extract_lookup_value = False
            self._request_path_prefix_segments = request_path.split('/')

    @staticmethod
    def _translate_path(root_dir, extra_path):
            # There is no good reason why a path should contain a null byte, so
            # we can be pretty sure someone is trying something nasty, if it
            # does. Actually, this case should already be caught in
            # prepare_context, but we have it here again, just in case the code
            # structure changes in the future.
            if '\0' in extra_path:
                return None
            # If we are running on a platform that does not use "/" as its path
            # separator (e.g. Windows), we convert every character that is the
            # path separator on this platform to "/". This ensures that after
            # splitting, the path segments, there will be no segment that
            # contains the platform's path separator.
            extra_path = extra_path.replace(os.path.sep, '/')
            # If there is no extra path, or if it ends with a "/", we do not
            # even have to look for a file.
            if (not extra_path) or extra_path.endswith('/'):
                return None
            # We split the path into its segments so that we can build the
            # corresponding path on the file system.
            extra_path_segments = extra_path.split('/')
            # We remove any leading empty segments (those are caused by leading
            # "/"s in the string).
            while extra_path_segments and extra_path_segments[0] == '':
                del extra_path_segments[0]
            # If there are no segments left, the path does not refer to a valid
            # file.
            if not extra_path_segments:
                return None
            # If there are path segments that are "." or "..", the chances are
            # good that someone is trying something nasty.
            if ('.' in extra_path_segments) or ('..' in extra_path_segments):
                return None
            # Now we can construct the path on the file system.
            fs_path = os.path.join(root_dir, *extra_path_segments)
            fs_path = os.path.normpath(fs_path)
            # The next check is kind of redundant: Due to the previous checks,
            # it should not be possible to construct a path that points outside
            # the root_dir. We still use this check to be extra sure.
            if not fs_path.startswith(root_dir):
                return None
            else:
                return fs_path

class HttpFileRequestHandler(FileRequestHandlerBase, HttpRequestHandler):
    """
    HTTP request handler that serves files from the file system.

    For information about the configuration options supported by this request
    handler, please refer to the
    `module documentation <vinegar.request_handler.file>`.
    """

    def __init__(self, config: Mapping[Any, Any]):
        """
        Create a HTTP file request handler. Usually, instances of this class are
        not instantiated directly, but through the `get_instance_http` function.

        :param config:
            configuration for this request handler. Please refer to the
            `module documentation <vinegar.request_handler.file>` for a list of
            supported options.
        """
        super().__init__(config)
        self._content_type = config.get('content_type', None)
        if not self._content_type:
            if config.get('template'):
                self._content_type = 'text/plain; charset=UTF-8'
            else:
                self._content_type = 'application/octet-stream'
        self._content_type_map = config.get('content_type_map', None)
        if not self._content_type_map:
           self._content_type_map = {}
        elif self._file:
            raise ValueError(
                'The content_type_map must be empty when operating in file '
                'mode.')

    def handle(
            self,
            filename: str,
            method: str,
            headers: http.client.HTTPMessage,
            body: io.BufferedIOBase,
            client_address: Tuple,
            context: Any) \
            -> Tuple[HTTPStatus, Mapping[str, str], io.BufferedIOBase]:
        if method not in ('GET', 'HEAD'):
            return HTTPStatus.METHOD_NOT_ALLOWED, None, None
        try:
            file, file_path = self._handle(filename, context)
        except PermissionError:
            return HTTPStatus.FORBIDDEN, None, None
        if file is None:
            return HTTPStatus.NOT_FOUND, None, None
        # When operating in directory mode, we try to determine the content type
        # based on entries in the content_type_map. If that fails, we use the
        # value of the content_type setting. In file mode, we skip the
        # content_type_map and go to the content_type setting directly.
        if self._root_dir:
            file_basename = os.path.basename(file_path)
            _, _, file_extension = file_basename.rpartition('.')
            content_type = self._content_type_map.get(
                file_basename, self._content_type_map.get(
                    '.' + file_extension, self._content_type))
        else:
            content_type = self._content_type
        response_headers = {}
        response_headers['Content-Type'] = content_type
        if method == 'HEAD':
            file.close()
            file = None
        return HTTPStatus.OK, response_headers, file

class TftpFileRequestHandler(FileRequestHandlerBase, TftpRequestHandler):
    """
    TFTP request handler that serves files from the file system.

    For information about the configuration options supported by this request
    handler, please refer to the
    `module documentation <vinegar.request_handler.file>`.
    """
    pass

    def __init__(self, config: Mapping[Any, Any]):
        """
        Create a TFTP file request handler. Usually, instances of this class are
        not instantiated directly, but through the `get_instance_tftp` function.

        :param config:
            configuration for this request handler. Please refer to the
            `module documentation <vinegar.request_handler.file>` for a list of
            supported options.
        """
        super().__init__(config)
        # When operating in file mode, we do not allow to specify a request path
        # of "/". This is a difference to HTTP where we allow such a
        # configuration. For TFTP, the notion of an "index file" does not exist,
        # and as we add a leading slash to the request, if needed, we would
        # actually allow requests with an empty filename, which is certainly not
        # what we want.
        if (config['request_path'] == '/') and config.get('file', None):
            raise ValueError(
                'A request path of "/" cannot be used in file mode.')

    def can_handle(self, filename: str, context: Any) -> bool:
        filename = self._rewrite_filename_if_needed(filename)
        return super().can_handle(filename, context)

    def handle(
            self,
            filename: str,
            client_address: Tuple,
            context: Any) -> io.BufferedIOBase:
        filename = self._rewrite_filename_if_needed(filename)
        try:
            file, _ = self._handle(filename, context)
        except PermissionError:
            raise TftpError(error_code=TftpErrorCode.ACCESS_VIOLATION)
        if file is None:
            raise TftpError(error_code=TftpErrorCode.FILE_NOT_FOUND)
        return file

    def prepare_context(self, filename: str) -> Any:
        filename = self._rewrite_filename_if_needed(filename)
        return super().prepare_context(filename)

    @staticmethod
    def _rewrite_filename_if_needed(filename):
        # Unlike HTTP, TFTP may have valid requests that do not start with a
        # forward slash. We want to treat such requests as if they started with
        # a forward slash.
        if filename.startswith('/') or filename.startswith('%2f'):
            return filename
        else:
            return '/' + filename

def get_instance_http(config: Mapping[Any, Any]) -> HttpFileRequestHandler:
    """
    Create a HTTP request handler serving files.

    If the request handler needs a data source (if its ``lookup_key``
    configuration option is used), the data source has to be set by calling
    the `~DataSourceAware.set_data_source` method of the returned object.

    :param config:
        configuration for this request handler. Please refer to the
        `module documentation <vinegar.request_handler.file>` for a list of
        supported options.
    :return:
        HTTP request handler serving files from the file system.
    """
    return HttpFileRequestHandler(config)

def get_instance_tftp(config: Mapping[Any, Any]) -> HttpFileRequestHandler:
    """
    Create a TFTP request handler serving files.

    If the request handler needs a data source (if its ``lookup_key``
    configuration option is used), the data source has to be set by calling
    the `~DataSourceAware.set_data_source` method of the returned object.

    :param config:
        configuration for this request handler. Please refer to the
        `module documentation <vinegar.request_handler.file>` for a list of
        supported options.
    :return:
        TFTP request handler serving files from the file system.
    """
    return TftpFileRequestHandler(config)
