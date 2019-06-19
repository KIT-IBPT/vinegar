.. _concepts_data_sources:

Data sources
============

Data sources are Vinegar's way of providing system-specific configuration data.
Users familar with `SaltStack <https://www.saltstack.com/>`_ may find that the
concept is very similar to Salt's pillar. In particular, the
`~vinegar.data_source.yaml_target` data source uses files that look a lot like
Salt's SLS files. This is not a coincidence: Vinegar has specifically been
designed with the concept of Salt's pillar in mind.

In Vinegar, one typically uses more than one data source. All configured data
sources form a stack, represented by a
`~vinegar.data_source.CompositeDataSource`. When starting the Vinegar server,
the `server CLI <vinegar.cli.server>` creates the composite data source by
calling `~vinegar.data_source.get_composite_data_source` with the configuration
from the server configuration file.

This composite data source is then injected into other components that need it
and indicate that by implementing the `~vinegar.data_source.DataSourceAware`
interface.

Each data source provides two methods:

The `~vinegar.data_source.DataSource.get_data` method returns the data for a
specific system. In case of the composite data source, the ``get_data`` method
is called for each of the data sources in order, passing the merged data from
the preceding sources to each data source.

The `~vinegar.data_source.DataSource.find_system` method, in contrast, is used
to find the system ID for a system identified by a unique piece of data (e.g. a
MAC or IP address). This method is only implemented by some of the data sources.
If a data source finds a match, the returned system ID is used. Otherwise, the
next data source in the chain is tried.

Vinegar comes bundled with three types of data sources: The
`~vinegar.data_source.sqlite`, `~vinegar.data_source.text_file`, and
`~vinegar.data_source.yaml_target` data source. Of these three, the last one is
the one that is typically used for most configuration data as it has the highest
degree of flexibility.

If none of the three data sources matches the needs for a certain scenario, it
is very simple to implement a custom data source. The API reference for the
`vinegar.data_source` module has all the necessary information.

SQLite data source
------------------

The `~vinegar.data_source.sqlite` data source provides per-system information
stored inside an SQLite database. This makes it suitable for serving
configuration data that changes frequently.

In particular, this data source is designed to work hand in hand with the
`~vinegar.request_handler.sqlite_update` request handler to allow dynamic
configuration updates triggered by clients.

The :ref:`getting_started` chapter contains an example of how this data source
can be used, if you want to learn more about the various options, please refer
to the API reference for `vinegar.data_source.sqlite`.

Text file data source
---------------------

The `~vinegar.data_source.text_file` data source is well suited for providing
pieces of data that are different for each system (like hostnames and IP or MAC
addresses). It can read virtually any text file as long as this text file is in
a format where there is one line for each system.

The `~vinegar.data_source.text_file` source extracts that information using
regular expressions and (if needed) further transforms it using
:ref:`transformations <concepts_transformations>`.

This data source allows reverse lookups using ``find_system``. This means that
is not just possible to get the data for a certain system, but also possible to
find the system ID of a system where a specific piece of data has a specific
value. For example, if the text file provides that information, it is possible
to find a system through its MAC address.

The :ref:`getting_started` chapter contains an example of how this data source
can be used, if you want to learn more about the various options, please refer
to the API reference for `vinegar.data_source.text_file`.

YAML target source
------------------

The `~vinegar.data_source.yaml_target` data source is very flexible. Groups of
systems can be targeted by matching their system IDs with patterns and the files
providing the data actually are templates that can use complex logic for
generating that data. Users familar with the SLS file syntax used for Salt's
pillar will find the concept very familiar.

However, the flexibility offered by this data source comes at a price: Providing
configuration data that only matches one individual system (in contrast to a
group of systems) is rather tedious when having to do this for a lot of systems
because it requires the creation of a separate file for each system. For this
reason, it is usually best to combine a `~vinegar.data_source.yaml_target`
source with a `~vinegar.data_source.text_file` source, using the first for the
configuration data shared by many systems and the second for the data associated
with single systems (like hostnames and MAC or IP addresses).

Another downside of the `~vinegar.data_source.yaml_target` source is that it
does not support the ``find_system`` method: As the system ID needs to be known
in order to decide which files to consider, this data source cannot do a reverse
lookup and find the system ID for which a key is set to a specific value. As
explained in the last paragraph, setting individual pieces of data is tedious
anyway when using the `~vinegar.data_source.yaml_target` source, so this
restriction is rather a theoretical one.

When you have read the :ref:`getting_started` chapter, you have already seen a
small example of how the `~vinegar.data_source.yaml_target` source can be
configured. Please refer to the API reference for
`vinegar.data_source.yaml_target` to learn more about the various configuration
options and details about the file format used by this data source.

After we have learned something about the four basic components that form the
backbone of Vinegar, we are going to learn something about transformations, that
are a support component to the other components, in the :ref:`next section
<concepts_transformations>`.
