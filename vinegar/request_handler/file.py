"""
Request handler that serves files from the file systems.

The files can either be served as is or they can be processed through a
template engine. The handler can either work with a single file or with a whole
directory of files.

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
using code has to take care of that. However, a `DataSource` is only needed
when using the ``lookup_key`` configuration option. If that option is empty
(the default), no data source is needed and it is not even used if it is
available.

This module provides request handlers for both HTTP and TFTP. These two
handlers are almost identical in their behavior with only a few minor
differences:

* The options related to the ``Content-Type`` header are only available in the
  HTTP version. TFTP does not have any equivalent of the ``Content-Type``
  header in HTTP.
* The TFTP version of the handler allows request paths that do not start with a
  forward slash (``/``). In this case, the forward slash is added
  automatically. The HTTP version of the handler, in contrast, does not do
  anything like this because request paths not starting with a forward slash
  are rejected by the HTTP server component.

By default, this request handler does not process files as templates and treats
them as binary files. However, when enabling templating through the
``template`` option, files are read as text files and decoded as UTF-8. The
result of the rendering process of the template engine is then encoded as UTF-8
before sending it to the client.

This means that the default value of the ``content_type`` option (only
available in the HTTP version of the handler) depends on whether a template
engine is used or not.

.. _request_handler_file_request_path_matching:

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
and due to a missing ``/`` being added automatically, such a configuration
would actually match requests with an empty path.

When operating in directory mode (if the ``root_dir`` configuration option is
used), the configured request path specifies the prefix that must match. Extra
portions of the actual request path are treated as the path of the requested
file relative to the ``root_dir``. For example, if ``request_path`` is set to
``/myprefix`` and ``root_dir`` is set to ``/path/on/fs``, a request specifying
the path ``/myprefix/some/file`` would result in the file
``/path/on/fs/some/file`` being served.

A request handler operating in directory mode will catch all requests that
start with the specified prefix, even if the file does not actually exist. This
means that a request handler serving a more specific path prefix has to come
earlier in the chain of request handlers or it will never be asked whether it
can handle a request.

When using the ``lookup_key`` configuration option, the configured request path
has to contain exactly one placeholder. The default placeholder string is
``...``, but this can be changed through the ``lookup_value_placeholder``
configuration option.

When such a configuration is used, the placeholder marks a portion of the
request path that might be different from request to request. For example, a
configured ``request_path`` of ``/prefix/file-...`` will match an actual
request path of ``/prefix/file-abc``, ``/prefix/file-def``, etc. The
placeholder will not match an empty string, so the request path will not match
``/prefix/file-``.

The value that replaces the placeholder in the actual request path is
transformed according to the configuration set through the
``lookup_value_transform`` configuration option and then used to find a system
ID through `DataSource.find_system`. This is most useful when also using a
template engine (see :ref:`request_handler_file_templates`). If no matching
system can be found, the request file is treated as not existing (unless
``lookup_no_result_action`` is set to ``continue``).

Placeholders do not necessarily have to appear at the end of a request path.
For example, a ``request_path`` of ``/prefix/.../suffix``` will match
``/prefix/abc/suffix``

Placeholders can be used in file mode as well as in directory mode. Like
request paths that do not use place holders, the extra portion of the path will
be used as the path of the file inside the directory, when operating in
directory mode.

.. _request_handler_file_templates:

Using templates
---------------

Optionally, files served by the request handlers can be treated as templates.
This behavior is enabled by setting the ``template`` configuration option to
the name of one of the template engines supported by
`~vinegar.template.get_template_engine`. One good choice might be the ``jinja``
template engine.

A context object with the name ``request_info`` is passed to the template
engine. For more information about this object, please refer to
:ref:`request_handler_file_request_info`.

If the ``lookup_key`` configuration option is also set, the request handler
additionally provides two context objects to the template engine: The ``id``
object contains the system ID (as a ``str``). The ``data`` object contains the
data that has been returned from the data source's `~DataSource.get_data`
method. The ``data`` object is passed as a
`~vinegar.utils.smart_dict.SmartLookupDict` to make it easier to get nested
values.

The ``data`` object is not available if the data source's ``get_data`` method
raised an exception. Usually, this will cause the template not even to be
rendered, but this can be overridden through the ``data_source_error_action``
configuration option.

If the data source's `~DataSource.find_system` method returns ``None`` and
``lookup_no_result_action`` is set to ``continue``, neither ``id`` nor ``data``
are available. The same applies if ``find_system`` raises an exception and
``lookup_no_result_action`` is set to ``continue`` and
``data_source_error_action`` is set to ``ignore`` or ``warn``.

.. _request_handler_file_request_info:

Request information
-------------------

The ``request_info`` object is a ``dict``, which contains the following keys.
The ``headers`` and ``method`` keys are only present for requests received via
HTTP. Additional keys might be added in future versions.

``client_address``
    The value for this key is a two-tuple, where the first element is the IP
    address of the requesting client (as a ``str``) and the second element is
    the port number used by the client (as an ``int``).

``headers``
    The HTTP request headers as an instance of ``http.client.HTTPMessage``.

    **This key is only available for HTTP requests.**

``method``
    The HTTP request method (e.g. ``GET``, ``POST``, etc.).

    **This key is only available for HTTP requests.**

``server_address``
    The value for this key is a two-tuple, where the first element is the IP
    address on which the server received the request (as a ``str``) and the
    second element is the port number on which the server received the requeset
    (as an ``int``).

    Please note that for TFTP requests, the server might not be able to
    determine the address on which a request was received (due to limitations
    on some platforms). In this case, this will instead be the IP address to
    which the server’s socket has been bound.

``uri``
    The full request URI specified by the client in undecoded form. For a TFTP
    request, this typically is the filename. For an HTTP request, this might
    also include a query string.

.. _request_handler_file_access_restrictions:

Access restrictions
-------------------

By default, this request handler will allow any client to retrieve files
rendered for any system. This might not be desirable if the files contain
confidential information (e.g. password), in particular when the network in
which the Vinegar server is running cannot be deemed secure.

Therefore, it is possible to limit access to the data for each system to
specific clients. This is achieved through the ``client_address_key``
configuration option. This option specifies a key into the system data. The key
can consist of multiple components separated by colons (``:``) to point into
a nested dictionary.

For example, suppose that ``client_address_key`` is set to ``net:ip_addr``. If
the handler gets a request for the system ID ``myid``, it will ask the data
source for the system data for this system by calling
``data_source.get_data('myid', {}, '')``.

If the system data returned for this system does not contain a value for the
specified key, the request is denied with HTTP status code 403 (forbidden).

For this example, let us assume that the data source returns the following data
for the system ``myid`` (expressed as YAML):

.. code-block:: yaml

    net:
        ip_addr: 192.0.2.1

In this case, the request handler will only allow the request, if it comes from
the IP address 192.0.2.1. In all other cases, it will reject the request.

Instead of a single IP address, the system data may also contain a list or set
of IP addresses. For example, if ``get_data`` returned the following system
data

.. code-block:: yaml

    net:
        ip_addr:
            - 192.0.2.1
            - 2001:db8::1

the request would be allowed if it came from 192.0.2.1 or 2001:db8::1.

In addition to single IP addresses, IP subnets using CIDR notation are allowed
as well. For example,

.. code-block:: yaml

    net:
        ip_addr:
            - 192.0.2.0/24
            - 2001:db8::/64

will allow access for all clients from the IP subnets 192.0.2.0/24 and
2001:db8::/64.

As an alternative to the ``client_address_key`` option, the
``client_address_list`` option may be specified. This option takes a list of IP
addresses or IP subnets and allows requests from clients that match one of
these entries. This can be useful in order to allow full access from certain
administrative clients.

When both ``client_address_key`` and ``client_address_list`` are specified,
they are combined, meaning that a request is allowed when it either matches one
of the entries from ``client_address_list`` or the entries from the data tree
for the ``client_address_key``.

When the ``client_address_key`` option is used, the ``lookup_key`` option must
be set as well and this request handler needs a data source in order to get
information about the system. This request handler implements the
``DataSourceAware`` interface, so when it is used inside a container, that
container will typically take care of setting the data source. If instantiated
directly, the data source has to be set explicitly by calling the handler’s
``set_data_source`` method.

.. _request_handler_file_config_example:

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
be replaced by ``:`` and letters will be converted to upper case). The
resulting value (``02:03:04:05:06:0A``) will be used as a lookup value together
and passed to the data source's ``find_system`` method along with the lookup
key (``net:mac_addr``). Assuming that the data source can resolve this
key-value combination, the returned system ID is used in a call to ``get_data``
and both the system ID and the data are passed to the template engine when
rendering ``myconf.txt``.

As we have set the ``lookup_no_result_action`` to ``continue`` a MAC address
that is not known by the data source will not result in a "not found" error
(status code 404 in the case of HTTP). Instead, the template is rendered
without a system ID and system data, so that some default content is returned.

Configuration options
---------------------

The ``file`` request handlers have several configuration options that can be
used to control their behavior. Most of them apply both the HTTP and TFTP
handler, but some are specific to only one of the two.

For a more detailed discussion about the options controlling request path
matching, please refer to :ref:`request_handler_file_request_path_matching`.
More information about the templating mechanism can be found in
:ref:`request_handler_file_templates` and a example making use of some of the
options an be found in :ref:`request_handler_file_config_example`.

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
    mode, the value of this option is treated as a prefix. If the
    ``lookup_key`` option is set, the specified path must contain a placeholder
    (which is configured through the ``lookup_value_placeholder`` option).
    Please refer to :ref:`request_handler_file_request_path_matching` for a
    more thorough discussion of request path matching.

:``root_dir`` (mandatory):
    Path to the directory that contains the files that are served by the
    request handler. Either this option or the ``file`` option must be set.
    Both options cannot be used together. If this option is set, the request
    handler answers all requests that specify a path that starts with the
    ``request_path``. The parts of the request path after that prefix are
    interpreted as the path of the file to be served, relative to the
    ``root_dir``.

:``client_address_key`` (optional):
    Key into the system data that points to the place in the data where the
    allowed client address or addresses are stored. If this option is not set
    (the default), each client can access this handler for arbitrary system IDs
    and thus potentially retrieve data associated with these systems. When this
    is not desired, this option can be used to limit the allowe client (IP)
    addresses for each system. The key can point into a nested dictionary,
    using the colon (``:``) to separate key components for the various levels.
    The value can be a string (matching exactly one IP address or IP subnet) or
    a list or set of IP addresses or IP subnets (matching any of the addresses
    or subnets in the list or set). If this option is set, ``lookup_key`` must
    be set as well. Please refer to
    :ref:`request_handler_file_access_restrictions` for a more detailed
    discussion of how this option can be used.

:``client_address_list`` (optional):
    List of IP addresses or IP subnets from which requests are allowed. Please
    refer to :ref:`request_handler_file_access_restrictions` for a more
    detailed discussion of how this option can be used.

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
    ``None`` or empty (the default), no system-specifc data is retrieved and
    the ``request_path`` is not expected to contain a placeholder. If set to
    the special value ``:system_id:``, the value extracted from the request
    path is not passed to ``find_system``, but used as a system ID directly.

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
    option. The default placeholder is ``...``. This option has no effect
    unless ``lookup_key`` is set.

:``lookup_value_transform`` (optional):
    Transformations to be applied to the lookup value. This is a list of
    transformations that are applied to the value extracted from the request
    path and being passed to ``find_system`` or being used as a system ID
    directly. This list is passed to
    `vinegar.transform.get_transformation_chain`. If this list is empty (the
    default), no transformations are applied and the string extracted from the
    request path is used as is.

:``template`` (optional):
    name of the template engine (as a ``str``) that shall be used for rending
    the files. This name is passed to `~vinegar.template.get_template_engine`
    in order to retrieve the template engine. If empty or set to ``None`` (the
    default), templating is disabled.

:``template_config`` (optional):
    configuration for the template engine. The default is an empty dictionary
    (``{}``). This configuration is passed on to the template engine as is.

The configuration options specific to the HTTP version of the request handler
are:

:``content_type`` (optional):
    Value to use for the ``Content-Type`` header that is sent to the client.
    If ``None`` or empty (the default), the content_type is guessed based on
    the ``template`` option. If no template engine is used, the value
    ``application/octet-stream`` is used. If a template engine is used, the
    value ``text/plain; charset=UTF-8`` is used. When specifying a different
    type, the value should include a ``charset`` specification for text types.
    The output of a template engine is always encoded as ``UTF-8``, so
    typically this charset should be specified.

:``content_type_map`` (optional):
    Dictionary of filenames and file extensions to ``Content-Type``
    specifications. This option is similar to the ``content_type`` option, but
    it allows for using different values for different files served by the same
    handler. When serving a file, the handler first looks for a key that
    exactly matches the filename (without any preceding path components). If no
    such key is found, it looks for a key that matches the file extension. If
    no such key is found either, it uses the value of the ``content_type``
    option. For example, when serving the file ``/path/to/my.html``, the
    handler first looks for ``my.html`` and, if that key does not exist, tries
    ``.html``. This option can only be used in directory mode. In file mode,
    using this option does not make sense because there only is a single file
    and thus using the ``content_type`` option is simpler.
"""

