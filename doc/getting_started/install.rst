.. _getting_started_install:

Installing the server
=====================

If you plan to run the Vinegar server on Ubuntu Linux (Ubuntu 16.04 LTS or
newer) or a modern release of Debian, you are lucky: The Vinegar source tree
also is a Debian source package that can be built with ``dpkg-buildpackage``.

If you use one of the Ubuntu releases for which we provide binary packages, you
might not even have to built the packages yourself, but can simply pick up the
binary packages that we already built for you. In this case you can skip to
:ref:`getting_started_install_deb_binary`. If you are not going to run Vinegar
on any flavor of Debian (anything that uses DPKG), you can skip the sections
about the Debian packages and continue directly with
:ref:`getting_started_install_source`.

.. _getting_started_install_deb_source:

Building Debian packages from source
------------------------------------

If there are no binary packages for the specific release of Ubuntu that you use
or if you use a different flavor or a Debian-based distribution, you might have
to build the binary packages from source.

In general, the binary packages that we provide do not contain any compiled
files, so they will most likely work with any sufficiently recent Debian-based
distribution, but if you experience problems, you might want to try building the
packages from source.

Luckily, this is very simple. You simply unpack the source tree of the Vinegar
release that you want to build and change into that directory. Inside that
directory, you simply run ``dpkg-buildpackage``. This command is provided by the
package ``dpkg-dev``, so you might have to install that package first.

Vinegar has a couple of build-time dependencies, but ``dpkg-buildpackage`` will
tell you about those, so you can simply install those dependencies (at least for
Ubuntu, they are all available from the standard package repositories) and run
``dpkg-buildpackage`` again.

When ``dpkg-buildpackage`` is done, you will see an error message like
``dpkg-buildpackage: error: failed to sign .dsc file``. This is not a problem,
it simply means that the binary packages that have been build are not signed,
but if you are going to install them manually, this is not an issue.

.. _getting_started_install_deb_binary:

Installing the binary Debian packages
-------------------------------------

Regardless of whether you downloaded the binary packages or you
:ref:`built them yourself <getting_started_install_deb_source>`, you will have
the following binary packages:

* ``python3-vinegar``: This package contains all the Python module of Vinegar.
  It is a dependency of the ``vinegar-server`` package, but it can also be
  installed on its own if you have code using the :ref:`Vinegar API <api>`, but
  do not want to run the Vinegar server on the same machine.

* ``vinegar-doc``: This package contains the documentation for Vinegar. This is
  the documentation that you are reading right now. You can install it if you
  want to have access to the documentation without need access to the Internet.

* ``vinegar-server``: This package contains the actual Vinegar server. As the
  Python code is already provided by ``python3-vinegar``, this package only
  provides a start script a Systemd unit file, and an example configuration
  file. It also contains a configuration file for logrotate, so that log files
  written by the server will not accumulate.

If you have added these packages to a local Apt repository, you can simply
install the Vinegar server by running

.. code-block:: sh

  apt-get-install vinegar-server

This will also install the ``python3-vinegar`` package. Otherwise, you have to
install both packages manually by running

.. code-block:: sh

  dpkg -i python3-vinegar_x.x.x_all.deb vinegar-server_x.x.x_all.deb

The Vinegar server is automatically started after the ``vinegar-server`` package
has been installed. You can find its configuration in ``/etc/vinegar`` and its
log files in ``/var/log/vinegar``.

Now that the Vinegar server is running, you can skip to the
:ref:`getting_started_install_config` section or you can read the next section
to learn more about the things of which the Debian package already took care.

.. note::

  The ``vinegar-server`` package provides a configuration file for Systemd that
  is used to start the server. If you are using a distribution that uses an
  alternative init system, you have to start the server yourself. The
  :ref:`getting_started_install_source` section has a few hints about how you
  might do this. Please note that in case of the Debian package, the
  ``vinegar-server`` executable can be found in ``/usr/sbin/vinegar-server``.

.. _getting_started_install_source:

Installing Vinegar from source (on non-Debian systems)
------------------------------------------------------

Vinegar can be built and installed using
`Setuptools <https://pypi.org/project/setuptools/>`_. Usually, it should be
sufficient to run

.. code-block:: sh

  python3 setup.py install

