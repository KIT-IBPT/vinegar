.. _getting_started_environment:

Adapting for your environment
=============================

After :ref:`installing and configuring the server <getting_started_install>`,
and :ref:`setting up DHCP <getting_started_dhcp>` we have to prepare the boot
environment. A minimal environment for automating the installation of a Linux
distribution typically consists of three components:

* The boot loader and its configuration files.
* The kernel image and its associated initial ramdisk.
* The preseed or kickstart file that tells the installer what to do.

We are going to use `GRUB 2 <https://www.gnu.org/software/grub/>`_ as the boot
loader. GRUB 2 is a boot loader that works both for a traditional BIOS-based
boot process and the UEFI boot process used by newer systems.

As an example for this documentation, we are going to create a configuration
that installs Ubuntu 18.04 LTS. Of course, this configuration can easily be
adapted for other releases of Ubuntu or even for completely different Linux
distributions.

Installing GRUB 2
-----------------

We starting by putting the binary files for GRUB in the right locations. The
easiest way of getting these binaries is taking a running Ubuntu 18.04 LTS
system and installing the following packages:

* grub-efi-amd64-signed
* grub-efi-ia32-bin
* grub-pc-bin
* shim-signed

At least one of the three is probably already installed on the system. We only
need the other ones to copy some files. After that, we can remove the from the
system again.

After installing these packages, we create the target directory and copy the
files that we need:

.. code-block:: sh

  grub-mknetdir --net-directory=/srv/vinegar/tftp --subdir=grub

This creates the files needed by GRUB 2 for ``i386-pc`` platform (PC BIOS boot),
the ``i386-efi`` platform (UEFI 32-bit boot), and the ``x86_64-efi`` platform
(UEFI 64-bit boot).

As we also want to support UEFI secure boot for the ``x86_64-efi`` platform, we
have to take a few extra steps:

.. code-block:: sh

  cp -a \
    /usr/lib/grub/x86_64-efi-signed/grubnetx64.efi.signed \
    /srv/vinegar/tftp/grub/x86_64-efi/grubx64.efi
  cp -a \
    /usr/lib/shim/shimx64.efi.signed \
    /srv/vinegar/tftp/grub/x86_64-efi/shimx64.efi

After copying these files, the packages that were not installed before can be
uninstalled again.

Configuring GRUB 2
------------------

In order to configure GRUB, we have to create to configuration files. The first
file has the same content for all systems. Its main purpose is to setup some
basic things that are shared for all configurations and load a second,
system-specific file.

The first file shared by all systems is saved as
``/srv/vinegar/tftp/grub/grub.cfg``:

.. code-block:: sh

  # On the PC BIOS platform, we need the biosdisk module so that chain loading
  # from the local hard disk will work.
  if [ x$grub_platform = xpc ]; then
    insmod biosdisk
  fi

  # The gfxmode is needed because some Linux installers will not work correctly
  # if GRUB has not been set to gfxmode.
  if loadfont $prefix/fonts/unicode.pf2 ; then
    set gfxmode=auto
    insmod efi_gop
    insmod efi_uga
    insmod gfxterm
    terminal_output gfxterm
  fi

  # We define some color settings to ensure that the menu is displayed properly.
  set menu_color_normal=white/black
  set menu_color_highlight=black/light-gray

  # This loads the system-specific configuration file.
  source /templates/$net_default_mac/grub.cfg

This file does not do much. It does some basic configuration for GRUB's
``gfxmode`` and loads the second configuration file. We specify the MAC address
of the interface that was used to load GRUB (which is available as
``$net_default_mac``) as part of the file path, so that the corresponding
request handler can determine the system ID.

There are more variables that are available in GRUB (please refer to the
`GRUB manual <https://www.gnu.org/software/grub/manual/grub/html_node/Network.html#Network>`_
for more information), but the MAC and IP address are about the only ones that
are available regardless of the DHCP server configuration.

For the second file, we use Jinja template syntax to make the content depend on
the system that is requesting it. We save this file as
``/srv/vinegar/tftp/templates/grub.cfg``:

