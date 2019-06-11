"""
Support for Jinja templates (using the Jinja 2 library).

The `JinjaEngine` provided by this module use the Jinja 2 library for rendering
template files. The Jinja 2 `~jinja2.Environment` can be configured when
creating the template engine.

The preferred way of creating an instance of the Jinja template engine is by
calling the `get_instance` function, not by creating an instance of
`JinjaEngine` directly.

Template syntax
---------------

The Jinja template engine supports the full range of features provided by the
Jinja 2 library. Please refer to the
`Jinja 2 documentation <http://jinja.pocoo.org/docs/>`_ to learn more about how to
write Jinja templates.

Unless disabled by setting ``provide_transform_functions`` to ``False``, this
template engine provides a ``transform`` object that can be used to access
functions from the ``vinegar.transform`` package.

Configuration options
---------------------

The template engine provded by this module supports the following configuration
options that can be passed through the ``config`` dictionary that is passed to
`get_instance`:

:``cache_enabled``:
    This option (a ``bool``) specifies whether caching is enabled. If ``True``
    (the default), templates are only recompiled when the corresponding file has
    been modified. Modification is detected by comparing the file's ``ctime``
    and ``mtime``. If ``False`` the template is recompiled on each request. This
    can make sense if files are changed rapidly and the time stamps provided by
    the file system do not provide sufficient precision. This option is actually
    handled by the loader, so it will have no effect when supplying a custom
    loader through the ``loader``environment option.

:``env``:
    This option is used to specify a dict that is used when creating the
    `~jinja2.Environment`. By default three options are passed to the
    environment, unless they are explicitly specified in the ``env`` dict:
    ``autoescape`` is set to ``False`` and ``keep_trailing_newline`` is set to
    ``True``. The ``loader`` is also created automatically based on the
    ``root_dir`` configuration option.

:``provide_transform_functions``:
    This option (a ``bool``) specifies whether an object with the name
    ``transform`` is added to the context. If ``True`` (the default), the
    ``transform`` object allows easy access to the transformation functions
    provided by `vinegar.transform`. The ``transform`` object is not added if
    there is an object using that key in the context that is passed to
    `~JinjaEngine.render`. If ``provide_transform_functions`` is ``False``, the
    ``transform`` object is not added to the context. The ``transform`` object
    can be used like in the following example:
    ``transform['string.to_upper']('This is all converted to upper case.')``

:``relative_includes``:
    This option (a ``bool``) specifies whether included templates (these are
    templates that are use by another template through the ``import`` or
    ``include`` directives) are resolved relative to the using template or
    relative to the root of the loader. The default value of this option is
    ``True``, meaning that included templates are resolved relative to their
    parent.

:``root_dir``:
    This option (a ``str``) specifies the root directory for the loader that
    loads templates. If it is ``None`` (the default), template names that
    represent an absolute path on the file system are used as-is and other
    template names are resolved relative to the current working directory.
    Please note that this option is only effective if not custom loader is
    specified through the ``env`` option. It is an error to specify this option
    when also specifying a custom loader.
"""
import os.path
import typing

import jinja2

from vinegar.template import TemplateEngine
from vinegar.transform import get_transformation_function
from vinegar.utils.version import version_for_file_path