This should install the dependencies of Vinegar
(`Jinja2 <https://pypi.org/project/Jinja2/>`_ and
`PyYAML <https://pypi.org/project/PyYAML/>`_) copy the Python modules for
Vinegar into a directory that is included in the ``PYTHONPATH`` and create a
``vinegar-server`` script that can be used to start the Vinegar server. On
Linux, this script will typically be created in ``/usr/bin`` or
``/usr/local/bin``. On Windows, it will typically be created in the ``Scripts``
sub-directory of the Python installation directory.

Vinegar needs a server configuration file. On Windows, this file is expected in
``C:\Vinegar\conf\vinegar-server.yaml``. On all other platforms, it is expected
in ``/etc/vinegar/vinegar-server.yaml``. The path can be overridden by passing
the ``--config-file`` argument to ``vinegar-server``. For example:

.. code-block:: sh

  vinegar-server --config-file=path/to/my/config-file.yaml

An example configuration is going to be discussed in the
:ref:`next section<getting_started_install_config>`.

Typically, you will not want to run the server manually from a console, but have
it start automatically as a system service. When using a Linux distribution that
uses Systemd as its init system, you can use a unit file like the following (the
Debian package uses a very similar definition):

.. code-block:: ini

  [Unit]
  Description=Vinegar Boot Server
  After=network.target

  [Service]
  ExecStart=/usr/bin/vinegar-server
  Restart=on-failure
  RestartSec=5s

  User=vinegar
  Group=vinegar

  CapabilityBoundingSet=CAP_NET_BIND_SERVICE
  AmbientCapabilities=CAP_NET_BIND_SERVICE

  [Install]
  WantedBy=multi-user.target

In order for this unit file to work, you have to create the ``vinegar`` user and
group and have to use Linux kernel 4.3 or newer. For older kernel versions, the
``AmbientCapabilities`` option does not work, so that the server does not get
the ``CAP_NET_BIND_SERVICE`` capability. This capabilitiy is needed in order to
bind to TCP and UDP ports below 1024. While the HTTP server can reasonably be
bound to a different port, this is not a good option for the TFTP server because
PXE clients will expect it to listen on the default port (UDP port 69). This
means that on a system where you cannot use ``AmbientCapabilities``, you will
have to run the server as ``root`` (not recommended) or find an alternative way
of binding to a privileged port, like
`authbind <https://en.wikipedia.org/wiki/Authbind>`_.

If running on a distribution that uses an alternative init system you will have
to find a different solution for starting the server. One option might be
running it inside a `Screen <https://www.gnu.org/software/screen/>`_ session. In
this case, you will probably have to use authbind, too.

.. _getting_started_install_config:

Server configuration
--------------------

If you installed the Vinegar server as a Debian package, congratulations, an
example configuration file has already been created for you. Otherwise, you have
to create the configuration file (typically as
``/etc/vinegar/vinegar-server.yaml`` see the
:ref:`preceding section<getting_started_install_source>` for details).

Here is the full example file so that you can copy and paste it. There are some
comments in the file, but we will also discuss it in this section.

This file does not work on its own. It needs a second file that describes the
logging configuration and is discussed in the sub-section
:ref:`getting_started_environment_logging`.

