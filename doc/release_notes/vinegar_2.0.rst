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

vingar.data_source.yaml_target
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Due to changes in the `vinegar.utils.system_matcher` module, the syntax for the
target matching expressions in the ``top.yaml`` file have changed. As a
consequence expressions that contain the symbol ``@`` must now be quoted.

The matching syntax has been extended significantly, now allowing much more
complex matching expressions.

The location of YAML files that are included from other files can now be
specified relative to the location of the file where they are included by
starting the name of the included file with a dot (``.``).

Finally, the file name suffix used for all the configuration files that are
used by the YAML target source can now be specified through the
``file_suffix`` configuration option. ``.yaml`` is still the default, so this
change is fully backwards compatible.

vinegar.request_handler.file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The file request handler supports the new ``client_address_key`` and
``client_address_list`` configuration options. If they are not specified, the
behavior is as before.

There also is a new ``file_suffix`` option that can be used to add a suffix to
the file name being looked up (this only works when operating in ``root_dir``
mode).

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

vinegar.utils.odict
^^^^^^^^^^^^^^^^^^^

The ``vinegar.utils.odict`` module has been removed because starting with
Python 3.7, the regular ``dict`` always preserves the insertion order.

vinegar.utils.oyaml
^^^^^^^^^^^^^^^^^^^

The ``vinegar.utils.oyaml`` module has been removed because starting with
Python 3.7, the regular ``dict`` always preserves the insertion order and thus
the regular ``yaml`` module has this feature as well, removing the need for the
``vinegar.utils.oyaml`` module.

vinegar.utils.smart_dict
^^^^^^^^^^^^^^^^^^^^^^^^

The class ``SmartLookupOrderedDict`` has been removed. Starting with
Python 3.7, the regular ``dict`` preserves insertion order, so
`~vinegar.utils.smart_dict.SmartLookupDict` now preservers the insertion order
as well and thus there is no need for ``SmartLookupOrderedDict``  any longer.

In addition to these changes, the ``SmartLookupDict`` now allows access to the
items of nested lists. In general, this change is backwards compatible, the
only effect is that attempts to access an item in a nested list that would
previously have resulted in a ``KeyError`` or the default value being returned
will now return an actual value.

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

vinegar.utils.system_matcher
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The syntax of the expressions supported by the `vinegar.utils.system_matcher`
module has been extended. This has two consequences which break backward
compatibility:

* Expressions that contain the ``@`` character must no be wrapped in quotes.
* The signatures of the `~vinegar.utils.system_matcher.match` function and the
  `~vinegar.utils.system_matcher.Matcher.matches` method have changed. They
  expect a dict for the system data in addition to the system ID now, and the
  ``case_sensitive`` argument has been removed, because case sensitivity can
  now be explicitly configured for each sub-expression.