class JinjaEngine(TemplateEngine):
    """
    Template engine using the Jinja 2 library.

    For information about the configuration options supported by this template
    engine, please refer to the `module documentation <vinegar.template.jinja>`.
    """

    class _NoCacheFileSystemLoader(jinja2.FileSystemLoader):
        """
        Variant of the file-system loader that always considers a file as
        modified.
        """

    def get_source(self, *args, **kwargs):
        contents, filename, _ = super().get_source(*args, **kwargs)
        return contents, filename, lambda _: False

    class _Environment(jinja2.Environment):
        """
        Environment used to resolve includes relative to their parent template.

        This environment is used instead of `jinja2.Environment` when the
        ``relative_includes`` configuration option is set.
        """

        def join_path(self, template, parent):
            # By default, Jinja resolves includes as relative to the root of the
            # loader. In our case, this is not desirable because our loader does
            # not have a root, so the path gets resolved relative to the current
            # working directory.
            # For this reason, we overload join_path so that includes get
            # resolved relative to the including template.
            return os.path.join(parent, '..', template)

    class _Loader(jinja2.BaseLoader):
        """
        Loader for Jinja templates.

        This loader is very similar to the `jinja2.FileSystemLoader`, but it
        does not use a search path but treats every template name as a path on
        the filesystem.
        """

        def __init__(self, cache_enabled=True, encoding='utf-8'):
            self._encoding = encoding
            self._cache_enabled = cache_enabled

        def get_source(self, environment, template):
            # We make the template path absolute, so that we can later resolve
            # relative includes, even if the current working directory has
            # changed in the meantime. This also makes caching easier because we
            # will always use the same path for the same file (unless symbolic
            # links are involved).
            template = os.path.abspath(template)
            # We treat the template name as a file path.
            file_version = version_for_file_path(template)
            try:
                with open(template, 'rb') as file_descriptor:
                    file_contents = file_descriptor.read().decode(self._encoding)
            except (FileNotFoundError, IsADirectoryError):
                raise jinja2.TemplateNotFound(template)

            if self._cache_enabled:
                def up_to_date():
                    current_file_version = version_for_file_path(template)
                    return current_file_version == file_version
            else:
                def up_to_date():
                    return False

            return file_contents, template, up_to_date

    class _TransformHelper:
        """
        Object that is added to the context under the ``transform`` key. This
        object allows access to transformation functions by passing the module
        and function name as an index to this object.

        Example::
        
            transform['string.to_upper']('Convert this to upper case.')
        """

        def __getitem__(self, key):
            return get_transformation_function(key)

    def __init__(self, config: typing.Mapping[typing.Any, typing.Any]):
        """
        Create a Jinja template engine using the specified configuration.

        :param config:
            configuration for this template engine. Please refer to the
            `module documentation <vinegar.template.jinja>` for a list of
            supported options.
        """
        root_dir = config.get('root_dir', None)
        user_env = config.get('env', {})
        relative_includes = config.get('relative_includes', True)        
        # We do not allow specifying both a custom loader and the root
        # directory. This would not make sense as that loader would not use the
        # specified root directory.
        if 'root_dir' in config and 'loader' in user_env:
            raise ValueError(
                'The configuration can either specify the root_dir option '
                'or provide its own loader in the env option, not both.')
        # If the root_dir option is specified, we use Jinja's file-system loader
        # with the specified root directory. If not, we use our own loader, that
        # looks for templates on the full file-system (templates names that
        # represent an absolute path are used as is, other template names are
        # resolved relative to the current working directory.
        if root_dir is None:
            loader = self._Loader(
                config.get('cache_enabled', True),
                config.get('encoding', 'utf-8'))
        else:
            if config.get('cache_enabled', True):
                loader = jinja2.FileSystemLoader(root_dir)
            else:
                loader = self._NoCacheFileSystemLoader(root_dir)
        env_options = {
            'autoescape': False,
            'keep_trailing_newline': True,
            'loader': loader
        }
        env_options.update(user_env)
        if relative_includes:
            self._environment = self._Environment(**env_options)
        else:
            self._environment = jinja2.Environment(**env_options)
        self._base_context = {}
        if config.get('provide_transform_functions', True):
            self._base_context['transform'] = self._TransformHelper()

    def render(
            self,
            template_path: str,
            context: typing.Mapping[str, typing.Any]) -> str:
        try:
            template = self._environment.get_template(template_path)
        except jinja2.TemplateNotFound as e:
            raise FileNotFoundError() from e
        merged_context = self._base_context.copy()
        merged_context.update(context)
        try:
            return template.render(**merged_context)
        except jinja2.TemplateNotFound as e:
            raise FileNotFoundError() from e

def get_instance(config: typing.Mapping[typing.Any, typing.Any]) -> JinjaEngine:
    """
    Create a Jinja template engine.

    For information about the configuration options supported by that engine,
    please refer to the `module documentation <vinegar.template.jinja>`.

    :param config:
        configuration for the template engine.
    :return:
        Jinja template engine using the specified configuration.
    """
    return JinjaEngine(config)