.. code-block:: yaml

  # List of data sources.
  # The data sources are processed in order: Data from data sources earlier in the
  # list is provided to data sources later in the list. Data from data sources
  # later in the list overrides data from data sources earlier in the list.
  data_sources:
    # The first data source reads the file /srv/vinegar/systems/list.txt,
    # expecting one line for every system. Each line has the following format:
    #
    # <MAC address>:<IPv4 address>:<hostname>[,<extra name 1>,<extra-name 2>,...]
    #
    # This format can be customized by change the configuration for the data
    # source. Please refer to the documentation for the text_file data source for
    # a full list of available configuration options.
    - name: text_file

      # We set the filename to /srv/vinegar/systems/list.txt.
      file: /srv/vinegar/systems/list.txt

      # This is the regular expression that matches the lines that we want to use.
      # We specify the X flag first (?x) so that we can use the multi-line syntax,
      # which makes the regular expression much more readable.
      regular_expression: |
          (?x)
          # We expect a CSV file with three columns that are separated by
          # semicolons.
          # The first column specifies the MAC address.
          (?P<mac>[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5});
          # The second column specifies the IP address.
          (?P<ip>[0-9]{1,3}(?:\.[0-9]{1,3}){3});
          # The third column specifies the hostname and an optional list of
          # additional names.
          (?P<hostname>[^,]+)
          (,(?P<extra_names>.+))?

          # We want to ignore empty lines and lines starting with a "#".
      regular_expression_ignore: "|(?:#.*)"

      # We build the system ID from the hostname by adding a domain name and
      # ensuring that everything is in lower case.
      system_id:
        source: hostname
        transform:        
          - string.add_suffix: .mydomain.example.com
          - string.to_lower

      # We define a couple of variables that will be available in the data tree
      # for each system.
      variables:
        'info:extra_names':
          source: extra_names
          transform:
            - string.to_lower
            - string.split: .
        'net:fqdn':
          source: hostname
          transform:
            - string.add_suffix: .mydomain.example.com
            - string.to_lower
        'net:hostname':
          source: hostname
          transform:
            - string.to_lower
        'net:ipv4_addr':
          source: ip
          transform:
            - ipv4_address.normalize
        'net:mac_addr':
          source: mac
          transform:
            - mac_address.normalize

    # We use a yaml_target data source as the second source in the list. This
    # source expects a top configuration file /srv/vinegar/datatree/top.yaml and
    # includes further files bases on the configuration in that file. As the
    # text_file data source is earlier in the list, the data from that data source
    # can be used in the files for the yaml_target data source through Jinja
    # template syntax (e.g. "{{ data.get('net:macaddr') }}").
    - name: yaml_target
      root_dir: /srv/vinegar/datatree

    # As the last source, we use an sqlite data source. This data source allows us
    # to update single pieces of data in a safe way (ensuring that these updates
    # become visible immediately). We use the same database as the HTTP request
    # handler later in this file, so that we can use data items updates by that
    # request handler.
    - name: sqlite

      # We use a database stored in /var/lib/vinegar/system-state.db.
      db_file: /var/lib/vinegar/system-state.db

      # We disable the find_system function for this data source because it only
      # stores flags that are not really useful for a reverse lookup.
      find_system_enabled: False

      # We store the data for this data source under a separate key in order to
      # avoid collissions with keys from other sources.
      key_prefix: state 

  # Lists in the data provided by data sources is not merged by default. Instead,
  # if a data source later in the list of data sources provides a list for the
  # same key as a data source earlier in the list, the list from the data source
  # that is later in the list completely replaces the list from the data source
  # earlier in the list. This can be changed by setting this option to True.
  # data_sources_merge_lists: False

  # Configuration for the HTTP server.
  http:
    # The HTTP server binds to all local interfaces by default.
    # bind_address: '::'
    
    # The HTTP server binds to port 80 by default.
    # bind_port: 80
    
    # The list of request handlers is processed in order, using the first handler
    # that matches.
    request_handlers:

      # We register a request handler that serves files after rendering them
      # through the Jinja template engine. This allows us to use data from the
      # data sources defined above in that files.
      - name: file

        # We have to define a request path. The files served by this request
        # handler are going to be available at
        # http://vinegar-server.example.com/templates/<system ID>/...
        request_path: /templates/...

        # We expect the system-ID to be specified as part of the request path.
        # This information is used to decide for which system a file should be
        # rendered.
        lookup_key: ':system_id:'

        # We use files in /srv/vinegar/http/templates as the templates.
        root_dir: /srv/vinegar/http/templates

        # We want to render the files with the Jinja template engine.
        template: jinja

      # We register a second request handler that can be used to reset the
      # 'netboot_enabled' flag in the SQLite database. This way, we can reset this
      # flag from an installer environment in order to avoid booting into the
      # installer again.
      - name: sqlite_update

        # This request handler is going to be available at
        # http://vinegar-server.example.com/reset-netboot-enabled/<system ID>
        request_path: /reset-netboot-enabled

        # This request handler uses the same database file as the sqlite datasource
        # defined earlier.
        db_file: /var/lib/vinegar/system-state.db

        # This handler deletes the data for the 'netboot_enabled' key, effectively
        # resetting the flag.
        action: delete_data
        key: netboot_enabled

        # We only allow a client to use this request handler if its IP address
        # matches the one for the targeted system. We know the IP address because
        # the text_file data source that we defined earlier provides it.
        client_address_key: 'net:ipv4_addr'

  # Path to the logging configuration.
  logging_config_file: /etc/vinegar/vinegar-server-logging.ini

  # Configuration for the TFTP server.
  tftp:
    # The TFTP server binds to all local interfaces by default.
    # bind_address: '::'
    
    # The TFTP server binds to port 69 by default. While you can change this port
    # number, most PXE clients will only use that port, so it will usually not be
    # useful to bind to a different one.
    # bind_port: 69
    
    # The list of request handlers is processed in order, using the first handler
    # that matches.
    request_handlers:

      # We register a request handler that serves files after rendering them
      # through the Jinja template engine. This allows us to use data from the
      # data sources defined above in that files.
      - name: file

        # We have to define a request path. The files served by this request
        # handler are going to be available at
        # tftp://vinegar-server.example.com/templates/<MAC address>/...
        request_path: /templates/...

        # We expect the MAC address to be specified as part of the request path.
        # This information is used to find the system ID which in turn allows us
        # to decide for which system a file should be rendered. We cannot use the
        # system ID directly because we will typically not know it in the PXE
        # environment, but the MAC address is known (e.g. $net_default_mac in
        # GRUB 2). The lookup the the MAC address works because the text-file
        # based data source defined earlier knows the MAC address for each system.
        lookup_key: 'net:mac_addr'

        # The MAC address specified by the client might not necessarily use the
        # same formatting as the data source, so we normalize the MAC address in
        # order to avoid false negatives.
        lookup_value_transform:
          - mac_address.normalize

        # We use files in /srv/vinegar/tftp/templates as the templates.
        root_dir: /srv/vinegar/tftp/templates

        # We want to render the files with the Jinja template engine.
        template: jinja

        # We want to use this request handler to load parts of the GRUB
        # configuration. This means that a problem with this handler could result
        # in a system getting stuck at the GRUB boot screen. We want to avoid this
        # at all cost, so we rather render a template without having
        # system-specifc data than not being able to fulfill the request. The
        # template files obviously have to be written in a way that they can
        # handle situation where there is no system data (and as a result the id
        # and data context objects are not available). We still want to log a
        # warning if such a situation appears so that we can fix the problem that
        # causes it in the first place.
        data_source_error_action: warn
        lookup_no_result_action: continue

    # We register two more request handler that serve static files without
    # rendering them as templates. We need these handler for two reasons. First,
    # we cannot render binary files (like the boot loader or kernel images) as
    # templates as this would corrupt them. Second, we do not know the MAC
    # address yet when loading the initial parts of the boot loader (the path
    # to these parts is fixed in the DHCP configuration).
    # The first handler is used for the files belonging to GRUB.
    - name: file

      # We have to define a request path. The files served by this request
      # handler are going to be available at
      # tftp://vinegar-server.example.com/grub/...
      request_path: /grub

      # We serve files from /srv/vinegar/tftp/grub.
      root_dir: /srv/vinegar/tftp/grub

    # The second request handler is used for installer files like the kernel
    # images and initial ramdisks.
    - name: file
      request_path: /images
      root_dir: /srv/vinegar/tftp/images

