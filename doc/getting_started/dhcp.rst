.. _getting_started_dhcp:

Setting up DHCP
===============

When a system boots from the network, the first point for getting configuration
information is the DHCP server. This means that we have to add a few lines to
the DHCP server configuration to make it point to the Vinegar server.

In this example, we are going to assume that we use the `ISC DHCP server
<https://www.isc.org/dhcp/>`_. We have to add the following lines to the
server's configuration file:

.. code-block:: text

  # Options used for PXE boot
  option architecture-type code 93 = unsigned integer 16;

  # PXE boot
  class "pxeclients" {
    match if substring (option vendor-class-identifier, 0, 9) = "PXEClient";
    next-server 192.2.0.99;
    if option architecture-type = 00:00 {
      filename "/grub/i386-pc/core.0";
    } else if option architecture-type = 00:06 {
      filename "/grub/i386-efi/core.efi";
    } else if option architecture-type = 00:07 {
      filename "/grub/x86_64-efi/shimx64.efi";
    }
  }

The first part (defining the ``architecture-type`` option) goes into the global
part of the configuration. The ``architecture-type`` simply is an alias that we
define so that we can easily refer to DHCP option 93.

The second part can appear in the global part of the configuration, but it can
also appear inside a ``group`` or ``subnet`` definition. This part matches any
client that identifies itself as a PXE client (through the
``vendor-class-identifier`` option) and makes the IP address of the boot server
(the server running Vinegar, ``192.2.0.99`` in this example) known to the
client. It also tells the client the path of the boot loader on the boot (TFTP)
server. The path depends on the client architecture because we need different
versions of the boot loader for PC BIOS, UEFI 32 bit, and UEFI 64 bit systems.

If you are using a different kind of DHCP server, you have to refer to its
documentation in order to find out how to set the IP address of the boot server
and the architecture-dependent path to the boot loader.

If you cannot modify the configuration of an existing DHCP server, you might
want to consider using [dnsmasq](https://thekelleys.org.uk/dnsmasq/doc.html).
dnsmasq can operator in proxyDHCP mode, meaning that it will be able to give
information about the boot server to PXE clients without interfering with the
operation of the regular DHCP server. Please refer to the dnsmasq documentation
in order to learn how to configure proxyDHCP mode.

We are going to set up the boot loader (GRUB 2) in the :ref:`next section
<getting_started_environment>`.
