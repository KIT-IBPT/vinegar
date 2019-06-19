.. _introduction:

Introduction
============

Vinegar is the answer to the question "How do we get a bare metal system into a
state where we can manage it with `Salt <https://www.saltstack.com/>`_?".

At the first glance, it is a boot server, but when taking a closer look, it
simply is an HTTP and TFTP server combined with a template engine and a simple
yet powerful data source system.

Unlike many other network boot or automated installation products, Vinegar is
not tied to a specific operating system, distribution, or even boot loader.
While we designed it to automate installation of Ubuntu Linux, there is
absolutely no reason why you should not use it for other distributions like
Debian or CentOS. In fact, you should even be able to use it for completely
different operating systems, as long as they support loading their installer
via TFTP or HTTP.

As a new user, there are two ways how you can read this documentation. You can
either start with :ref:`getting_started` to first learn how to setup a basic
server and then continue with :ref:`concepts`, or you can study the
:ref:`concepts` first to get a better understanding of how the various
components work together and then continue with :ref:`getting_started` to get
your server running.

In either case, you will find a lot of pointers into the :ref:`api`. The API
reference is not just a reference for the code interface of the various
components, it also contains detailed information about the configuration
options for each component, so you will typically come back to that reference
when adapting the server configuration for your needs.

When you are familar with Cobbler or Salt, you might want to read the
:ref:`introduction_for_cobbler_users` or :ref:`introduction_for_salt_users`
sections before proceeding with the :ref:`getting_started` chapter.

.. _introduction_for_cobbler_users:

Vinegar for Cobbler users
-------------------------

If you have previously used `Cobbler <https://cobbler.github.io/>`_, you will
find that Vinegar does things a bit differently. Vinegar itself does not know
anything about boot loaders,  kernels, Linux distributions, or preseed files.

Vinegar is simpy a combined HTTP and TFTP server with a very powerful template
engine. In contrast to Cobbler, this means that you can make the configuration
as complex as you need it, not as complex as the system's concept dictates.

If you only want to install a single Linux distribution, things are very simple:
You have do not have to think about profiles, but simply define the
configuration for that one distribution. If you want to add another
distribution, you simply add the files for that distribution. If you want to
share something between the two distributions, you simply put the shared data
into a separate file that you include from the other files.

The fact that Vinegar is agnostic to the boot loaders and Linux distributions
involved also has another advantage: You are not tied to a particular boot
loader of configuration file format. In the :ref:`getting_started` chapter, we
are going to use GRUB 2, but if you prefer PXELINUX, this is just as possible.
Instead of copying the GRUB files, you will simply copy the PXELINUX files and
adjust the template files so that they match the format expected by PXELINUX.

In contrast to Cobbler, there is absolutely no need to patch existing or write
new Python code just to support a different boot loader, Linux distribution or
even a completely different operating system like a xBSD or Windows. As long as
the installer can be loaded from TFTP or HTTP and it supports text-based
configuration files, Vinegar supports it.

.. _introduction_for_salt_users:

Vinegar for Salt users
----------------------

When you already use `Salt <https://www.saltstack.com/>`_ you will find that
Vinegar feels a lot like Salt, with the difference that it works in an
environment where no operating system has been installed yet.

In contrast to Salt, you will find that two things work a bit differently.
You cannot use grains for targeting (grains do not exist because there is no
way to get information *from* the system) and rendering happens on the server
not on the individual system (in the preboot or installer environment, we simply
do not have the means to implement any complex logic).

Like the pillar in Salt, Vinegar use a tree of configuration information that is
retrieved from components called :ref:`data sources <concepts_data_sources>`.
You can achieve something similar to the targeting based on grains in Salt, if
you have a data source that provides the piece of data (e.g. the system's IP
address) and then using Jinja code in templates to decide whether that piece of
data matches your condition. This is why in the example configuration that we
are going to discuss in :ref:`getting_started`, we place the
`~vinegar.data_source.text_file` data source before the
`~vinegar.data_source.yaml_target` data source.

The `~vinegar.data_source.yaml_target` uses a tree of YAML files rendered with
Jinja that look extremely similar to the file tree used for Salt's pillar (the
main difference is that there are no environments in the top file).

As the `~vinegar.data_source.text_file` data source is called first, the
`~vinegar.data_source.yaml_target` source can actually use the data from the
first source when rendering the templates for the second, thus making it
possible to use conditional blocks in Jinja to match on things like IP
addresses (assuming they are provided by the first source).

We will have a closer look at how data sources are used in Vinegar in the
:ref:`concepts` chapter, and also see some examples in the
:ref:`getting_started` chapter.