We are not going to discuss all the option that can be used in the configuration
file. For a full list of options supported by the server, please refer to the
API reference for `vinegar.cli.server`. For the options supported by the various
sub-components, please refer to their respective API reference (there are
pointers to them in the following paragraphs).

Data sources
^^^^^^^^^^^^

The first section of the file defines the
:ref:`data sources <concepts_data_sources>`. In this example, we define three
data sources.

The first data source is of type `~vinegar.data_source.text_file`. From a
configuration perspective, it is the most complex data source type:

.. code-block:: yaml

    - name: text_file
      file: /srv/vinegar/systems/list.txt
      regular_expression: |
          (?x)
          (?P<mac>[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5});
          (?P<ip>[0-9]{1,3}(?:\.[0-9]{1,3}){3});
          (?P<hostname>[^,]+)
          (,(?P<extra_names>.+))?
      regular_expression_ignore: "|(?:#.*)"
      system_id:
        source: hostname
        transform:        
          - string.add_suffix: .mydomain.example.com
          - string.to_lower
      variables:
        'info:extra_names':
          source: extra_names
          transform:
            - string.to_lower
            - string.split: .
        'net:fqdn':
          source: hostname
          transform:
            - string.add_suffix: .mydomain.example.com
            - string.to_lower
        'net:hostname':
          source: hostname
          transform:
            - string.to_lower
        'net:ipv4_addr':
          source: ip
          transform:
            - ipv4_address.normalize
        'net:mac_addr':
          source: mac
          transform:
            - mac_address.normalize

