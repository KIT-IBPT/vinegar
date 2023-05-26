"""
Provides an order-preserving dictionary.

This module used to provide an insertion-order preserving ``dict``
implementation for Python versions before 3.7. As only newer versions of Python
are supported now, this module is not needed any longer and is only kept for
compatibility with the old API.

.. deprecated:: Vinegar 1.3
   Since Python 3.7, regular ``dict``s are order preserving.
   Will be removed in Vinegar 2.0.
"""

OrderedDict = dict
"""
.. deprecated:: Vinegar 1.3
   Since Python 3.7, regular ``dict``s are order preserving.
   Will be removed in Vinegar 2.0.
"""
