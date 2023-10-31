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
`Jinja 2 documentation <http://jinja.pocoo.org/docs/>`_ to learn more about how
to write Jinja templates.

Unless disabled by setting ``provide_transform_functions`` to ``False``, this
template engine provides a ``transform`` object that can be used to access
functions from the ``vinegar.transform`` package.

Optionally, access to selected Python modules can be enabled through the
``provide_python_modules`` setting. If this setting is non-empty, a object
with the name ``python`` is added to the template context. This object can then
be used to access the explicitly allowed Python modules.

This template engine also provides a ``raise`` function that can be used to
raise a ``TemplateError`` from within templates. That function is added to the
globals so that it is also available in templates that are imported without the
context.

The environment created by this template engine adds four extensions by
default:

* ``jinja2.ext.do``: This extension provides the ``do`` tag that can be used to
  execute some code  (similar to a ``{{ ... }}`` block) without generating
  output.
* ``jinja2.ext.loopcontrols``: This extension provides the ``break`` and
  ``continue`` tags that can be used for loop control.
* ``jinja2.ext.with_``: This extension provides the ``with`` tag. Since Jinja
  2.10 this tag is available even when this extension is not loaded.
* `vinegar.template.jinja.SerializerExtension`: This extension provides tags
  and filters for dealing with JSON and YAML. Please refer to the class
  documentation for details.

Please note that these extensions are not available when explicitly setting the
environment's ``extensions`` option through the ``env`` configuration option.
In this case, each extension that is desired has to be mentioned explicitly.

Configuration options
---------------------

The template engine provded by this module supports the following configuration
options that can be passed through the ``config`` dictionary that is passed to
`get_instance`:

:``cache_enabled``:
    This option (a ``bool``) specifies whether caching is enabled. If ``True``
    (the default), templates are only recompiled when the corresponding file
    has been modified. Modification is detected by comparing the file's
    ``ctime`` and ``mtime``. If ``False`` the template is recompiled on each
    request. This can make sense if files are changed rapidly and the time
    stamps provided by the file system do not provide sufficient precision.
    This option is actually handled by the loader, so it will have no effect
    when supplying a custom loader through the ``loader`` environment option.

:``context``:
    This options (a ``dict``) provides extra objects that are made available in
    the template's context. These objects are provided in addition to the
    objects passed through the ``context`` parameter of the
    `~JinjaEngine.render` method. In case of a key collision, objects specified
    via this option take precedence over objects parsed to ``render``.

:``env``:
    This option is used to specify a dict that is used when creating the
    `~jinja2.Environment`. By default three options are passed to the
    environment, unless they are explicitly specified in the ``env`` dict:
    ``autoescape`` is set to ``False`` and ``keep_trailing_newline`` is set to
    ``True``. The ``loader`` is also created automatically based on the
    ``root_dir`` configuration option.

:``provide_python_modules``:
    This option (``None``, a ``str``, or a sequence of ``str``) specifies which
    Python module should be made available through the ``python`` object that
    is added to the context. If ``None`` or empty (the default), the ``python``
    object is not added to the context at all. Each of the strings can either
    be a module name, a wildcard match all sub-modules (e.g.
    ``parent_module.*``), or the global wildcard ``*``, which matches all
    module names. In a template, the attributes of a module that has been
    allowed through this option can be accessed by specifying the combination
    of the module name and the attribute name as an index to the ``python``
    object. For example, if access to the ``os`` module is allowed, the
    following expression can be used in a template:
    ``python["os.stat"]("/path/to/file")``