This complexity comes from the fact that it is designed to work with almost any
text file as its source of data. When you have a text file that contains one
line per system, this data source is almost certainly able to process it.

The configuration above is designed to match a text file in the following
format:

.. code-block:: text

  # Lines starting with a # are ignored.
  02:00:00:00:00:01;192.0.2.1;myhost1
  # Empty lines are ignored as well.

  02:00:00:00:00:02;192.0.2.2;myhost2
  02:00:00:00:00:03;192.0.2.1;myhost3,alias-for-myhost3

The format of lines containing data is configured through the
``regular_expression`` option. It typically makes sense to specify the ``(?x)``
option at the start of the expression. This has the consequence that whitespace
outside character classes and comments are ignored, so the regular expression
(which might be quite complex) can be formatted nicely.

We do not discuss the details of writing regular expressions here, please refer
to the documentation of |Python's re module|_ for that. We are just going to
have quick look at the regular expression that we use in this example.

.. |Python's re module| replace:: Python's ``re`` module
.. _Python's re module: https://docs.python.org/3/library/re.html

As already said, the first line enables the multi-line mode. The second line of
the expression matches the first column in the text file and puts it into a
catching group with the name ``mac``. This way, we can refer to this group by
name from the variable definitions later in the configuration. If we used an
unnamed catching group, we could still refer to it by its integer index, but
this would be less comfortable.

The third line matches the second column, which stores the IP address, and makes
it available in the ``ip`` group.

The fourth line matches the first name in the third column and makes it
available as the ``hostname`` group.

The final line matches more names in the third column and makes them available
in the ``extra_names`` group.

The ``regular_expression_ignore`` option specifies a regular expression of lines
that shall be ignored. In this example, we ignore lines that start with a ``#``
or are empty.

The ``system_id`` option defines how the system ID is extracted from a line. The
concept of System IDs is described in :ref:`concepts`. The system ID is
generated by using the value of the capturing group that is identified through
the ``source`` option and then (optionally) transformed using the
transformations specified through the ``transform`` option. In this example, we
add a suffix to the extracted string (so that we get an FQDN) and make sure that
the resulting string is all lower case.

The main purpose of a data source is providing data associated with a system ID.
For the ``text_file`` data source, this data is configured through the
``variables`` option. In this example, we define four variables that (like the
system ID) are generated by using the value of one of the capturing groups and
transforming it. The name of the variables defines the key in the resulting data
dictionary. In this example, the variable name ``net:fqdn`` will cause the data
to be made available under the key ``fqdn`` inside a dictionary that is stored
under the key ``net`` in the top data dictionary.

We do not discuss all of the configuration options of the
`~vinegar.data_source.text_file` data source here. Please refer to the API
documentation for a list of all supported options and their meaning.

The second data source that we define in the example configuration is a
`~vinegar.data_source.yaml_target` data source. The configuration for this data
source looks fairly simple:

.. code-block:: yaml

    - name: yaml_target
      root_dir: /srv/vinegar/datatree

The only option that has to be specified is the ``root_dir`` which is where the
data source finds the files which contain the data.

While the configuration for this data source is quite simple, it is still a very
powerful type of data source. The files used by this data source are YAML files
that are rendered as :ref:`templates <concepts_templates>`. The regular way of
how this data source maps systems to their data is by matching the system IDs
with patterns, but thanks to templating, it is possible to use more complex
matching using data from the earlier data sources.

For example, we could use the IP address of a system (provided by the
``text_file``) data source in a template expression to decide whether a certain
piece of data is used for a system or not. In fact, we could even calculate data
based on that data (e.g. calculate a broadcast address matching the IP address).

We will discuss examples of how this data source can be used in
:ref:`getting_started_environment`. For more information about the optional
configuration options and the file format, please refer to the
`~vinegar.data_source.yaml_target` API reference.

The third and last data source that we define in the example configuration is an
`~vinegar.data_source.sqlite` data source.

.. code-block:: yaml

    - name: sqlite
      db_file: /var/lib/vinegar/system-state.db
      find_system_enabled: False
      key_prefix: state 

The only mandatory option for this data source is the path to the ``db_file``.
The database file is created if it does not exist yet. Inside this file, the
data source uses a single table for storing the data associated with each
system.