.. code-block:: jinja

  set timeout=2

  {% if data is not defined  or not data.get('state:netboot_enabled', False) %}
  menuentry "Boot from local disk" {
    set root=(hd0)
    chainloader +1
  }
  {% else %}
  menuentry "{{ data.get('boot:description') }}" {
  {% if data.get('boot:gfx_payload_keep', False) %}
    set gfxpayload=keep
  {% endif %}
    linux {{ data.get('boot:kernel') }} \
      {{ data.get('boot:kernel_options', []) | join(' ') }}
    initrd {{ data.get('boot:kernel_initrd') }}
  }
  {% endif %}

This file does a number of things, so let's go through it step by step.

The ``set timeout=2`` has the effect that GRUB will automatically select the
first menu entry after two seconds. We could set the timeout to zero if did not
want the menu to be shown at all. This makes sense once everything is running,
but for debugging, it can be useful to show the menu for a short amount of time
so that the process can be interrupted at that point.

Next, we use a Jinja ``if`` expression. We can use Jinja code in this file
because we selected that template engine when configuring the request handler
for the ``templates`` directory.

We use that ``if`` expression to distinguish between two cases: If the ``data``
context variable is not available (e.g. if the system is not known to us or if
there was problem when compiling the data), we boot from the local disk. If the
``netboot_enabled`` flag is not set for the system, we also boot from the local
disk. We will discuss this flag in more detail in
:ref:`getting_started_environment_netboot_enabled`.

If the ``netboot_enabled`` flag is set, we generate a menu entry that uses the
data compiled for the system in order to determine the path to the kernel and
the initial ramdisk as well as the options passed to the kernel. We will see
in the next section how these settings are configured.

Creating a profile for Ubuntu 18.04 LTS server
----------------------------------------------

As an example, we are going to create a configuration for Ubuntu 18.04 LTS
server. Basically, the same process applies to all versions of Ubuntu or Debian.

For other distributions (e.g. CentOS) the process might look a bit different due
to the installer systems being different, but most steps will be very similar:
Get the kernel image, get the initial ramdisk, find out the kernel options, and
create a preseed or kickstart file.

We can get the files that we need from the
`Ubuntu Netboot Images archive <http://cdimage.ubuntu.com/netboot/>`_. After
choosing the Ubuntu release and architecture (we choose the ``amd64``
architecture for the moment), we are directed to a
`directory <http://archive.ubuntu.com/ubuntu/dists/bionic-updates/main/installer-amd64/current/images/netboot/>`_
with the files. We can download the ``netboot.tar.gz`` to get all files in a
single download or we can just download the individual files that we actually
need. For the moment, we are going to assume that we downloaded the
``netboot.tar.gz`` archive and are now inside the directory where we extracted
it.

We copy the files ``linux`` and ``initrd.gz`` from the
``ubuntu-installer/amd64`` sub-directory to
``/srv/vinegar/tftp/images/ubuntu/bionic/amd64``:

.. code-block:: sh

  mkdir -p /srv/vinegar/tftp/images/ubuntu/bionic/amd64
  cp \
    netboot/ubuntu-installer/amd64/{linux,initrd.gz} \
    /srv/vinegar/tftp/images/ubuntu/bionic/amd64

In order to have configuration data that we can use in our template for the
preseed file (and in the already existing template for the GRUB configuration
file), we create some files that are going to be used by the
`~vinegar.data_source.yaml_target` source that we defined earlier in the server
configuration file. We start with the file that controls the targeting of
systems. This file is saved in ``/srv/vinegar/datatree/top.yaml``:

.. code-block:: yaml+jinja

  '*':
    - common

  'myhost.mydomain.example.com or *.otherdomain.example.com':
    - ubuntu.bionic.amd64.server

This top file does two things: It defines that the data from the ``common`` file
shall be applied to all systems and it also defines that the data from the
``ubuntu.bionic.amd64.server`` file shall be used for the system with the ID
``my.host.example.com`` and all systems with IDs that end with
``.subdomain.example.com``.

We create the file ``/srv/vinegar/datatree/common/init.yaml`` with the following
content:

.. code-block:: yaml+jinja

  {% set http_url_prefix = 'http://192.2.0.99' %}

  common:
    http_url_prefix: {{ http_url_prefix | yaml }}

This file does two things: It defines a variable for the URL prefix and it uses
this variable to create an entry for ``common:http_url_prefix`` in the resulting
data tree.

For obvious reasons, the IP address used in this file has to be changed to match
the IP address of the Vinegar server and if the HTTP server is not listening on
its default port (port 80), the port number has to be added to the URL.

