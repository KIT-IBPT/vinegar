"""
Provides an order-preserving dictionary.

The only type in this module is ``OrderedDict``. When running on Python 3.7 or
newer, this type is the type ``dict`` (the regular built-in dictionary type).
When running on older versions of Python, this type is
``collections.OrderedDict``.

Since Python 3.7, regular dictionaries guarantee that they preserve the
insertion order of keys. In fact, the implementation provided by CPython 3.6
already preserved the insertion order, but this was merely an implementation
detail, not something guaranteed by the language. Since Python 3.7, it is
guaranteed by the specification.

Please note that the ``OrderedDict`` provided by this module does not
necessarily provide the ``popitem`` method that takes a ``bool`` arugment and
the ``move_to_end`` method. If either of these methods are needed,
``collections.OrderedDict`` has to be used instead.
"""

import sys

if sys.version_info >= (3, 7):
    OrderedDict = dict
else:
    from collections import OrderedDict
