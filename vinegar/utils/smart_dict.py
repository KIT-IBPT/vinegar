"""
Provides a dictionary that has a smart ``get`` method.

The ``get`` method of ``SmartLookupDict`` is implemented in a way that makes it
easy to look for values in nested dictionaries.

For example, take a dictionary with the following content::

    {'key1': {'key2': {'key3': 'value'}}}

In order to get the nested value, one would ordinarily have to use one of the
two following expressions::

    value = regular_dict['key1']['key2']['key3']
    value = regular_dict.get('key1').get('key2').get('key3')

This is particularly bothersome if one cannot be sure that the nested value
even exists. In order to use a default value if one of the keys is missing, one
could use nested calls to ``get`` with default values::

    value = regular_dict.get(
        'key1', {}).get('key2', {}).get('key3', 'default value')

An alternative would be catching the ``KeyError``::

    try:
        value = regular_dict['key1']['key2']['key3']
    catch KeyError:
        value = "default value"

Both alternatives are not very user friendly, in particular if used from a
template language where a ``try...catch`` construct might not be available.

The smart dictionaries make such use cases either by enabling the user to get a
nested value in a single call to ``get``::

    value = smart_dict.get('key1:key2:key3', 'default value')

By default the colon (``:``) is used as the key separator, but this can be
changed by specifying the ``sep`` argument::

    value = smart_dict.get('key1_key2_key3', 'default value', sep='_')

In addition to handling nested dicts, the smart-lookup dict can also handle
nested lists. For example, consider a dictionary with the following content:

    {'key1': ['a', 'b', {'nested_key': 123}]}

The nested values can be looked up in the following way:

    smart_dict.get('key1:0')
    smart_dict.get('key1:2:nested_key')

In addition to the ``get`` method, the ``setdefault`` method is overriden, so
that it automatically inserts nested dictionaries if needed. Please note that
``setdefault`` can handle traversing lists, but it cannot handle inserting a
new item into a list.

The implementation of ``get`` provided by the smart lookup dictionaries also
differs from the one for regular dictionaries in that it do not use a default
value of ``None`` by default. Instead, it raises a ``KeyError`` if the key is
not found and no default value is provided.
"""

import collections.abc
import re

_RE_INT = re.compile("[0-9]+")


def _get_nested_value(container, key):
    try:
        return container[key]
    except TypeError:
        # We might encounter a TypeError because the container is a sequence
        # and not a mapping. In this case, we try again, using a numeric key
        # this time. We only do this if certain conditions are met (e.g. the
        # key is actually numeric and the container is not a string-like
        # object).
        if (
            isinstance(container, collections.abc.Sequence)
            and _RE_INT.fullmatch(key)
            and not isinstance(container, collections.abc.ByteString)
            and not isinstance(container, str)
        ):
            try:
                return container[int(key)]
            except IndexError as err:
                # We convert an IndexError to a KeyError so that it can be
                # handled correctly in the calling code. Code using a dict’s
                # get method might not expect an IndexError, so it is better to
                # signal this as a KeyError.
                raise KeyError(int(key)) from err
            except TypeError:
                pass
        # If we could cannot use the specified key as a numeric key either, we
        # raise the original exception.
        raise


class SmartLookupDict(dict):
    """
    Dict that allows easy lookup and setting of nested values.
    """

    def get(self, key, *args, **kwargs):
        """
        Return the value for ``key``.

        If ``key`` is not in the dictionary and ``default`` is given, return
        ``default``. If ``default`` is not given raise a ``KeyError``.

        The ``key`` can be a nested key into nested dictionaries inside this
        dictionary. The ``key`` is split using the ``sep`` (default ``:``) and
        each component is used as the key on one level of nested dictionaries,
        the first component being used at the top level.

        :param key:
            key for which the value shall be looked up. This can be a nested
            key into nested dictionaries. ``sep`` is used to separate
            components of the key.
        :param default:
            default value to be returned if this dictionary (or one of the
            nested dictionaries) does not contain ``key``. If not specified, a
            ``KeyError`` is raised instead.
        :param sep:
            separator separating components in ``key``. The default is ``:``.
        :return:
            value for ``key`` or ``default`` if specified and ``key`` is not
            found.
        """
        have_default = False
        sep = ":"
        if len(args) > 2:
            raise TypeError(
                f"get expected at most 3 arguments, got {len(args) + 1}"
            )
        if len(args) >= 1:
            if "default" in kwargs:
                raise TypeError(
                    "Default value must not be given both as a positional and "
                    "a keyword argument."
                )
            default = args[0]
            have_default = True
        if len(args) >= 2:
            if "sep" in kwargs:
                raise TypeError(
                    "Separator must not be given both as a positional "
                    "argument and a keyword argument."
                )
            sep = args[1]
        try:
            default = kwargs["default"]
            have_default = True
        except KeyError:
            pass
        try:
            sep = kwargs["sep"]
        except KeyError:
            pass
        for kwarg_key in kwargs:
            if kwarg_key not in ("default", "sep"):
                raise TypeError(
                    f"test() got an unexpected keyword argument '{kwarg_key}'"
                )
        keys = key.split(sep)
        nested_value = self
        try:
            for key_part in keys:
                nested_value = _get_nested_value(nested_value, key_part)
        except KeyError:
            if have_default:
                return default  # type: ignore
            raise KeyError(key) from None
        return nested_value

    def setdefault(self, key, default=None, sep=":", dict_type=dict):
        """
        Return the value for ``key`` inserting and returning ``default`` if
        ``key`` does not exist yet.

        The ``key`` can be a nested key into nested dictionaries inside this
        dictionary. The ``key`` is split using the ``sep`` (default ``:``) and
        each component is used as the key on one level of nested dictionaries,
        the first component being used at the top level.

        If one of the key components except the last key component is not
        found, a new dictionary of type ``dict_type`` is inserted
        automatically.

        :param key:
            key for which the value shall be looked up. This can be a nested
            key into nested dictionaries. ``sep`` is used to separate
            components of the key.
        :param default:
            default value to be inserted and returned if this dictionary (or
            one of the nested dictionaries) does not contain ``key``.
        :param dict_type:
            the type of dictionary that is created when a new dictionary has to
            be inserted. The default is ``dict``.
        :return:
            value for ``key`` or ``default`` if ``key`` is not found.
        """
        keys = key.split(sep)
        last_key = keys[-1]
        keys = keys[:-1]
        nested_value = self
        for key_part in keys:
            try:
                nested_value = _get_nested_value(nested_value, key_part)
            except KeyError:
                nested_value[key_part] = dict_type()
                nested_value = nested_value[key_part]
        try:
            return nested_value[last_key]
        except KeyError:
            nested_value[last_key] = default
            return default
