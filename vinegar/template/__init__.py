"""
Renderers for various template languages.

Template engines are used to render template files, enriching them with
information provided through a context. They are the primary way of generating
customized files based on configuration information.

The `vinegar.template.jinja` module provides a template engine using the
powerful Jinja 2 library. An instance of that engine can be retrieved by
calling `get_template_engine` with ``name`` set to `jinja`.

All template engine modules have in common that they must specify a
`get_instance` function that takes a `dict` with configuration data as its only
parameter. This function must return an instance of `TemplateEngine`.

Template engines are thread safe.
"""

import abc
import importlib

from typing import Any, Mapping


# pylint: disable=too-few-public-methods
class TemplateEngine(abc.ABC):
    """
    Renderer for template files.

    A template engine is used to read template files and provide the output of
    the rendering process.

    Each template engine has to implement the `render` method. This method is
    used to read a template file and returns is rendering result as a string.

    Template engines have to be implemented in a thread-safe manner, so that
    `render` can safely be used by different threads.
    """

    @abc.abstractmethod
    def render(self, template_path: str, context: Mapping[str, Any]) -> str:
        """
        Render the template file specified by ``template_path`` and return the
        result.

        :param template_path:
            path to the template file.
        :param: context:
            context available to the template. The objects supplied by this
            mapping should be made available to the template code when
            rendering. The details of how the context objects are made
            available depends on the template engine.
        :return:
            result of rendering the template.
        """
        raise NotImplementedError


def get_template_engine(
    name: str, config: Mapping[Any, Any]
) -> TemplateEngine:
    """
    Create the an instance of the template engine with the specified name,
    using the specified configuration.

    :param name:
        name of the template engine. If the name contains a dot, it is treated
        as an absolute module name. Otherwise it is treated as a name of one of
        the modules inside the `vinegar.template` module.
    :param: config:
        configuration data for the template engine. The meaning of that data is
        up to the implementation of the template engine.
    :return:
        newly created template engine.
    """
    module_name = name if "." in name else f"{__name__}.{name}"
    template_engine_module = importlib.import_module(module_name)
    return template_engine_module.get_instance(config)
