.. module:: vinegar.http

vinegar.http
============

This module is responsible for serving files via HTTP.

HTTP is used to load additonal files, once the basic installation system (kernel
and initial ramdisk) has been booted. Typically, this includes the preseed or
kickstart file and early and late command files.

Sub modules
-----------

.. currentmodule:: vinegar.http

.. autosummary::
  :toctree:

  server