import dataclasses
import io
import logging
import os
import os.path
import urllib.parse

from http import HTTPStatus
from typing import Any, Dict, Mapping, Optional, Tuple

from vinegar.data_source import DataSource, DataSourceAware
from vinegar.http.server import HttpRequestHandler, HttpRequestInfo
from vinegar.template import get_template_engine
from vinegar.tftp.protocol import ErrorCode as TftpErrorCode
from vinegar.tftp.server import TftpError, TftpRequestHandler
from vinegar.transform import get_transformation_chain
from vinegar.utils.smart_dict import SmartLookupDict
from vinegar.utils.socket import contains_ip_address, InetSocketAddress

# Logger used by this module.
logger = logging.getLogger(__name__)


class _FileRequestHandlerBase(DataSourceAware):
    """
    Base class for the `HttpFileRequestHandler` and `TftpFileRequestHandler`.

    This class implements most of the functionality of both handlers, but is
    not intended for direct use by code outside this module. Code outside this
    module should only use the two child classes.

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
        self._client_address_key = config.get("client_address_key", None)
        client_address_list = config.get("client_address_list", None)
        # If the client_address_list option is specified, we convert the value
        # into a set, because this is what we are going to need later.
        if client_address_list:
            self._client_address_set = set(client_address_list)
        else:
            self._client_address_set = None
        # The data source is injected later by calling set_data_source.
        self._data_source = None
        self._data_source_error_action = config.get(
            "data_source_error_action", "error"
        )
        if self._data_source_error_action not in ("error", "ignore", "warn"):
            raise ValueError(
                "Invalid data_source_error_action "
                f'"{self._data_source_error_action}". Action must be one of '
                '"error", "ignore", "warn".'
            )
        self._file = config.get("file", None)
        self._lookup_no_result_action = config.get(
            "lookup_no_result_action", "not_found"
        )
        if self._lookup_no_result_action not in ("continue", "not_found"):
            raise ValueError(
                "Invalid lookup_no_result action "
                f'"{self._lookup_no_result_action}". Action must be one of '
                '"continue", "not_found".'
            )
        self._root_dir = config.get("root_dir", None)
        # When neither the "file" nor the "root_dir" key are present in the
        # configuration, we raise a KeyError. This way, we are consistent with
        # the behavior for other missing configuration keys.
        if ("file" not in config) and ("root_dir" not in config):
            raise KeyError("file or root_dir key must be present.")
        if (not self._file) and (not self._root_dir):
            raise ValueError(
                "Either the file or the root_dir configuration option needs "
                "to be set."
            )
        if self._file and self._root_dir:
            raise ValueError(
                "Only one of the file and the root_dir configuration options "
                "must be set."
            )
        template = config.get("template", None)
        template_config = config.get("template_config", {})
        if template:
            self._template_engine = get_template_engine(
                template, template_config
            )
        else:
            self._template_engine = None
        # Initializing the variables that are related to the request path is
        # rather complex, so we do it in a separate method.
        self._init_request_path(config)
        # If client_address_key option is specified, a lookup_key must be
        # specified as well.
        if self._client_address_key and not self._lookup_key:
            raise ValueError(
                "If the client_address_key option is set, lookup_key must be "
                "set as well."
            )

    def _can_handle(
        self,
        uri: str,  # pylint: disable=unused-argument
        context: Any,
    ) -> bool:
        """
        Tell whether the request can be handled by this request handler.

        Returns ``True`` if the request can be handled and ``False`` if it
        cannot be handled and the next request handler should be tried.

        This implementation simply checks whether ``prepare_context`` detected
        a match and returns ``True`` if and only if it did.

        :param uri:
            URI that has been requested by the client.
        :param context:
            context object that was returned by ``prepare_context``.
        :return:
            ``True`` if this request handler can handle the specified request,
            ``False`` if the request should be deferred to the next handler.
        """
        return context["matches"]

    def _handle(
        self,
        uri: str,  # pylint: disable=unused-argument
        context: Any,
        client_address: InetSocketAddress,
        request_info: Dict[str, Any],
    ) -> Tuple[Optional[io.BufferedIOBase], Optional[str]]:
        """
        Handle the request.

        :param uri:
            URI that has been requested by the client.
        :param context:
            context object that was returned by ``prepare_context``.
        :param client_address:
            client address. The structure of the tuple depends on the address
            family in use, but typically the first element is the client's
            host address and the second element is the client's port number.
        :param request_info:
            additional information about the request that is passed to the
            template engine, so that it can be used when rendering templates.
        :return:
            tuple of the a file-like object that provides the data that is
            transferred to the client and a string providing the file-system
            path to the file being served. The file-like object is optional. If
            it is ``None``, this indicates that the file cannot be found. The
            path is also optional but may only be ``None`` if the file-like
            object is ``None``.
        """
        # We might have to do a lookup.
        if self._extract_lookup_value:
            lookup_key = self._lookup_key
            lookup_raw_value = context["lookup_raw_value"]
            lookup_value = self._lookup_value_transform(lookup_raw_value)
            # If the lookup key is set to ":system_id", we treat the value as
            # the system ID instead of trying to look it up.
            if lookup_key == ":system_id:":
                system_id = lookup_value
            else:
                # If the data source is not available, we raise an error or
                # continue without a system ID, depending on the
                # data_source_error_action.
                try:
                    assert self._data_source is not None
                    system_id = self._data_source.find_system(
                        lookup_key, lookup_value
                    )
                # We do not know which kind of exceptions a data source might
                # raise, so we intentionally catch all regular exceptions.
                except Exception:  # pylint: disable=broad-exception-caught
                    if self._data_source_error_action == "error":
                        raise
                    if self._data_source_error_action == "warn":
                        logger.warning(
                            'The data_source.find_system("%s", "%s") method '
                            "raised an exception. This is treated as a lookup "
                            "failure (system_id == None).",
                            lookup_key,
                            lookup_value,
                            exc_info=True,
                        )
                    system_id = None
            if system_id is None:
                data = None
            else:
                # If there is no template engine and the client_address_key
                # option is not used, there is no sense in retrieving the
                # system data because it would not be used anyway.
                if (
                    not self._client_address_key
                ) and self._template_engine is None:
                    data = None
                else:
                    try:
                        assert self._data_source is not None
                        data, _ = self._data_source.get_data(system_id, {}, "")
                    # We do not know which kind of exceptions a data source
                    # might raise, so we intentionally catch all regular
                    # exceptions.
                    except Exception:  # pylint: disable=broad-exception-caught
                        if self._data_source_error_action == "error":
                            raise
                        if self._data_source_error_action == "warn":
                            logger.warning(
                                'The data_source.get_data("%s", ...) method '
                                "raised an exception. Continuing without "
                                "system data.",
                                system_id,
                                exc_info=True,
                            )
                        data = None
        else:
            # If we have no lookup key, the system ID and data are always None.
            system_id = None
            data = None
        # If we have system data, we wrap it in a smart-lookup dict, because
        # there are several places where we expect to be able to do lookups for
        # nested keys.
        if data is not None:
            data = SmartLookupDict(data)
        # If the client_address_key or client_address_list options have been
        # specified, we have to check access restrictions.
        expected_client_addresses = None
        if self._client_address_key:
            # When self._client_address_key is set, set_data_source should have
            # been called before this method is called.
            assert self._data_source is not None
            # We get the expected client address from the system data. We wrap
            # the system data in a smart lookup dict, so that we can look for a
            # value inside a nested dict. If we do not have a system ID, we
            # cannot do a lookup, so we treat this like an empty list of client
            # addresses.
            if system_id is None or data is None:
                expected_client_addresses = []
            else:
                expected_client_addresses = data.get(
                    self._client_address_key, None
                )
            # The expected client addresses can be a container (e.g. list, set)
            # of allowed addresses or they can be a single string. The expected
            # client addresses may also not be defined at all, in which case we
            # simply use an empty list.
            if isinstance(expected_client_addresses, str):
                expected_client_addresses = [expected_client_addresses]
            elif not expected_client_addresses:
                expected_client_addresses = []
        if self._client_address_set:
            # If we already have a set of expected client addresses, we have to
            # use the union of bot hsets. Otherwise, we can simply use the set
            # as-is.
            if expected_client_addresses is None:
                expected_client_addresses = self._client_address_set
            else:
                expected_client_addresses = self._client_address_set.union(
                    expected_client_addresses
                )
        if expected_client_addresses is not None:
            # The IP address part of the client address is the first element of
            # the tuple. If we do not have a client address, we cannot perform
            # the access check. This is fine, because the client_address should
            # only be None if third-party code calls this method, and this code
            # should not expect any of the client_address related configuration
            # options.
            assert client_address is not None
            actual_client_address = client_address[0]
            # If the client address is not in the set of allowed addresses,
            # the request is not allowed.
            if not contains_ip_address(
                expected_client_addresses, actual_client_address
            ):
                # Raising a permission error ensures that the calling code
                # sends the correct status code to the client.
                raise PermissionError()
        # If we are expected to make a lookup, but this lookup was not
        # successful (we do not have a system ID) and the
        # lookup_no_result_action is “not found”, we treat this like if the
        # requested file was not found. It would be easier to handle this
        # earlier, in the lookup logic, but then an unauthorized clients might
        # get information about whether a lookup was successful (by seeing a
        # permission error instead of a not found error), so we always do the
        # permission check first.
        if (
            self._extract_lookup_value
            and self._lookup_no_result_action == "not_found"
            and system_id is None
        ):
            return (None, None)
        extra_path = context["extra_path"]
        # When we are operating in directory mode, we have to find out whether
        # the extra path matches a file in the root_dir.
        if self._root_dir:
            file = self._translate_path(self._root_dir, extra_path)
        else:
            file = self._file
        # If the file could not be resolved, we treat it like it does not
        # exist.
        if file is None:
            return (None, None)
        try:
            if self._template_engine is not None:
                # Please note that we do not cache the result of the rendering
                # process. It is unlikely that the same file is repeatedly
                # requested for the same system, so caching would probably not
                # bring much benefit.
                template_context: Dict[str, Any] = {
                    "request_info": request_info
                }
                if system_id is not None:
                    template_context["id"] = system_id
                if data is not None:
                    template_context["data"] = data
                render_result = self._template_engine.render(
                    file, template_context
                )
                return (io.BytesIO(render_result.encode()), file)
            return (open(file, mode="rb"), file)
        except PermissionError:
            # On Windows, we get a permission error when trying to open a
            # directory, so we want to catch such a situation and treat it
            # like a IsADirectoryError.
            if os.path.isdir(file):
                return None, file
            raise
        except (FileNotFoundError, IsADirectoryError):
            # We treat a request to a file that is actually a directory like a
            # request to a file that does not exist. This is consistent with
            # our behavior that we do not allow a request with an extra path
            # that has a trailing slash.
            return None, file

    def _init_request_path(self, config):
        request_path = config["request_path"]
        # Every valid request path must start with a forward slash.
        if not request_path.startswith("/"):
            raise ValueError(
                f'Invalid request path "{request_path}": The request path '
                'must start with a "/".'
            )
        # The special request path "/" is replaced with the empty string. That
        # has the effect that the first "/" of an actual request is added to
        # the extra path. One could argue that the configured request path for
        # this case should actually be the empty string, but this would make it
        # more likely to create such a configuration by accident.
        if request_path == "/":
            request_path = ""
        # The request path must not end with a forward slash.
        if request_path.endswith("/") and request_path != "/":
            raise ValueError(
                f'Invalid request path "{request_path}": The request path '
                'must not end with a "/".'
            )
        self._lookup_key = config.get("lookup_key", None)
        self._lookup_value_placeholder = config.get(
            "lookup_value_placeholder", "..."
        )
        self._lookup_value_transform = get_transformation_chain(
            config.get("lookup_value_transform", [])
        )
        # If a lookup key is defined, the request path must contain a
        # placeholder. That placeholder defines which part of the path contains
        # the value to be looked up.
        if self._lookup_key:
            self._extract_lookup_value = True
            # We split the path into its segments. We expect that the lookup
            # value does not contain any slashes (if it did, there would be
            # some ambiguity regarding what is part of the value and what is
            # part of the path).
            request_path_segments = request_path.split("/")
            placeholder_index = None
            placeholder = self._lookup_value_placeholder
            for index, request_path_segment in enumerate(
                request_path_segments
            ):
                if placeholder in request_path_segment:
                    if placeholder_index is None:
                        placeholder_index = index
                    else:
                        raise ValueError(
                            f'Request path "{request_path}" contains '
                            f'placeholder "{placeholder}" more than once.'
                        )
            if placeholder_index is None:
                raise ValueError(
                    f'Request path "{request_path}" does not contain '
                    f'placeholder "{placeholder}".'
                )
            # The path segment
            request_path_placeholder_segment = request_path_segments[
                placeholder_index
            ]
            placeholder_segment_sub_components = (
                request_path_placeholder_segment.split(placeholder)
            )
            # We know that the component contains the placeholder, so know that
            # the split cannot result in less than two components.
            if len(placeholder_segment_sub_components) > 2:
                raise ValueError(
                    f'Request path "{request_path}" contains placeholder '
                    f'"{placeholder}" more than once.'
                )
            self._request_path_prefix_segments = request_path_segments[
                :placeholder_index
            ]
            self._request_path_placeholder_segment_prefix = (
                placeholder_segment_sub_components[0]
            )
            self._request_path_placeholder_segment_suffix = (
                placeholder_segment_sub_components[1]
            )
            self._request_path_suffix_segments = request_path_segments[
                (placeholder_index + 1) :
            ]
        else:
            self._extract_lookup_value = False
            self._request_path_prefix_segments = request_path.split("/")

    def _prepare_context(self, uri: str) -> Any:
        """
        Prepare a context object for use by ``can_handle`` and ``handle``. This
        method is called for each request before calling ``can_handle``.

        This method parses the filename and checks whether it matches the
        configuration of this handler. It saves this information in the
        returned context for later use by ``can_handle``.

        :param uri:
            URI that has been requested by the client.
        :return:
            context object that is passed to ``can_handle`` and ``handle``.
        """
        # We initialize the context so that it signals a mismatch if returned
        # without changing it.
        context = {
            "extra_path": None,
            "lookup_raw_value": None,
            "matches": False,
        }
        # If the original filename contains a null byte, someone is trying
        # something nasty and we do not consider the path to match. The same is
        # true if the null byte is present in URL encoded form.
        if "\0" in uri or "%00" in uri:
            return context
        # We do not use urllib.parse.urlsplit beause that function produces
        # unexpected results if the filename is not well-formed.
        path, _, _ = uri.partition("?")
        path = urllib.parse.unquote(path)
        # We need special handling for the case where both the configured and
        # the actual request path is "/" and this handler is registered for a
        # file. In this case, the regular logic would fail, because we would
        # generate two empty segments for the actual request path, but only
        # have one empty segment for the configured request path. Please note
        # that this only applies when we do not expect a lookup value and we
        # operate in file mode.
        if (
            (path == "/")
            and (self._request_path_prefix_segments == [""])
            and (not self._extract_lookup_value)
            and self._file
        ):
            context["matches"] = True
            return context
        path_segments = path.split("/")
        # If the path has fewer segments than our prefix, it cannot match.
        if len(path_segments) < len(self._request_path_prefix_segments):
            return context
        for expected_segment, actual_segment in zip(
            self._request_path_prefix_segments, path_segments
        ):
            if expected_segment != actual_segment:
                return context
        # We know that the path matches the prefix, so we can cut all the
        # segments that we just checked.
        path_segments = path_segments[
            len(self._request_path_prefix_segments) :
        ]
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
                    self._request_path_placeholder_segment_prefix
                )
                and path_lookup_value_segment.endswith(
                    self._request_path_placeholder_segment_suffix
                )
            ):
                return context
            # We remove the segment that contains the lookup value and check
            # that the rest actually matches the suffix.
            del path_segments[0]
            # If the path has fewer segments than our suffix, it cannot match.
            if len(path_segments) < len(self._request_path_suffix_segments):
                return context
            for expected_segment, actual_segment in zip(
                self._request_path_suffix_segments, path_segments
            ):
                if expected_segment != actual_segment:
                    return context
            # Now we know that the suffix matches, so we can remove if from the
            # path as well.
            path_segments = path_segments[
                len(self._request_path_suffix_segments) :
            ]
            # In order to extract the lookup value, we simply remove the prefix
            # and suffix.
            lookup_raw_value = path_lookup_value_segment[
                len(self._request_path_placeholder_segment_prefix) :
            ]
            if self._request_path_placeholder_segment_suffix:
                lookup_raw_value = lookup_raw_value[
                    : -len(self._request_path_placeholder_segment_suffix)
                ]
            # If the lookup value is empty, we do not consider this a match.
            if not lookup_raw_value:
                return context
            context["lookup_raw_value"] = lookup_raw_value
        # The extra path is defined by the remaining segments. We removed the
        # leading "/" of the extra path when removing the prefix, so we have to
        # make sure that it is added again when converting back to a string. We
        # only have to add the "/" if there are any extra segments at all.
        if path_segments:
            # In file mode, there should not be any extra path segments. if
            # there are, we do not consider this a match.
            if self._file:
                return context
            context["extra_path"] = "/".join([""] + path_segments)
        else:
            # In directory mode, we need extra path segments, otherwise we
            # cannot handle the request.
            if self._root_dir:
                return context
        context["matches"] = True
        return context

    @staticmethod
    def _translate_path(root_dir, extra_path):
        # There is no good reason why a path should contain a null byte, so we
        # can be pretty sure someone is trying something nasty, if it does.
        # Actually, this case should already be caught in prepare_context, but
        # we have it here again, just in case the code structure changes in the
        # future.
        if "\0" in extra_path:
            return None
        # If we are running on a platform that does not use "/" as its path
        # separator (e.g. Windows), we convert every character that is the path
        # separator on this platform to "/". This ensures that after splitting,
        # the path segments, there will be no segment that contains the
        # platform's path separator.
        extra_path = extra_path.replace(os.path.sep, "/")
        # If there is no extra path, or if it ends with a "/", we do not even
        # have to look for a file.
        if (not extra_path) or extra_path.endswith("/"):
            return None
        # We split the path into its segments so that we can build the
        # corresponding path on the file system.
        extra_path_segments = extra_path.split("/")
        # We remove any leading empty segments (those are caused by leading
        # "/"s in the string).
        while extra_path_segments and extra_path_segments[0] == "":
            del extra_path_segments[0]
        # If there are no segments left, the path does not refer to a valid
        # file.
        if not extra_path_segments:
            return None
        # If there are path segments that are "." or "..", the chances are good
        # that someone is trying something nasty.
        if ("." in extra_path_segments) or (".." in extra_path_segments):
            return None
        # Now we can construct the path on the file system.
        fs_path = os.path.join(root_dir, *extra_path_segments)
        fs_path = os.path.normpath(fs_path)
        # The next check is kind of redundant: Due to the previous checks, it
        # should not be possible to construct a path that points outside the
        # root_dir. We still use this check to be extra sure.
        if not fs_path.startswith(root_dir):
            return None
        return fs_path

    def set_data_source(self, data_source: DataSource) -> None:
        self._data_source = data_source


class HttpFileRequestHandler(_FileRequestHandlerBase, HttpRequestHandler):
    """
    HTTP request handler that serves files from the file system.

    For information about the configuration options supported by this request
    handler, please refer to the
    `module documentation <vinegar.request_handler.file>`.
    """

    def __init__(self, config: Mapping[Any, Any]):
        """
        Create a HTTP file request handler. Usually, instances of this class
        are not instantiated directly, but through the `get_instance_http`
        function.

        :param config:
            configuration for this request handler. Please refer to the
            `module documentation <vinegar.request_handler.file>` for a list of
            supported options.
        """
        super().__init__(config)
        self._content_type = config.get("content_type", "")
        if not self._content_type:
            if config.get("template"):
                self._content_type = "text/plain; charset=UTF-8"
            else:
                self._content_type = "application/octet-stream"
        self._content_type_map = config.get("content_type_map", {})
        # This check seems unnecessary, but it also handles the case where the
        # config map contains an empty string as the value for the key.
        if not self._content_type_map:
            self._content_type_map = {}
        elif self._file:
            raise ValueError(
                "The content_type_map must be empty when operating in file "
                "mode."
            )

    def can_handle(self, uri: str, context: Any) -> bool:
        return self._can_handle(uri, context)

    def handle(
        self,
        request_info: HttpRequestInfo,
        body: io.BufferedIOBase,
        context: Any,
    ) -> Tuple[
        HTTPStatus, Optional[Mapping[str, str]], Optional[io.BufferedIOBase]
    ]:
        if request_info.method not in ("GET", "HEAD"):
            return HTTPStatus.METHOD_NOT_ALLOWED, None, None
        try:
            file, file_path = self._handle(
                request_info.uri,
                context,
                client_address=request_info.client_address,
                request_info=dataclasses.asdict(request_info),
            )
        except PermissionError:
            return HTTPStatus.FORBIDDEN, None, None
        if file is None:
            return HTTPStatus.NOT_FOUND, None, None
        # When file is not None, file_path should not be None either.
        assert file_path is not None
        # When operating in directory mode, we try to determine the content
        # type based on entries in the content_type_map. If that fails, we use
        # the value of the content_type setting. In file mode, we skip the
        # content_type_map and go to the content_type setting directly.
        if self._root_dir:
            file_basename = os.path.basename(file_path)
            _, _, file_extension = file_basename.rpartition(".")
            content_type = self._content_type_map.get(
                file_basename,
                self._content_type_map.get(
                    "." + file_extension, self._content_type
                ),
            )
        else:
            content_type = self._content_type
        response_headers = {}
        response_headers["Content-Type"] = content_type
        try:
            fpos = file.tell()
            file.seek(0, os.SEEK_END)
            response_headers["Content-Length"] = str(file.tell() - fpos)
            file.seek(fpos, os.SEEK_SET)
        except io.UnsupportedOperation:
            pass
        if request_info.method == "HEAD":
            file.close()
            file = None
        return HTTPStatus.OK, response_headers, file

    def prepare_context(self, uri: str) -> Any:
        return self._prepare_context(uri)


class TftpFileRequestHandler(_FileRequestHandlerBase, TftpRequestHandler):
    """
    TFTP request handler that serves files from the file system.

    For information about the configuration options supported by this request
    handler, please refer to the
    `module documentation <vinegar.request_handler.file>`.
    """

    def __init__(self, config: Mapping[Any, Any]):
        """
        Create a TFTP file request handler. Usually, instances of this class
        are not instantiated directly, but through the `get_instance_tftp`
        function.

        :param config:
            configuration for this request handler. Please refer to the
            `module documentation <vinegar.request_handler.file>` for a list of
            supported options.
        """
        super().__init__(config)
        # When operating in file mode, we do not allow to specify a request
        # path of "/". This is a difference to HTTP where we allow such a
        # configuration. For TFTP, the notion of an "index file" does not
        # exist, and as we add a leading slash to the request, if needed, we
        # would actually allow requests with an empty filename, which is
        # certainly not what we want.
        if (config["request_path"] == "/") and config.get("file", None):
            raise ValueError(
                'A request path of "/" cannot be used in file mode.'
            )

    def can_handle(self, filename: str, context: Any) -> bool:
        filename = self._rewrite_filename_if_needed(filename)
        return self._can_handle(filename, context)

    def handle(
        self,
        filename: str,
        client_address: InetSocketAddress,
        server_address: InetSocketAddress,
        context: Any,
    ) -> io.BufferedIOBase:
        filename = self._rewrite_filename_if_needed(filename)
        try:
            request_info = {
                "client_address": client_address,
                "server_address": server_address,
                "uri": filename,
            }
            file, _ = self._handle(
                filename,
                context,
                client_address=client_address,
                request_info=request_info,
            )
        except PermissionError:
            # We do not include the original exception here because it won’t be
            # used anyway. The exception only indicates that the error code
            # should be send to the client.
            raise TftpError(  # pylint: disable=raise-missing-from
                error_code=TftpErrorCode.ACCESS_VIOLATION
            )
        if file is None:
            raise TftpError(error_code=TftpErrorCode.FILE_NOT_FOUND)
        return file

    def prepare_context(self, filename: str) -> Any:
        filename = self._rewrite_filename_if_needed(filename)
        return self._prepare_context(filename)

    @staticmethod
    def _rewrite_filename_if_needed(filename):
        # Unlike HTTP, TFTP may have valid requests that do not start with a
        # forward slash. We want to treat such requests as if they started with
        # a forward slash.
        if filename.startswith("/") or filename.startswith("%2f"):
            return filename
        return "/" + filename


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


def get_instance_tftp(config: Mapping[Any, Any]) -> TftpFileRequestHandler:
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