Unlike the other two data sources, this data source does not use any caching.
This means that even changes that happen in rapid succession and are thus not
detectable by changes in the time stamp of the file (the primary way of how
changes are detected for the other data sources), are reliably detected by this
data source. The fact that SQLite implements safe transactions across multiple
processes also makes it safe for concurrent updates.

We are going to use this data source to store a flag indicating whether a system
should boot into the installer or boot locally. In
:ref:`getting_started_environment_netboot_enabled`, we are going to write a very
simple script that we use to set this flag inside the database. The same flag
will be reset by an HTTP request handler that we are going to discuss later in
this section.

HTTP request handlers
^^^^^^^^^^^^^^^^^^^^^

The HTTP request handlers are defined in the ``request_handlers`` sub-section of
the ``http`` section. We define two request handlers.

The first request handler is a `~vinegar.request_handlers.file` request handler
that serves files that are rendered as templates using the
`~vinegar.template.jinja` template engine.

.. code-block:: yaml

      - name: file
        request_path: /templates/...
        lookup_key: ':system_id:'
        root_dir: /srv/vinegar/http/templates
        template: jinja

For this request handler, we specify a request path of ``/templates/...``. The
elipsis in this request path is used as a placeholder for the system ID. This is
specified through the ``lookup_key`` option. What this means is that a request
to ``/templates/myhost.example.com/myfile.txt`` will render the file
``/srv/vinegar/http/templates/myfile.txt`` as a template and provide it with the
data from the data sources defined earlier for the system ID
``myhost.example.com``.

The ``root_dir`` option specifies the directory where the template files are
located. The ``template`` option specifies the name of the template engine that
is used. If not specified, the files are not rendered as templates and instead
they are served with their exact content. That mode is suitable when serving
binary files that would be corrupted when being processed by a template engine.
Like nearly everything in Vinegar, the template engine is pluggable, the
``jinja`` engine is simply the default engine provided by Vinegar, but you can
easily add more template engines. For details please refer to
:ref:`concepts_templates`.

For a full list of configuration options, please refer to the API reference for
the `~vinegar.request_handlers.file` request handler.

We define a second request handler of type
`~vinegar.request_handlers.sqlite_update`.

.. code-block:: yaml

      - name: sqlite_update
        request_path: /reset-netboot-enabled
        db_file: /var/lib/vinegar/system-state.db
        action: delete_data
        key: netboot_enabled
        client_address_key: 'net:ipv4_addr'

This request handler has a very simple job: Whenever it receives a request to
its ``request_path`` (with a system ID appended. like
``/reset-netboot-eabled/myhost.example.com``), it deletes the
``netboot_enabled`` flag from the entry for ``myhost.example.com`` in the SQLite
database that is stored in the ``db_file``.

This behavior is specified by setting ``action`` to ``delete_data`` and ``key``
to ``netboot_enabled``.

As a security measure, the request is only allowed if the HTTP client's IP
address matches the value of the key specified in the
``client_address_key`` option. For this check, the handler requests the system
data for the specified system ID from the data sources and then looks for the
specified key. In this example, the request handler looks for a value with the
key ``ipv4_addr`` that is stored inside a dictionary that is stored under the
``net`` key in the top data structure. As you might remember, this is exactly
the place where the ``text_file`` data source that we defined earlier stores a
system's IP address.

Effectively, this means that a system is only allowed to reset the
``netboot_enabled`` flag for itself. It cannot do this for a different system
because the IP addresses will not match.

There are more configuration options. For example, a different action can be
used to set (instead of delete) a value inside the database. Please refer to the
API reference for the `~vinegar.request_handlers.sqlite_update` request handler
for details.

.. _getting_started_environment_logging:

Logging
^^^^^^^

The Vinegar server uses a logging system to provide you with information about
what is happening and the stack traces of exceptions when something fails. This
information can be invaluable when you try to figure out why something does not
work as expected.

In the example configuration, we specify the path to a file with the logging
configuration:

.. code-block:: yaml

  logging_config_file: /etc/vinegar/vinegar-server-logging.ini

This file is distributed with the Debian package and has the following content
by default:

