"""
Request handler that allows for making changes to an SQLite database.

This request handler is backed by an instance of
`vinegar.utils.sqlite_store.DataStore` for actually accessing the database.

This can be useful when a flag for a system has to be updated dynamically. For
example, there might be a flag that indicates whether a system should boot into
an installer when booting from the network. Once the system installation has
finished, this flag would need to be reset to avoid running the installer again
and again. With this handler, this can be achieved by making a HTTP request to
an instance of this handler once the installation process has finished. This
handler can then reset the flag in the database, ensuring that the system will
not boot into the installer again.

This handler only handles ``POST`` requests. The semantics of ``GET`` requests
are that they are idempotent, meaning that they do not change any state. As
this request handler makes changes to the state of the database, allowing
``GET`` requests would violate the semantics of the HTTP protocol.

It is very easy to trigger a ``POST`` request from the command line. Depending
on which tools are available on the system, either of the following two
commands can be used::

    curl -X POST http://vinegar.example.com/sqlite-prefix/system-id
    wget -O - --post-data= http://vinegar.example.com/sqlite-prefix/system-id

When using the ``set_json_value_from_request_body`` or
``set_text_value_from_request_body`` action, the value that shall be set can be
passed like this::

    curl -X POST --data-binary myvalue \
        http://vinegar.example.com/sqlite-prefix/system-id
    wget -O - --post-data=myvalue \
        http://vinegar.example.com/sqlite-prefix/system-id

.. _request_handler_sqlite_update_access_restrictions:

Access restrictions
-------------------

By default, this request handler will allow any client to update the data for
all systems. This might not be desirable, in particular when the network in
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
specified key, the request is denied with HTTP status code 403 (forbidden) and
the database is not modified.

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

When the ``client_address_key`` option is used, this request handler needs a
data source in order to get information about the system. This request handler
implements the ``DataSourceAware`` interface, so when it is used inside a
container, that container will typically take care of setting the data source.
If instantiated directly, the data source has to be set explicitly by calling
the handler's ``set_data_source`` method.

Configuration options
---------------------

The ``sqlite_update`` request handler have several configuration options that
can be used to control its behavior.

:``action`` (mandatory):
    Action to be taken when this handler is triggers. If set to
    ``delete_data``, all data stored for the specified system is deleted. If
    set to ``delete_value``, only the key and value specified by the ``key``
    option are deleted. If set to ``set_value`` the value for the key specified
    by the ``key`` option is set to the value specified by the ``value``
    option. If set to ``set_json_value_from_request_body``, the value is read
    from the body of the HTTP request and decoded as JSON. If set to
    ``set_text_value_from_request_body``, the value is read from the body of
    the HTTP request (it must be encoded as UTF-8) and stored as a string.

:``db_file`` (mandatory):
    Path to the database file that contains the SQLite database that will be
    updated by this handler. This database must be a database in the format
    expected by `vinegar.utils.sqlite.data_store`.

:``request_path`` (mandatory):
    request path for which this request handler shall be used. The specified
    path must start with a ``/``. It will match any request that has a path
    that starts with the configured request path and is followed by a string.
    For example, when the ``request_path`` is set to ``/prefix`` the handler
    will match ``/prefix/name``. In this example, ``name`` is the string that
    is used as the system ID.

:``client_address_key`` (optional):
    Key into the system data that points to the place in the data where the
    allowed client address or addresses are stored. If this option is not set
    (the default), each client can access this handler for arbitrary system IDs
    and thus modify the data for arbitrary systems. When this is not desired,
    this option can be used to limit the allowe client (IP) addresses for each
    system. The key can point into a nested dictionary, using the colon (``:``)
    to separate key components for the various levels. The value can be a
    string (matching exactly one IP address or IP subnet) or a list or set of
    IP addresses or IP subnets (matching any of the addresses or subnets in the
    list or set). Please refer to
    :ref:`request_handler_sqlite_update_access_restrictions` for a more
    detailed discussion of how this option can be used.

:``client_address_list`` (optional):
    List of IP addresses or IP subnets from which requests are allowed. Please
    refer to :ref:`request_handler_sqlite_update_access_restrictions` for a
    more detailed discussion of how this option can be used.

:``key`` (optional):
    Name of the key in the database that shall be deleted or updated. If the
    ``action`` is set to ``delete_value``, ``set_value``,
    ``set_json_value_from_request_body``, or
    ``set_text_value_from_request_body``, this option must be specified.

:``value`` (optional):
    Value to be set for the key denoted by the ``key``. When the ``action`` is
    set to ``set_value``, this option must be specified.
"""

import io
import json
import urllib.parse

from http import HTTPStatus
from typing import Any, Mapping, Optional, Tuple

from vinegar.data_source import DataSource, DataSourceAware
from vinegar.http.server import HttpRequestHandler, HttpRequestInfo
from vinegar.utils.smart_dict import SmartLookupDict
from vinegar.utils.socket import contains_ip_address
from vinegar.utils.sqlite_store import open_data_store


