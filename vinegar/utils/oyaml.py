# This module is from https://github.com/wimglenn/oyaml/.
#
# Copyright (c) 2018 wim glenn
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
YAML library that uses ``OrderedDict`` from `vinegar.utils.odict` instead of a
regular ``dict``.

Thanks to this change, insertion order of keys in dictionaries is preserved,
even when running on a Python version where regular dicts are not
order-preserving yet.

Effectively, this library acts as a wrapper around PyYAML (module ``yaml``), but
it can simply be used like the regular module. For example::

  import vinegar.utils.oyaml as yaml
"""

import platform
import sys
from vinegar.utils.odict import OrderedDict

import yaml as pyyaml


_items = "viewitems" if sys.version_info < (3,) else "items"
_std_dict_is_order_preserving = sys.version_info >= (3, 7) or (
    sys.version_info >= (3, 6) and platform.python_implementation() == "CPython"
)


def map_representer(dumper, data):
    return dumper.represent_dict(getattr(data, _items)())


def map_constructor(loader, node):
    loader.flatten_mapping(node)
    pairs = loader.construct_pairs(node)
    try:
        return OrderedDict(pairs)
    except TypeError:
        loader.construct_mapping(node)  # trigger any contextual error
        raise


if pyyaml.safe_dump is pyyaml.dump:
    # PyYAML v4.x
    SafeDumper = pyyaml.dumper.Dumper
    DangerDumper = pyyaml.dumper.DangerDumper
else:
    SafeDumper = pyyaml.dumper.SafeDumper
    DangerDumper = pyyaml.dumper.Dumper

pyyaml.add_representer(dict, map_representer, Dumper=SafeDumper)
pyyaml.add_representer(OrderedDict, map_representer, Dumper=SafeDumper)
pyyaml.add_representer(dict, map_representer, Dumper=DangerDumper)
pyyaml.add_representer(OrderedDict, map_representer, Dumper=DangerDumper)


Loader = None
if not _std_dict_is_order_preserving:
    for loader_name in pyyaml.loader.__all__:
        Loader = getattr(pyyaml.loader, loader_name)
        pyyaml.add_constructor("tag:yaml.org,2002:map", map_constructor, Loader=Loader)


# Merge PyYAML namespace into ours.
# This allows users a drop-in replacement:
#   import oyaml as yaml
del map_constructor, map_representer, SafeDumper, DangerDumper, Loader
from yaml import *