.. code-block:: ini

  [loggers]
  keys=root

  [handlers]
  keys=file

  [formatters]
  keys=default

  [logger_root]
  level=INFO
  handlers=file

  [handler_file]
  class=handlers.WatchedFileHandler
  level=NOTSET
  args=('/var/log/vinegar/server.log',)
  formatter=default

  [formatter_default]
  format=%(asctime)s [%(name)s] [%(levelname)s] %(message)s

This file uses the format specified in Pythons |logging.config|_ module. In the
example configuration, we specify a single logger that logs everything at a
level of ``INFO`` (this also includes ``WARNING``, ``ERROR``, and ``CRITICAL``
messages) to the file ``/var/log/vinegar/server.log``. For obvious reasons, the
user that runs the Vinegar server needs sufficient permissions to actually write
to this file.

.. |logging.config| replace:: ``logging.config``
.. _logging.config: https://docs.python.org/3/library/logging.config.html#logging-config-fileformat

As an alternative to the ``logging_config_file`` option, one can specify the
``logging_level`` option. That option simply takes the name of a log level
(e.g. ``INFO``) as its value. If this option is used, messages of the specified
level (and higher levels) are written to the standard output.

If neither of the two logging options is used, the server writes log messages
with a level of ``INFO`` or higher to the standard output by default.

TFTP request handlers
^^^^^^^^^^^^^^^^^^^^^

The TFTP request handlers are defined in the ``request_handlers`` sub-section of
the ``http`` section. The request handler configuration works in the same way as
for HTTP request handlers. In the example configuration, we define three request
handlers.

The first request handler is a `~vinegar.request_handlers.file` request handler
that serves files that are rendered as templates using the
`~vinegar.template.jinja` template engine.

.. code-block:: yaml

      - name: file
        request_path: /templates/...
        lookup_key: 'net:mac_addr'
        lookup_value_transform:
          - mac_address.normalize
        root_dir: /srv/vinegar/tftp/templates
        template: jinja
        data_source_error_action: warn
        lookup_no_result_action: continue

The ``request_path`` is set to ``/templates/...`` and the ``lookup_key`` is set
to ``net:mac_addr``. This means that a request to
``/templates/02:00:00:00:00:01/myfile.txt`` will try to find a system that has
its ``net:mac_addr`` variable set to ``02:00:00:00:00:01``.

Due to the ``root_dir`` option being set to ``/srv/vinegar/tftp/templates``, the
request handler will then take the file
``/srv/vinegar/tftp/templates/myfile.txt`` and render it with the specified
``template`` engine (the `~vinegar.template.jinja` engine is this example).

As part of this rendering process, the data for the system identified by its MAC
address is going to be made available. When looking for a system with the MAC
address specified as part of the request path, the MAC address is normalized
using the `vinegar.transform.mac_address.normalize` transformation. For example,
this means that a request to ``/templates/02-00-00-00-00-0a`` will result in a
lookup for the MAC address ``02:00:00:00:00:0A``.

You might rembember that we also normalized the MAC addresses in the
configuration of the ``text_file`` data source. This means that regardless of
which format is used in the text file and in the request path (e.g. upper or
lower case, ``:`` or ``-`` as the separator) there will be a match as long as
both essentially specifiy the same address.

In this example, the ``data_source_error_action`` is set to ``warn``. This has
the consequence that if one of the data sources raises an exception, this will
not make the whole request fail. Instead, the template will be rendered without
the system data available.

Setting ``lookup_no_result_action`` to ``continue``, has a similar consequence:
If no system can be found for the MAC address specified in the request path, the
template is also rendered without system data.

This has the advantage that a problem with one of the data sources (or a system
missing in the text file) will not lead to an error and the system will instead
receive some default content defined in the template for that case. This can be
useful if the template file is included by the boot loader configuration and
would cause the boot process to stall if it could not be read from the server.
For this case, the template file might provide some default content that causes
the boot loader to boot from the local disks instead.

The second and third request handler also are instances of the
`~vinegar.request_handlers.file` request handler.

.. code-block:: yaml

    - name: file
      request_path: /grub
      root_dir: /srv/vinegar/tftp/grub

    - name: file
      request_path: /images
      root_dir: /srv/vinegar/tftp/images

In contrast to the first instance, these request handlers do not render files
as templates. For this reason, they are suitable for serving binary files like
the boot loader or kernel images.

Now that we have a configuration file for the server, we can continue with
setting up the :ref:`environment <getting_started_environment>` for the boot
process.