class HttpSQLiteUpdateRequestHandler(HttpRequestHandler, DataSourceAware):
    """
    HTTP request handler that applies updates to an SQLite database.

    For information about the configuration options supported by this request
    handler, please refer to the
    `module documentation <vinegar.request_handler.sqlite_update>`.
    """

    def __init__(self, config: Mapping[Any, Any]):
        """
        Create a HTTP SQLite update request handler. Usually, instances of this
        class are not instantiated directly, but through the
        `get_instance_http` function.

        :param config:
            configuration for this request handler. Please refer to the
            `module documentation <vinegar.request_handler.sqlite_update>` for
            a list of supported options.
        """
        self._request_path = config["request_path"]
        if not self._request_path.startswith("/"):
            raise ValueError(
                f'Invalid request path "{self._request_path}": The request '
                'path must start with a "/".'
            )
        if not self._request_path.endswith("/"):
            self._request_path += "/"
        self._action = config["action"]
        if self._action not in (
            "delete_data",
            "delete_value",
            "set_value",
            "set_json_value_from_request_body",
            "set_text_value_from_request_body",
        ):
            raise ValueError(
                f'Invalid action "{self._action}". Action must be one of '
                '"delete_data", "delete_value", "set_value".'
            )
        if self._action in (
            "delete_value",
            "set_value",
            "set_json_value_from_request_body",
            "set_text_value_from_request_body",
        ):
            self._key = config["key"]
        if self._action == "set_value":
            self._value = config["value"]
        self._client_address_key = config.get("client_address_key", None)
        client_address_list = config.get("client_address_list", None)
        # If the client_address_list option is specified, we convert the value
        # into a set, because this is what we are going to need later.
        if client_address_list:
            self._client_address_set = set(client_address_list)
        else:
            self._client_address_set = None
        self._data_source: Optional[DataSource] = None
        self._data_store = open_data_store(config["db_file"])

    def can_handle(self, uri: str, context: Any) -> bool:
        return context["matches"]

    def close(self):
        """
        Close the data store backing this request handle. All operations that
        involve the data store will fail by raising an exception after calling
        this method.

        For most applications, where request handlers are long-lived, relying
        on Python's garbage collection is fine for closing the underlying data
        store. However, if an application rapidly creates and discards request
        handler instances (e.g. for automated tests), closing the request
        handler explicitly can be beneficial because it helps to release
        resources early on.
        """
        self._data_store.close()

    def handle(
        self,
        request_info: HttpRequestInfo,
        body: io.BufferedIOBase,
        context: Any,
    ) -> Tuple[
        HTTPStatus, Optional[Mapping[str, str]], Optional[io.BufferedIOBase]
    ]:
        # We only allow requests using the POST method.
        if request_info.method != "POST":
            return HTTPStatus.METHOD_NOT_ALLOWED, None, None
        system_id = context["system_id"]
        # If the client_address_key or client_address_list options have been
        # specified, we have to check access restrictions.
        expected_client_addresses = None
        if self._client_address_key:
            # When self._client_address_key is set, set_data_source should have
            # been called before this method is called.
            assert self._data_source is not None
            # We get the expected client address from the system data. We wrap
            # the system data in a smart lookup dict, so that we can look for a
            # value inside a nested dict.
            system_data, _ = self._data_source.get_data(system_id, {}, "")
            system_data = SmartLookupDict(system_data)
            expected_client_addresses = system_data.get(
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
            # the tuple.
            actual_client_address = request_info.client_address[0]
            # If the client address is not in the set of allowed addresses,
            # the request is not allowed.
            if not contains_ip_address(
                expected_client_addresses, actual_client_address
            ):
                return HTTPStatus.FORBIDDEN, None, None
        # If we have made it here, the request is allowed.
        if self._action == "delete_data":
            self._data_store.delete_data(system_id)
        elif self._action == "delete_value":
            self._data_store.delete_value(system_id, self._key)
        elif self._action == "set_value":
            self._data_store.set_value(system_id, self._key, self._value)
        elif self._action == "set_json_value_from_request_body":
            try:
                body_length = int(
                    request_info.headers.get("Content-Length", "0")
                )
                raw_bytes = body.read(body_length)
                value = json.load(io.BytesIO(raw_bytes))
            except (OSError, ValueError):
                return HTTPStatus.BAD_REQUEST, None, None
            self._data_store.set_value(system_id, self._key, value)
        elif self._action == "set_text_value_from_request_body":
            try:
                body_length = int(
                    request_info.headers.get("Content-Length", "0")
                )
                raw_bytes = body.read(body_length)
                value = raw_bytes.decode()
            except (OSError, ValueError):
                return HTTPStatus.BAD_REQUEST, None, None
            self._data_store.set_value(system_id, self._key, value)
        else:
            raise RuntimeError(f"Unimplemented action: {self._action}")
        response_headers = {"Content-Type": "text/plain; charset=UTF-8"}
        # We do not send an empty reply because curl considers this an error.
        response_body = io.BytesIO(b"success\n")
        return HTTPStatus.OK, response_headers, response_body

    def prepare_context(self, uri: str) -> Any:
        # We initialize the context so that it signals a mismatch if returned
        # without changing it.
        context = {"matches": False, "system_id": None}
        # If the original filename contains a null byte, someone is trying
        # something nasty and we do not consider the path to match. The same is
        # true if the null byte is present in URL encoded form.
        if "\0" in uri or "%00" in uri:
            return context
        # We do not use urllib.parse.urlsplit beause that function produces
        # unexpected results if the filename is not well-formed.
        path, _, _ = uri.partition("?")
        path = urllib.parse.unquote(path)
        if path.startswith(self._request_path):
            system_id = path[len(self._request_path) :]
            if system_id:
                context["matches"] = True
                context["system_id"] = path[len(self._request_path) :]
        return context

    def set_data_source(self, data_source: DataSource) -> None:
        self._data_source = data_source


def get_instance_http(
    config: Mapping[Any, Any]
) -> HttpSQLiteUpdateRequestHandler:
    """
    Create a HTTP request handler that applies updates to an SQLite database.

    :param config:
        configuration for this request handler. Please refer to the
        `module documentation <vinegar.request_handler.sqlite_update>` for a
        list of supported options.
    :return:
        HTTP request handler applying updates to an SQLite database.
    """
    return HttpSQLiteUpdateRequestHandler(config)
