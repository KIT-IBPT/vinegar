"""
Base package for transformation functions.

Transformation functions are functions that help with transforming a value,
possibly building a chain.

For a list of the supported functions, please refer to the various sub-modules
that provide the actual functions. The functions from these modules can be
called directly.

The `apply_transformation` function in this module helps with calling
transformation functions that are not known at the time of writing the code. For
example, code might allow a user to choose the transformation function at
runtime.

The `apply_transformation_chain` function can be used when a user can specify a
whole chain of transformations that shall be applied one after the other.
"""

import collections.abc
import importlib

from typing import Any, Callable, Mapping, Sequence, Union

# Type of the transformation chain passed to `apply_transformation_chain`.
#
# This type is defined here so that it can easily be used as a type hint.
TransformationChain = Sequence[Union[str, Mapping[str, Any]]]

def apply_transformation(name: str, *args, **kwargs) -> Any:
    """
    Transform a value using the specified transformation.

    The name of the transformation function that shall be used is specified in
    the form ``module_name.function_name``, where ``module_name`` is either the
    name of one of the modules in the ``vinegar.transform`` package or the fully
    qualified name of a Python module, and ``function_name`` is the name of the
    transformation function in that module.

    Typically, transformation functions take the value to be transformed as
    their first positional argument.

    Example::

        apply_transformation('string.to_upper', 'abc')

    :param name:
        name of the transformation that shall be applied.
    :param args:
        positional arguments. This arguments are simply passed on to the
        transformation function.
    :param kwargs:
        keyword arguments. This arguments are simply passed on to the
        transformation function.
    :return:
        value returned by the transformation function.
    """
    transform_function = get_transformation_function(name)
    return transform_function(*args, **kwargs)

def apply_transformation_chain(chain: TransformationChain, value: Any) -> Any:
    """
    Apply a chain of transformations to a value.

    Each of the functions in the chain in the chain is applied to the input
    value in sequence.

    The ``chain`` argument is a list of transformation specifications. Each
    specification is either a ``str`` simply specifying the name of the
    transformation function, or it is a ``dict`` with a single entry, where the
    key is the name of the transformation function and the value is the
    configuration for that function.

    The name of the transformation function is parsed according to the same
    as for the `apply_transformation` function.

    The configuration for a function can be a ``dict``, a ``list`` or another
    value. If it is a ``dict``, the items in it are passed to the function as
    keyword arguments. If it is a ``list``, the items in it are passed to the
    function as positional arguments (after the ``value`` argument). In all
    other cases, the configuration is passed as a single positional argument
    after the ``value`` argument.

    Example::

        # The following three calls all result in the output "ABC.def":
        chain = [
            'string.to_upper',
            {'string.add_suffix': '.def'}]
        apply_transformation_chain(chain, 'abc')
        chain = [
            {'string.to_upper': []},
            {'string.add_suffix': ['.def']}]
        apply_transformation_chain(chain, 'abc')
        chain = [
            {'string.to_upper': {}},
            {'string.add_suffix': {'suffix': '.def'}}]
        apply_transformation_chain(chain, 'abc')

    :param chain:
        list describing the transformation chain. Please refer to the function
        description for details.
    :param value:
        value that shall be transformed. This is the input to the first function
        in the transformation chain.
    :return:
        transformed value. This is the return value of the last function in the
        transformation chain.
    """
    for transformation in chain:
        if isinstance(transformation, collections.abc.Mapping):
            if len(transformation) != 1:
                raise ValueError(
                    'Invalid transformation: A transformation entry either '
                    'has to be a str or a dict with exactly one item.')
            name = next(iter(transformation.keys()))
            config = next(iter(transformation.values()))
        else:
            name = transformation
            config = None
        if not isinstance(name, str):
            raise ValueError(
                'Transformation name is a {0} not a str: {1}'.format(
                    type(name).__name__, name))
        args = []
        kwargs = {}
        if isinstance(config, collections.abc.Mapping):
            kwargs = config
        elif isinstance(config, collections.abc.Sequence) and not isinstance(
                config, (bytearray, bytes, memoryview, str)):
            args = config
        elif config is not None:
            args = [config]
        value = apply_transformation(name, value, *args, **kwargs)
    return value

def get_transformation_function(name: str) -> Callable:
    """
    Return a transformation by name.

    The name of the transformation function that shall be used is specified in
    the form ``module_name.function_name``, where ``module_name`` is either the
    name of one of the modules in the ``vinegar.transform`` package or the fully
    qualified name of a Python module, and ``function_name`` is the name of the
    transformation function in that module.

    If the specified module cannot be found, a ``ModuleNotFoundError`` is
    raised. If the module is found, but the transformation function does not
    exist, an ``AttributeError`` is raised. If an object by the specified name
    exists, but it is not a ``Callable``, a ``TypeError`` is raised.

    :param name:
        name of the transformation that shall be returned.
    :return:
        transformation function for the specified name.
    """
    # If there are two components, we assume that the first component is a
    # sub-module name in vinegar.transform and the second one is the function
    # name.
    # If there are more than two components, we assume that all but the last
    # component form the module name and the last one is the function name.
    # If there are less than two components, this is considered an error.
    module_name, _, function_name = name.rpartition('.')
    if not module_name:
        raise ValueError(
            'Missing module name in transformation name: {0}'.format(name))
    if '.' not in module_name:
        module_name = '{0}.{1}'.format(__name__, module_name)
    transform_module = importlib.import_module(module_name)
    transform_function = getattr(transform_module, function_name)
    if not isinstance(transform_function, collections.abc.Callable):
        raise TypeError(
            '\'{0}\' object is not callable'.format(
                type(transform_function).__name__))
    return transform_function
