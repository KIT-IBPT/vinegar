.. _concepts_templates:

Templates
=========

Templates play a vital role in Vinegar. They are used in two places: The first
place are template files that are served via the `~vinegar.request_handler.file`
request handler. The second place are the configuration files for the
`~vinegar.data_source.yaml_target` data source.

These two components do not implement the rendering of templates themselves.
Instead, they use a template engine that is retrieved using
`vinegar.template.get_template_engine`.

Usually, the `~vinegar.template.jinja`` engine that is bundled with Vinegar is
used. However, one can easily use a different template engine by providing a
custom template engine module. The API reference for `vinegar.template`
describes the interface that has to be implemented by a custom template engine.

Context objects
---------------

When rendering a template, the component calling the template engine typically
passed context objects that can be used from the template code. The template
objects that are available depend on the component that is calling the template
engine and might even depend on the runtime situation. However, there typically
are two context objects.

The ``id`` context object is of type ``str`` and provides the system ID of the
system for which the template is rendered. In the context of the
`~vinegar.data_source.yaml_target` data source, this is the system for which the
data is compiled. In case of the `~vinegar.request_handler.file` request
handler, it is the ID of the system that is specified in the request path. This
means that the ``id`` context object might not be available if the request path
did not specify a system. Please refer to the documentation for the
`~vinegar.request_handler.file` request handler for details.

The other context object is the ``data`` object. It is a ``dict`` containing all
the data relating to the system as provided by the :ref:`data sources
<concepts_data_sources>`. In case of the `~vinegar.data_source.yaml_target` data
source this is only the data provided by the data sources *preceding* the
`~vinegar.data_source.yaml_target` source because other data is obviously not
available yet when rendering the files for that data source.

Configuration
-------------

Each component that uses a template engine creates its own instance of the
template engine. This means that different configurations can be used for each
context. The content of the configuration depends on the actual template engine
that is used because each template engine might have different configuration
options.

.. _concepts_templates_jinja:

Jinja template engine
---------------------

The `~vinegar.template.jinja` template engine is the only one that is bundled
with Vinegar. It is a very powerful template engine with a rich syntax, so we
will not discuss the template engine's syntax here. Instead, readers are advised
to refer to Jinja's `Template Designer documentation
<http://jinja.pocoo.org/docs/2.10/templates/>`_.

Here, we are only going to discuss the specifics of how Jinja is implemented in
Vinegar. When using the template engine with an empty (default) configuration,
the engine automatically provides for extensions:

* ``jinja2.ext.do``: This extension provides the ``do`` tag that can be used to
  execute some code  (similar to a ``{{ ... }}`` block) without generating
  output.
* ``jinja2.ext.loopcontrols``: This extension provides the ``break`` and
  ``continue`` tags that can be used for loop control.
* ``jinja2.ext.with_``: This extension provides the ``with`` tag. Since Jinja
  2.10 this tag is available even when this extension is not loaded.
* `vinegar.template.jinja.SerializerExtension`: This extension provides tags and
  filters for dealing with JSON and YAML. Please refer to the class
  documentation for details.

The template engine also provides two global context objects:

* ``raise``: This is a function that raises a ``TemplateError`` with the
  specified message. Example: ``{{ raise('Problem detected.') }}``
* ``transform``: This is a special object that can be used like a ``dict`` to
  access all functions from the `vinegar.transform` module. For example, in
  order to normalize a MAC address, the following code can be used:
  ``{{ transform['mac_address.normalize']('02:aB:Cd:EF:01:02') }}``

As we have already learned, templates are a powerful tool in Vinegar because
they can use the data provided by data sources, so we are going to learn more
about how data sources work in the :ref:`next section<concepts_data_sources>`.
