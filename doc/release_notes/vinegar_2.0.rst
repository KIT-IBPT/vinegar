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
