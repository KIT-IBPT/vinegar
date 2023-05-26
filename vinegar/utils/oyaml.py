"""
YAML library that preserves key order in ``dict``s.

This module used to be useful when running on Python versions before 3.7. As
only newer versions of Python are supported now, this module is not needed any
longer and is only kept for compatibility with the old API.

.. deprecated:: Vinegar 1.3
   Use the regular ``yaml`` module instead.
   Will be removed in Vinegar 2.0.
"""

# pylint: disable=unused-wildcard-import,wildcard-import
from yaml import *  # type: ignore
