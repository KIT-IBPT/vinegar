.. _release_notes_vinegar_2.0:

Vinegar 2.0
===========

When upgrading from Vinegar 1.x to Vinegar 2.x, there are a number of breaking
changes, so you might have to adapt your configuration and – in case you have
extended Vinegar – your code.

Vinegar 2.0 needs Python 3.8 or newer. Python 3.5, 3.6, and 3.7 are not
supported any longer.

Configuration changes
---------------------

TODO Document all changes to the configuration file.

vinegar.request_handler.file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The file request handler supports the new ``client_address_key`` and
``client_address_list`` configuration options. If they are not specified, the
behavior is as before.

If using the ``template`` option, a new context object called ``request_info``
is now available while rendering the template.

Please refer to the API documentation for
`vinegar.request_handler.file` for more information.

vinegar.request_handler.sqlite_update
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The SQLite-update request handler supports the new ``client_address_list``
configuration option and the behavior of the ``client_address_key``
configuration option has changed slightly: When the value in the data tree that
is referenced through this key contains an IP subnet mask specification, client
IP addresses within the respective subnet are now matched, while before such an
entry would simply be ignored.

Please refer to the API documentation for
`vinegar.request_handler.sqlite_update` for more information.

API changes
-----------

TODO Document all changes to the API.

vinegar.http.server
^^^^^^^^^^^^^^^^^^^

The interface of the `~vinegar.http.server.HttpRequestHandler` has undergone
significant changes:

The ``filename`` arguments of the
`~vinegar.http.server.HttpRequestHandler.can_handle` and the
`~vinegar.http.server.HttpRequestHandler.prepare_context` methods have been
renamed to ``uri`` in order to better reflect their meaning.

The `~vinegar.http.server.HttpRequestHandler.handle` method has been
refactored, replacing its ``filename``, ``method``, ``headers``, and
``client_address`` arguments with the new ``request_info`` argument that is an
instance of the newly introduced class `~vinegar.http.server.HttpRequestInfo`.

vinegar.request_handler.file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``FileRequestHandlerBase`` class has been removed and replaced by a private
class. This class was never intended for use outside this module.

The method signatures of the
`~vinegar.request_handler.file.HttpFileRequestHandler` and
`~vinegar.request_handler.file.TftpFileRequestHandler` classes have been
changed in order to match the changes made to
`~vinegar.http.server.HttpRequestHandler` and
`~vinegar.tftp.server.TftpRequestHandler`.

vinegar.request_handler.sqlite_update
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The method signatures of the
`~vinegar.request_handler.sqlite_update.HttpSQLiteUpdateRequestHandler` have
been changed in order to match the changes made to
`~vinegar.http.server.HttpRequestHandler`.

vinegar.tftp.server
^^^^^^^^^^^^^^^^^^^

The interface of the `~vinegar.tftp.server.TftpRequestHandler` has been
slightly changed:

A new argument with the name ``server_address`` has been added to the
`~vinegar.tftp.server.TftpRequestHandler.handle` method.

vinegar.utils.socket
^^^^^^^^^^^^^^^^^^^^

The `~vingar.utils.socket.socket_address_to_str` method now only accepts an
argument of type `~vinegar.utils.socket.InetSocketAddress`. This means that
tuples that only have a single element are not accepted any longer and it
also means that the first element of the tuple has to be a ``str`` and the
second element has to be an ``int``.

Three new type aliases have been introduced:
`~vingar.utils.socket.Inet4SocketAddress`,
`~vingar.utils.socket.Inet6SocketAddress`, and
`~vingar.utils.socket.InetSocketAddress`. These are aliases for the types of
tuples that may be encountered when dealing with IPv4 or IPv6 socket addresses.