There is a simple reason to why we first define a variable and than use that
variable instead of simply specifying the value directly: By doing things this
way, another template in the tree can ``import`` this template and use the
variable that we defined. This means that another template can create a value
that is based on this variable (e.g. a URL that starts with that prefix).

If we did not have this variable, the final URL would have to be assembled in
the template that is processed by the file handler, which would make things more
complex because that template would need to know when it has to add the prefix.

Next, we create the other file that we reference from ``top.yaml`` in
``/srv/vinegar/datatree/ubuntu/bionic/amd64/server.yaml``:

.. code-block:: yaml+jinja

  {% from '../../../common/init.yaml' import http_url_prefix %}
  {% from 'init.yaml' import ubuntu_boot as _boot %}

  {% set default_preseed_url =
    http_url_prefix ~ '/templates/' ~ id
    ~ '/ubuntu/bionic/ubuntu-server.seed' %}

  {% macro  ubuntu_boot(
      kopts_install=[],
      kopts_permanent=[],
      preseed_url=default_preseed_url) -%}
  {{ _boot(['url=' ~ preseed_url, 'quiet'] + kopts_install, kopts_permanent) }}
  {%- endmacro %}

  {{ ubuntu_boot() }}

This file references ``init.yaml`` from the ``common`` directory to import the
``http_url_prefix`` macro and it references ``init.yaml`` from the same
directory (a file that we still have to create) to import the ``ubuntu_boot``
macro.

Using macros allows us to concentrate generic information in one file while
still being able to create customized versions for different scenarios.

The file creats its own version of the ``ubuntu_boot`` macro that adds the
``url`` and ``quiet`` parameters to the kernel options and uses the new macro.
Using the new macro (instead of just defining it) means that the file can
directly be referenced from ``top.yaml``. However, it can also be imported by
another file in order to call the macro with different arguments.

There are two types of kernel options. The first ones (``kopts_install``) are
only used by the installer system. Other second ones (``kopts_permanent``) are
used by the installer system and are also copied to the boot configuration of
the newly installed system. In the final kernel command line, they are separated
by ``---`` (see the `Debian GNU/Linux Installation Guide
<https://www.debian.org/releases/stretch/amd64/ch05s03.html.en>`_ for details).

We create the referenced file ``init.yaml`` as
``/srv/vinegar/datatree/ubuntu/bionic/amd64/init.yaml``:

.. code-block:: yaml+jinja

  {% from '../init.yaml' import ubuntu_boot as _boot %}

  {% macro ubuntu_boot(kopts_install=[], kopts_permanent=[]) -%}
  {{ _boot('amd64', kopts_install, kopts_permanent) }}
  {%- endmacro %}

That file references another ``init.yaml`` file from the parent directory. It
delegates to the ``ubuntu_boot`` macro from that file, but sets that macro's
``arch`` argument to ``amd64``.

We create the referenced file ``/srv/vinegar/datatree/ubuntu/bionic/init.yaml``
with the following content:

.. code-block:: yaml+jinja

  {% macro ubuntu_boot(arch, kopts_install=[], kopts_permanent=[]) %}
  boot:
    description: "Install Ubuntu 18.04 ({{ architecture }})"
    gfx_payload_keep: True
    kernel: "/images/ubuntu/bionic/{{ arch }}/linux"
    kernel_initrd: "/images/ubuntu/bionic/{{ arch }}/initrd.gz"
    kernel_options:
    {% for option in kopts_install %}
      - {{ option | yaml }}
    {% endfor %}
      - "---"
    {% for option in kopts_permanent %}
      - {{ option | yaml }}
    {% endfor %}
  {% endmacro %}

Finally, we create the preseed file that we specify through the ``url`` kernel
option in ``/srv/vinegar/http/templates/ubuntu/bionic/ubuntu-server.seed``. We
simply copy this file from the Ubuntu Server installer CD:

.. code-block:: text

  # Suggest LVM by default.
  d-i	partman-auto/init_automatically_partition	string some_device_lvm
  d-i	partman-auto/init_automatically_partition	seen false
  # Install the Ubuntu Server seed.
  tasksel	tasksel/force-tasks	string server
  # Only install basic language packs. Let tasksel ask about tasks.
  d-i	pkgsel/language-pack-patterns	string
  # No language support packages.
  d-i	pkgsel/install-language-support	boolean false
  # Only ask the UTC question if there are other operating systems installed.
  d-i	clock-setup/utc-auto	boolean true
  # Verbose output and no boot splash screen.
  d-i	debian-installer/quiet	boolean false
  d-i	debian-installer/splash	boolean false
  # Install the debconf oem-config frontend (if in OEM mode).
  d-i	oem-config-udeb/frontend	string debconf
  # Wait for two seconds in grub
  d-i	grub-installer/timeout	string 2
  # Add the network and tasks oem-config steps by default.
  oem-config	oem-config/steps	multiselect language, timezone, keyboard, user, network, tasks

This configuration is already sufficient to boot into the Ubuntu installer
system. If we set the ``netboot_enabled`` flag for one of the systems targeted
by ``top.yaml``, it would boot right into the Ubuntu installer.

However, there are still two things to be taken care of: The ``netboot_enabled``
flag should be reset automatically  when the installation is finished and you
probably do not want to set all installer options manually.

We can take care of resetting the ``netboot_enabled`` flag by using a "late
command". This command is going to be run by the installer when the installation
process has almost finished. We do this by adding the following line to the
preseed file (``ubuntu-server.seed``):

.. code-block:: text

  d-i preseed/late_command string \
    wget -O - "{{ data.get('common:http_url_prefix') }}/templates/{{ id }}/ubuntu/bionic/late-command.sh" | sh

Of course, we also have to create the shell script that is downloaded and
executed by that command. We save the shell script in
``/srv/vinegar/http/templates/ubuntu/bionic/late-command.sh``:

.. code-block:: sh

  #!/bin/sh

  wget \
    -O - \
    --method=POST \
    "{{ data.get('common:http_url_prefix') }}/reset-netboot-enabled/{{ id }}" \
    >/dev/null || true

Note how we use templating code in both the preseed file and the late command
script. This allows us to make the preseed file and shell script look different
for each system.

In addition to resetting the ``netboot_enabled`` flag, we want some of the
questions usually asked by the installer to be answered automatically. Usually,
we can achieve this by setting the respective answers inside the preseed file.

Some questions, however, are asked before the preseed file can even be loaded.
As the preseed file is loaded over the network, it can only be loaded once the
network configuration has finished. This means that all answers relating to the
network configuration have to be specified in the kernel command line.

For now, we automatically want to set the system's hostname and we want to delay
some questions until after the preseed file is loaded. In order to achieve this,
we edit ``/srv/vinegar/datatree/ubuntu/bionic/amd64/server.yaml`` and add the
``auto`` and the ``hostname`` option to the kernel command line:

.. code-block:: yaml+jinja
  :emphasize-lines: 15-17

  {% from '../../../common/init.yaml' import http_url_prefix %}
  {% from 'init.yaml' import ubuntu_boot as _boot %}

  {% set default_preseed_url =
    http_url_prefix ~ '/templates/' ~ id
    ~ '/ubuntu/bionic/ubuntu-server.seed' %}

  {% macro  ubuntu_boot(
      kopts_install=[],
      kopts_permanent=[],
      preseed_url=default_preseed_url) -%}
  {{ _boot(['url=' ~ preseed_url, 'quiet'] + kopts_install, kopts_permanent) }}
  {%- endmacro %}

  {% set hostname_option = 'hostname=' ~ data.get('net:hostname') %}

  {{ ubuntu_boot(kopts_install=['auto', hostname_option]) }}

Now, the installer should not ask us for the hostname any longer when
configuring the network.

.. _getting_started_environment_netboot_enabled:

Changing the ``netboot_enabled`` flag
-------------------------------------

In order to boot a system into the installer environment, we need to set the
``netboot_enabled`` flag under the ``state`` key. In theory, we could set this
flag by adding an appropriate file to the ``yaml_target`` data source, but this
would be bothersome as we would have to edit that file (or ``top.yaml``) each
time we wanto to enable or disable the flag for a system. More importantly,
there would be no way to automatically reset that flag from a late command
script running inside the installer system.

For these reasons, we rather store the flag inside an SQLite database. We have
already added the `~vinegar.data_source.sqlite` data source to the server,
configuration, now we only need a simple way of changing that database from the
command line.

We create a simple Python script that helps us with this job. For example we can
save this script to ``/usr/local/sbin/vinegar-netboot``:

