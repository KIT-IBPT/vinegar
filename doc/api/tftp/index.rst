.. module:: vinegar.tftp

vinegar.tftp
============

This module is responsible for serving files via TFTP.

TFTP is used very early in the boot process in order to download the boot loader
and its configuration files. A bit later in the process, it is used to download
the kernel and the initial ramdisk.

Sub modules
-----------

.. currentmodule:: vinegar.tftp

.. autosummary::
  :toctree:

  protocol
  server
