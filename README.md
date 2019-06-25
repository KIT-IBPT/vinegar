What is Vinegar?
================

Vinegar is a boot server written in Python 3. It integrates an HTTP and TFTP
server with a data source framework and template engine in order to provide a
tool for automating operating system installations. It is mainly targeted at
(but not limited to) automating installations of Linux distributions.

Download
========

Vinegar can retrieved in both binary and source form from the GitHub site at
https://github.com/KIT-IBPT/vinegar/.

Documentation
=============

The documentation is available at https://vinegar.readthedocs.io/.

License
=======

Vinegar is licensed under the terms of the GNU Lesser General Public License
version 3. Please refer to the [license text](LICENSE.txt) and the
[licensing notices](NOTICE.txt) for details.

FAQ
===

Why did you write Vinegar?
--------------------------

We needed a tool for automating the installation of (Ubuntu) Linux systems and
wanted a solution that could easily be integrated with our environment.

Before, we were using [Cobbler](https://cobbler.github.io/), but we were really
unhappy with it, for several reasons.

Switching to a different boot loader (GRUB 2) proved to be a major hassle
because Cobbler did not simply use template files but made many assumptions
about file layouts and formats so that adding support for GRUB 2 would have
meant rewriting parts of Cobbler completely.

Other reasons were the rather bad quality of the documentation and the fact that
no Debian packages were distributed any longer and building Debian packages from
the source was not well supported either.

We also did not like the fact that the management of the configuration had to be
done through a command-line tool instead of simply editing configuration files.

Why is it called Vinegar?
-------------------------

Vinegar was designed to install a system to a point from where it can be managed
with [SaltStack](https://www.saltstack.com/). The name Pepper was already used
other things in the context of software, so we called it Vinegar.