.. code-block:: python3

  #!/usr/bin/python3

  import argparse
  import sys

  from vinegar.utils.sqlite_store import open_data_store

  parser = argparse.ArgumentParser(
    description='Check or change netboot_enabled flag.')
  parser.add_argument(
    '--enable',
    action='store_true',
    dest='enable',
    help='set the netboot_enabled flag')
  parser.add_argument(
    '--disable',
    action='store_true',
    dest='disable',
    help='clear the netboot_enabled flag')
  parser.add_argument(
    'system_id',
    help='system ID')
  args = parser.parse_args()

  if args.enable and args.disable:
    print(
      'Only one of --enable or --disable may be specified.', file=sys.stderr)
    sys.exit(1)

  with open_data_store('/var/lib/vinegar/system-state.db') as store:
    if args.enable:
      store.set_value(args.system_id, 'netboot_enabled', True)
      print('Enabled netboot for system %s.' % args.system_id)
    elif args.disable:
      store.delete_value(args.system_id, 'netboot_enabled')
      print('Disabled netboot for system %s.' % args.system_id)
    else:
      try:
        netboot_enabled = store.get_value(args.system_id, 'netboot_enabled')
      except KeyError:
        netboot_enabled = False
      print(
        'Netboot is %s for system %s.' % (
          ('enabled' if netboot_enabled else 'disabled'), args.system_id))

This script uses the `vinegar.utils.sqlite_store` module to open the database
and read or update the ``netboot_enabled`` flag for the specified system. After
marking the script as executable
(``chmod a+x /usr/local/sbin/vinegar-netboot``), we can use it like this:

.. code-block:: console

  $ vinegar-netboot myhost.example.com
  Netboot is disabled for system myhost.example.com.

  $ vinegar-netboot --enable myhost.example.com
  Enabled netboot for system myhost.example.com.

  $ vinegar-netboot myhost.example.com
  Netboot is enabled for system myhost.example.com.

  $ vinegar-netboot --disable myhost.example.com
  Disabled netboot for system myhost.example.com.

Testing the setup
-----------------

Now we are ready to test our setup. We have to make sure that the list of
systems in ``/srv/vinegar/systems/list.txt`` contains a line for the system that
we want to install. For this example, we are going to assume that the system's
FQDN and system ID is ``myhost.mydomain.example.com`` and it has the MAC address
``02:00:00:00:00:01`` and the IP address ``192.2.0.1``. For a real environment,
you will of course have to adjust this values and ensure that the pattern in
``top.yaml`` matches the actual system ID.

For the example case, the line in ``/srv/vinegar/systems/list.txt`` looks like
this:

.. code-block:: text

  02:00:00:00:00:01;192.2.0.1;myhost

We set the ``netboot_enabled`` flag in order to make the system boot into the
installer environment:

.. code-block:: sh

  vinegar-netboot --enable myhost.mydomain.example.com

If we reboot the system now (and it is configured to boot from the network), we
should end up inside the installer environment.

Next steps
----------

In many scenarios, you will want to run the installer without any kind of
interaction. This can be achieved by choosing the appropriate preseed options.
We cannot discuss all possible preseed options supported by the Debian Installer
here.

A good starting point to learn more about automating Debian and Ubuntu
installations is `Appendix B of the Debian GNU/Linux Installation Guide
<https://www.debian.org/releases/stretch/amd64/apb.html.en>`_. Even though this
guide is written for Debian, most (if not everything) of it also applies to
Ubuntu. You might also find the `preseed examples
<https://help.ubuntu.com/community/InstallCDCustomization/PreseedExamples>`_
from the Ubuntu Community Help Wiki helpful.

At some point, you might also want to add support for more architectures (e.g.
``i386``). Thanks to the modular design that we chose for this example
configuration, this is not very hard. Basically, you can repeat the instructions
above for that architecture (of course only adding those files that actually
depend on the architecture) and you should be good to go.

The GRUB configuration that we created is already prepared to work with a
traditional PC BIOS based boot environment as well as 32 and 64 bit UEFI boot,
so you most likely will not have to make any changes to the GRUB configuration.

You might also want to add other distributions (be it other releases of Ubuntu
or completely different distributions like Debian or CentOS). In every case, you
can choose which parts of the configuration you want to share and which parts
are specific to certain profiles.

Before you start with this, it is a good idea to read the :ref:`concepts` part
of this documentation because it will give you a much better understanding of
how things work together.
