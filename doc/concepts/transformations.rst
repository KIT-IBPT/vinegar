.. _concepts_transformations:

Transformations
===============

In contrast to the four other components that we have discussed so far in the
:ref:`concepts` chapter, transformations are not really a separate component.
They rather constitute a set of simple but very useful functions that help with
converting data.

In general, there are two places where transformations can be used: They can be
used from templates (at least when using the :ref:`Jinja
<concepts_templates_jinja>` template engine) or they can be used as part of the
configuration of other components, most importantly the
`~vinegar.data_source.text_file` data source and the
`~vinegar.request_handlers.file` request handler.

When used from templates, they are simply called like regular functions. When
used in the configuration of another component, they are used by providing a
chain of functions that shall be applied on a value.

For example, a transformation chain that converts a hostname to lower case and
appends a domain name, might look like this:

.. code-block:: yaml

  - string.to_lower
  - string.add_suffix: .mydomain.example.com

As you can see from this example, a chain is specified as a list of functions.
In the simplest case (a function that takes the value to be transformed as its
only argument, like `~vinegar.transform.string.to_lower`), the item in the list
simply is a string identifying the function.

If the function takes a second argument (like the
`~vinegar.transform.string.add_sufix`) function, the list item is a `dict` with
exactly one entry, using the function name as the key and the second argument as
the value.

If the function takes more than two arguments, the extra arguments can be passed
as positional or keyword arguments. Obviously, this also works with function
that only take a single or two arguments, but that syntax is more verbose.

For example, the transformation chain could also be written like this, using
explicit positional arguments:

.. code-block:: yaml

  - string.to_lower: []
  - string.add_suffix:
      - .mydomain.example.com

It could also be written using explicit keyword arguments:

.. code-block:: yaml

  - string.to_lower: {}
  - string.add_suffix:
      suffix: .mydomain.example.com

Obviously, in these simple cases using the more verbose syntax does not make any
sense, but it is useful when looking at a more complex case like the
`~vinegar.transform.string.split` function:

.. code-block:: yaml

  - string.to_lower
  - string.split:
      sep: ","
      maxsplit: 3

This transformation chain first converts a string to lower case and then splits
it along occurrences of the comma character (``,``), but only splits at the
first three places where this character occurs (the result is a list that never
contains more than four items).

There are some transformation functions dealing with strings, but there are also
functions dealing with IP or MAC addresses. Please refer to the list of
sub-modules in the API reference for `vinegar.transform` for a full list of
transformation functions that are bundled with Vinegar.
