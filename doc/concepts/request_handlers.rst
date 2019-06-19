.. _concepts_request_handlers:

Request handlers
================

Request handlers (from the module `vinegar.request_handlers`) are responsible
for handling requests received by :ref:`servers <concepts_servers>`.

While custom request handlers can be implemented by providing a module with a
``get_instance_http`` or ``get_instance_tftp`` function that returns an instance
of `~vinegar.http.server.HttpRequestHandler` or
`~vinegar.tftp.server.TftpRequestHandler` respectively.

.. warning::

  When implementing a custom request handler, be aware that the servers do not
  decode or sanitize the request path. Each request handler is responsible for
  URL decoding the request path and ensuring that it is not vulnerable to
  directory traversal attacks or other similar attacks.

Two different request handlers are bundled with Vinegar:

The `~vinegar.request_handler.file` request handler serves resources from the
file system. This can either be a single file or a whole directory of files.
Files may be served as is, or they may be rendered as :ref:`templates
<concepts_templates>`. When rendering files as templates, the request path can
contain a system ID or another mean of identifying a specific system. In this
case, the data (as provided by the :ref:`data sources <concepts_data_sources>`)
for this system is made available to the template through the ``data`` context
variable and the system's system ID is made available through the ``id`` context
variable.

Any template engine that can be instantiated through
`~vinegar.template.get_template_engine` can be used with the ``file`` request
handler. Please refer to the API reference for `vinegar.request_handler.file`
for a full list of configuration options.

The other request handler is the `~vinegar.request_handler.sqlite_update`
request handler. This request handler has a very specific purpose: It can be
used to update an SQLite database that is used by the
`~vinegar.data_source.sqlite` data source. This means that it provides a way of
dynamically updating the data associated with a system, possible from the
installer environment.

Please refer to the API reference for `vinegar.request_handler.sqlite_update` to
learn more about how this request handler can be configured to apply the desired
changes.

In the :ref:`next section <concepts_templates>` we are going to learn more about
how we can leverage the power of templates in Vinegar.
