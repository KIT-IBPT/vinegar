.. _concepts_servers:

Servers
=======

The `HTTP <vinegar.http.server>` and `TFTP <vinegar.tftp.server>` servers are
the entry point into Vinegar. Usually, they are not instantiated directly, but
by starting the `Vinegar server CLI <vinegar.cli.server>`.

We are not going into the details of configuring the server here. The
:ref:`getting_started` chapter already contains an example configuration file
and discusses the meaning of the various sections and a definitive guide to the
available options can be found in the `API reference <vinegar.cli.server>`.

The server CLI does not just instantiate the HTTP and TFTP servers. It also
creates the :ref:`request handlers <concepts_request_handlers>` and registers
them with the servers and creates the:ref:`data sources
<concepts_data_sources`>. If a request handler implements the
`~vinegar.data_source.DataSourceAware` interface, the server CLI injects a
reference to the composite data source (see :ref:`concepts_data_sources`) into
it.

When a server receives a request, it asks each of its request handlers whether
it can handle the request. The first request handler that can handle the request
is used and no further request handlers are asked. This is why the *order* of
request handlers matters.

The request handlers themselves are going to be discussed in the :ref:`next
section <concepts_request_handlers>`.