:``provide_transform_functions``:
    This option (a ``bool``) specifies whether an object with the name
    ``transform`` is added to the context. If ``True`` (the default), the
    ``transform`` object allows easy access to the transformation functions
    provided by `vinegar.transform`. The ``transform`` object is added to the
    globals. This means that it is also going to be available in imported
    templates that are not imported with the context. If
    ``provide_transform_functions`` is ``False``, the ``transform`` object is
    not available from templates. The ``transform`` object can be used like in
    the following example: ``transform['string.to_upper']('This is all
    converted to upper case.')``

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
import functools
import importlib
import json
import os.path
import typing

import jinja2
import jinja2.environment
import jinja2.exceptions
import jinja2.ext
import jinja2.nodes
import jinja2.parser
import yaml

from vinegar.template import TemplateEngine
from vinegar.transform import get_transformation_function
from vinegar.utils.version import version_for_file_path


# pylint: disable=too-few-public-methods
class JinjaEngine(TemplateEngine):
    """
    Template engine using the Jinja 2 library.

    For information about the configuration options supported by this template
    engine, please refer to the
    `module documentation <vinegar.template.jinja>`.
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
            # By default, Jinja resolves includes as relative to the root of
            # the loader. In our case, this is not desirable because our loader
            # does not have a root, so the path gets resolved relative to the
            # current working directory.
            # For this reason, we overload join_path so that includes get
            # resolved relative to the including template.
            return os.path.normpath(os.path.join(parent, "..", template))

    class _Loader(jinja2.BaseLoader):
        """
        Loader for Jinja templates.

        This loader is very similar to the `jinja2.FileSystemLoader`, but it
        does not use a search path but treats every template name as a path on
        the filesystem.
        """

        def __init__(self, cache_enabled=True, encoding="utf-8"):
            self._encoding = encoding
            self._cache_enabled = cache_enabled

        def get_source(self, environment, template):
            # We make the template path absolute, so that we can later resolve
            # relative includes, even if the current working directory has
            # changed in the meantime. This also makes caching easier because
            # we will always use the same path for the same file (unless
            # symbolic links are involved).
            template = os.path.abspath(template)
            # We treat the template name as a file path.
            file_version = version_for_file_path(template)
            try:
                with open(template, "rb") as file_descriptor:
                    file_contents = file_descriptor.read().decode(
                        self._encoding
                    )
            except (FileNotFoundError, IsADirectoryError):
                # We are not interested in the details of why the template was
                # not found, so we do not include the original exception.
                #
                # pylint: disable=raise-missing-from
                raise jinja2.TemplateNotFound(template)

            def up_to_date_with_cache():
                current_file_version = version_for_file_path(template)
                return current_file_version == file_version

            def up_to_date_no_cache():
                return False

            return (
                file_contents,
                template,
                up_to_date_with_cache
                if self._cache_enabled
                else up_to_date_no_cache,
            )

    class _PythonHelper:
        """
        Object that is added to the context under the ``python`` key. This
        object allows access to attributes of Python modules by spcecifying the
        module and attribute name as an index to this object.

        Only modules that have been explicitly allowed can be accessed.

        Example::

            python['os.stat']('/path/to/file')
        """

        def __init__(
            self, allowed_module_names: typing.Union[str, typing.Sequence[str]]
        ):
            if isinstance(allowed_module_names, str):
                allowed_module_names = [allowed_module_names]
            self._allowed_module_names = allowed_module_names
            self._cache: typing.Dict[str, bool] = {}

        def __getitem__(self, key):
            if not isinstance(key, str):
                raise TypeError(f"Invalid key {key!r}: Key must be a str.")
            try:
                module_name, attribute_name = key.rsplit(".", 1)
            except ValueError:
                raise ValueError(  # pylint: disable=raise-missing-from
                    f"Invalid key {key!r}: Key must have the format "
                    "<module name>.<attribute name>."
                )
            self._check_access(module_name)
            python_module = importlib.import_module(module_name)
            return getattr(python_module, attribute_name)

        def _check_access(self, module_name: str):
            try:
                # If the check result has been cached, we use the cached
                # result.
                allowed = self._cache[module_name]
            except KeyError:
                # If the check for the module is not cached, we check whether
                # the module is allowed according to the configuration.
                allowed = False
                for allowed_module_name in self._allowed_module_names:
                    if allowed_module_name == "*":
                        allowed = True
                        break
                    if allowed_module_name.endswith(".*"):
                        if module_name.startswith(allowed_module_name[:-1]):
                            allowed = True
                            break
                    else:
                        if allowed_module_name == module_name:
                            allowed = True
                            break
                # We want to cache the check result. If the cache would grow
                # beyond 1024 entries, we clean it. This is not as efficient as
                # using an LRU cache, but we do not expect to hit this limit in
                # any practical application. and as long as we do not hit the
                # limit, it is more efficient than an LRU cache, because we do
                # not need the logic for updating statistics about cache usage.
                # So, this limit only exists as a safety measure in case of
                # gross misuse.
                if len(self._cache) >= 1024:
                    self._cache.clear()
                self._cache[module_name] = allowed
            if not allowed:
                raise RuntimeError(
                    f"Access to module {module_name!r} is not allowed."
                )

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
        root_dir = config.get("root_dir", None)
        user_env = config.get("env", {})
        relative_includes = config.get("relative_includes", True)
        # We do not allow specifying both a custom loader and the root
        # directory. This would not make sense as that loader would not use the
        # specified root directory.
        if "root_dir" in config and "loader" in user_env:
            raise ValueError(
                "The configuration can either specify the root_dir option "
                "or provide its own loader in the env option, not both."
            )
        # If the root_dir option is specified, we use Jinja's file-system
        # loader with the specified root directory. If not, we use our own
        # loader, that looks for templates on the full file-system (templates
        # names that represent an absolute path are used as is, other template
        # names are resolved relative to the current working directory.
        if root_dir is None:
            loader = self._Loader(
                config.get("cache_enabled", True),
                config.get("encoding", "utf-8"),
            )
        else:
            if config.get("cache_enabled", True):
                loader = jinja2.FileSystemLoader(root_dir)
            else:
                loader = self._NoCacheFileSystemLoader(root_dir)
        env_options = {
            "autoescape": False,
            "extensions": [
                "jinja2.ext.do",
                "jinja2.ext.loopcontrols",
                "vinegar.template.jinja.SerializerExtension",
            ],
            "keep_trailing_newline": True,
            "loader": loader,
        }
        # The with statement has been built into Jinja for a long time, so the
        # with_ extension was removed in Jinja 3.x. For this reason, we check
        # whether the extension actually exists before adding it.
        if hasattr(jinja2.ext, "with_"):
            env_options["extensions"] += ["jinja2.ext.with_"]
        env_options.update(user_env)
        if relative_includes:
            self._environment = self._Environment(**env_options)
        else:
            self._environment = jinja2.Environment(**env_options)
        self._environment.globals["raise"] = self._raise_template_error
        allowed_python_modules = config.get("provide_python_modules", None)
        if allowed_python_modules:
            self._environment.globals["python"] = self._PythonHelper(
                allowed_python_modules
            )
        if config.get("provide_transform_functions", True):
            self._environment.globals["transform"] = self._TransformHelper()
        self._base_context = config.get("context", {})

    def render(
        self, template_path: str, context: typing.Mapping[str, typing.Any]
    ) -> str:
        try:
            template = self._environment.get_template(template_path)
        except jinja2.TemplateNotFound as err:
            raise FileNotFoundError() from err
        merged_context = dict(context)
        merged_context.update(self._base_context)
        try:
            return template.render(**merged_context)
        except jinja2.TemplateNotFound as err:
            raise FileNotFoundError() from err

    @staticmethod
    def _raise_template_error(message):
        raise jinja2.exceptions.TemplateError(message)


class SerializerExtension(jinja2.ext.Extension):
    """
    Jinja extension for dealing with JSON and YAML.

    This extension adds four filters and four tags to Jinja. The four filters
    are:

    * ``load_json`` (parses a JSON string into the corresponding object)
    * ``load_yaml`` (parses a YAML string into the corresponding object)
    * ``json`` (serializes an object into JSON)
    * ``yaml`` (serializes an object into YAML)

    The ``json`` filter has two optional arguments::

        json(sort_keys=False, indent=None)

    The ``sort_keys`` option defines whether keys are in dictionaries are
    sorted when serializing the dictionaries. If it is not set, the keys are
    serialized in iteration order.

    The ``indent`` option defines the number of spaces to use for indentation
    when formatting the output. If ``None``, the output is rendered without
    line breaks and thus without indentation.

    The ``yaml`` filter has one optional argument::

        yaml(flow_style=True)

    If the ``flow_style`` argument is ``True``, the serialization uses the flow
    style, if it the argument is ``False`` it uses the block style. Using the
    block style is problematic when the serialization result is supposed to be
    embedded into another document (because the indentation will typically not
    match the one of the surrounding document).

    The ``load_json`` and ``load_yaml`` filters do not have any arguments.

    The four tags provided by this extension are:

    * ``import_json``
    * ``import_yaml``
    * ``load_json``
    * ``load_yaml``

    Example for ``import_json``:

    .. code-block: jinja

        {% import_json 'json.jinja' as value %}

    This renders the template ``json.jinja``, parses it as JSON, and puts it
    into ``value``. Essentially, it is a shorthand notation for:

    .. code-block: jinja

        {% import 'json.jinja' as value %}
        {% set value = value | load_json %}

    The ``import_yaml`` tag works exactly like the ``import_json`` tag, with
    the exception that it parses YAML instead of JSON:

    .. code-block: jinja

        {% import_yaml 'yaml.jinja' as value %}

    Example for ``load_json``:

    .. code-block: jinja

        {% load_json as value %}
        {"abc": 123, "def": 456}
        {% endload %}

    The ``load_json`` tag takes everything up to the ``endload`` tag and parses
    it as JSON. Essentially, it is a shorthand notation for:

    .. code-block: jinja

        {% set value %}
        {"abc": 123, "def": 456}
        {% endset %}
        {% set value = value | load_json %}

    or (in Jinja 2.10 and newer)

    .. code-block: jinja

        {% set value | load_json %}
        {"abc": 123, "def": 456}
        {% endset %}

    The ``load_yaml`` tag can be used in the same way as the ``load_json`` tag
    with the only exception being that it expects YAML content.

    .. code-block: jinja

        {% load_yaml as value %}
        abc: 123
        def: 456
        {% endload %}
    """

    tags = {"import_json", "import_yaml", "load_json", "load_yaml"}

    def __init__(self, environment: jinja2.Environment):
        super().__init__(environment)
        # Register filters.
        self.environment.filters["load_json"] = self._load_json
        self.environment.filters["load_yaml"] = self._load_yaml
        self.environment.filters["json"] = self._to_json
        self.environment.filters["yaml"] = self._to_yaml

    def parse(
        self, parser: jinja2.parser.Parser
    ) -> typing.Union[jinja2.nodes.Node, typing.List[jinja2.nodes.Node]]:
        tag_name = parser.stream.current.value
        if tag_name == "import_json":
            return self._parse_import(parser, "json")
        if tag_name == "import_yaml":
            return self._parse_import(parser, "yaml")
        if tag_name == "load_json":
            return self._parse_load(parser, "json")
        if tag_name == "load_yaml":
            return self._parse_load(parser, "yaml")
        raise RuntimeError(f"parse called for unexpected tag '{tag_name}'.")

    @staticmethod
    def _load_json(value):
        # We use this filter for our custom import_json tag. In this case, the
        # value that is passed is going to be the imported template, so that we
        # first have to get the string representation (the rendering result) of
        # that template.
        if isinstance(value, jinja2.environment.TemplateModule):
            value = str(value)
        # We catch all exceptions and wrap them inside a TemplateRuntimeError.
        # This way, the code that renders the template does not receive an
        # unexpected type of exception.
        try:
            return json.loads(value)
        except Exception as err:
            raise jinja2.exceptions.TemplateRuntimeError(
                f"Could not decode value as JSON: {value}"
            ) from err

    @staticmethod
    def _load_yaml(value):
        # We use this filter for our custom import_yaml tag. In this case, the
        # value that is passed is going to be the imported template, so that we
        # first have to get the string representation (the rendering result) of
        # that template.
        if isinstance(value, jinja2.environment.TemplateModule):
            value = str(value)
        # We catch all exceptions and wrap them inside a TemplateRuntimeError.
        # This way, the code that renders the template does not receive an
        # unexpected type of exception.
        try:
            return yaml.safe_load(value)
        except Exception as err:
            raise jinja2.exceptions.TemplateRuntimeError(
                f"Could not decode value as YAML: {value}"
            ) from err

    def _parse_import(self, parser: jinja2.parser.Parser, type_name: str):
        # We do not use parser.parse_import here because it is not clear
        # whether that function is part of the stable API (the documentation
        # does not mention that method).
        lineno = next(parser.stream).lineno
        import_node = jinja2.nodes.Import(lineno=lineno)
        import_node.template = parser.parse_expression()
        parser.stream.expect("name:as")
        import_node.target = parser.parse_assign_target(name_only=True).name
        if parser.stream.current.test_any(
            "name:with", "name:without"
        ) and parser.stream.look().test("name:context"):
            import_node.with_context = next(parser.stream).value == "with"
            parser.stream.skip()
        else:
            import_node.with_context = False
        # The import node will take care of loading the referenced template and
        # making its contents available under the specified variable name. We
        # still have to transform the variable by deserializing the JSON or
        # YAML string. We do this by applying the appropriate filter on the
        # variable and assigning the result back to the variable.
        filter_name = "load_" + type_name
        filter_node = jinja2.nodes.Filter(
            jinja2.nodes.Name(import_node.target, "load", lineno=lineno),
            filter_name,
            [],
            [],
            None,
            None,
            lineno=lineno,
        )
        assign_node = jinja2.nodes.Assign(
            jinja2.nodes.Name(import_node.target, "store", lineno=lineno),
            filter_node,
            lineno=lineno,
        )
        return [import_node, assign_node]

    def _parse_load(self, parser, type_name):
        lineno = next(parser.stream).lineno
        parser.stream.expect("name:as")
        target = parser.parse_assign_target(name_only=True).name
        body_nodes = parser.parse_statements(
            ("name:endload",), drop_needle=True
        )
        # Since Jinja 2.10, the AssignBlock node has a filter field that could
        # directly be used to apply a filter. Unfortunately, this would make
        # our code incompatible with earlier versions of Jinja, so we set it to
        # None if it exists and add a separate FilterNode.
        if "filter" in jinja2.nodes.AssignBlock.fields:
            assign_block_node = jinja2.nodes.AssignBlock(
                jinja2.nodes.Name(target, "store", lineno=lineno),
                None,
                body_nodes,
                lineno=lineno,
            )
        else:
            assign_block_node = jinja2.nodes.AssignBlock(
                jinja2.nodes.Name(target, "store", lineno=lineno),
                body_nodes,
                lineno=lineno,
            )
        filter_name = "load_" + type_name
        filter_node = jinja2.nodes.Filter(
            jinja2.nodes.Name(target, "load", lineno=lineno),
            filter_name,
            [],
            [],
            None,
            None,
            lineno=lineno,
        )
        assign_node = jinja2.nodes.Assign(
            jinja2.nodes.Name(target, "store", lineno=lineno),
            filter_node,
            lineno=lineno,
        )
        return [assign_block_node, assign_node]

    @staticmethod
    def _to_json(value, sort_keys=False, indent=None):
        return json.dumps(value, sort_keys=sort_keys, indent=indent)

    @staticmethod
    def _to_yaml(value, flow_style=True):
        text = yaml.safe_dump(value, default_flow_style=flow_style)
        # safe_dump adds a trailing newline character, that we do not want.
        if text.endswith("\n"):
            text = text[:-1]
        # When we are not serializing the value into the flow style, it is not
        # safe for embedding into another document anyway, so there is no need
        # to further post-process it.
        if not flow_style:
            return text
        # When the serialized value is a simple value (like a string, number,
        # etc.) safe_dump adds an end of document marker ("..."). We do not
        # want that marker because it will cause problems when we embed the
        # string into another YAML document.
        if text.endswith("\n..."):
            text = text[:-4]
        return text


def get_instance(
    config: typing.Mapping[typing.Any, typing.Any]
) -> JinjaEngine:
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
