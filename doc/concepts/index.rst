.. _concepts:

Concepts
========

.. toctree::
  :maxdepth: 1
  :caption: Contents:

  servers
  request_handlers
  templates
  data_sources
  transformations

In this chapter, we are going to explore the concepts behind Vinegar. After
reading it, you should have a better understanding of how the different
components work together and which options might fit your scenario.

The Vinegar server (`vinegar.cli.server`) is just a simple piece of software
that reads a configuration file and - based on this configuration - instantiates
four differnt kinds of components. When you read the :ref:`getting_started`
chapter, you already came in touch with all these components, maybe without
realizing it.

The first component are the actual servers that serve HTTP
(`vinegar.http.server`) and TFTP (`vinegar.tftp.server`) requests. These servers
merely implement the low-level protocol handling. The actual request handling is
delegated to the second component, the request handlers. We have a closer look
at the servers in :ref:`concepts_servers`.

The request handlers (`vinegar.request_handlers`) deal with actually handling
the requests received via the HTTP or TFTP server. Depending on the type and
configuration of the request handler, the handling might end there, or it might
involve the third and fourth component. Vinegar comes with two types of request
handlers. The `~vinegar.request_handler.file` request handler is the predominant
one. It supports both HTTP and TFTP and can either serve static files or render
templates. The `~vinegar.request_handler.sqlite_update` request handler has a
very specific purpose: It is used to modify entries in an SQLite database. In
:ref:`getting_started`, we already saw an example of how that handler can be
used. The :ref:`concepts_request_handlers` section gives more information
about request handlers.

When a request handler renders templates, template engines (`vinegar.template`),
which are the third component, are involved. Exactly one template engine comes
bundled with Vinegar: The `~vinegar.template.jinja` engine. This engine is quite
powerful and unless you want to use a different template language because you
are already familiar with it, Jinja will typically fulfill all your needs. In
:ref:`concepts_templates`, we learn more about how Vinegar uses templates.

Templates are so powerful in Vinegar because they can use data from the fourth
component, the data sources (`vinegar.data_source`). There are three kinds of
data sources that are bundled with Vinegar: The `~vinegar.data_source.sqlite`
data source gets its data from an SQLite database. The
`~vinegar.data_source.text_file` gets its data from a CSV-style text file and
thanks to its flexible configuration it can be adapted to read almost any kind
of file. The `~vinegar.data_source.yaml_target` source supports a flexible
targeting mechanism that can be used to dynamically build the configuration for
each system by assembling it from smaller bricks of data. We are going to
discuss the role of data sources in :ref:`concepts_data_sources`.

In order to uniquely identify a booting system across various components, system
IDs play a vital role. While technically, these IDs can be arbitrary strings, it
is strongly suggested to use a system's fully qualified domain name (FQDN) as
the system ID. This both ensures that system IDs are actually unique and makes
targeting based on things like a hostname prefix or a domain name suffix easy.

In requests, a system is either identified by its system ID or by another piece
of data that uniquely identifies this system (e.g. a MAC address or IP address).
In the latter case, :ref:`data sources<concepts_data_sources>` are used to
resolve this piece of data into a system ID.

Before we look into the data sources, we are going to learn something about the
HTTP and TFTP servers in the :ref:`next section <concepts_servers>`.
