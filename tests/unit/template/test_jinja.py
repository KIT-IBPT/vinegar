"""
Tests for `vinegar.template.jinja`.
"""

import inspect
import os.path
import pathlib
import unittest

import vinegar.template
import vinegar.template.jinja

from tempfile import TemporaryDirectory

from vinegar.template.jinja import JinjaEngine

class TestJinjaEngine(unittest.TestCase):
    """
    Tests for the `JinjaEngine`.
    """

    def test_cache_invalidation(self):
        """
        Test that a template is compiled again when its file changes.
        """
        engine = JinjaEngine({})
        with TemporaryDirectory() as tmpdir:
            # We have to generate a template file that can be read by the
            # template engine.
            tmpdir_path = pathlib.Path(tmpdir)
            template_path = tmpdir_path / 'test.jinja'
            _write_file(
                template_path,
                """
                {{ 'some text' }}
                """)
            self.assertEqual(
                'some text', engine.render(template_path.as_posix(), {}))
            # Now we change the template.
            _write_file(
                template_path,
                """
                {{ 'other text' }}
                """)
            self.assertEqual(
                'other text', engine.render(template_path.as_posix(), {}))

    def test_config_env(self):
        """
        Test the that options passed through ``config['env']`` are actually
        passed on to the Jinja environment.
        """
        # The easiest thing that we can test is that replacing the variable
        # start and end strings (default '{{' and '}}') has the expected effect.
        config = {
            'env': {
                'variable_start_string': '{!',
                'variable_end_string': '!}'}}
        engine = JinjaEngine(config)
        with TemporaryDirectory() as tmpdir:
            # We have to generate a template file that can be read by the
            # template engine.
            tmpdir_path = pathlib.Path(tmpdir)
            template_path = tmpdir_path / 'test.jinja'
            _write_file(
                template_path,
                """
                {! 'some text' !}
                """)
            self.assertEqual(
                'some text', engine.render(template_path.as_posix(), {}))

    def test_config_provide_transform_functions(self):
        """
        Test the ``provide_transform_functions`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We have to generate a template file that can be read by the
            # template engine.
            tmpdir_path = pathlib.Path(tmpdir)
            template_path = tmpdir_path / 'test.jinja'
            _write_file(
                template_path,
                """
                {{ transform['string.to_upper']('Some text') }}
                """)
            engine = JinjaEngine({})
            self.assertEqual(
                'SOME TEXT',
                engine.render(template_path.as_posix(), {}))
            # Explicitly setting proide_transform_functions should not make a
            # difference.
            engine = JinjaEngine({'provide_transform_functions': True})
            self.assertEqual(
                'SOME TEXT',
                engine.render(template_path.as_posix(), {}))
            # If provide our own transform object in the context, this should
            # override the automatically provided transform object.
            _write_file(
                template_path,
                """
                {{ transform }}
                """)
            self.assertEqual(
                'text from context',
                engine.render(
                    template_path.as_posix(),
                    {'transform': 'text from context'}))
            # The "is defined" check should succeed if there is a transform
            # object, and fail if there is none.
            _write_file(
                template_path,
                """
                {{ transform is defined }}
                """)
            self.assertEqual(
                'True',
                engine.render(template_path.as_posix(), {}))
            # Now, we set provide_transform_functions to False, which should
            # remove the transform object from the context.
            engine = JinjaEngine({'provide_transform_functions': False})
            self.assertEqual(
                'False',
                engine.render(template_path.as_posix(), {}))

    def test_config_relative_includes_and_root_dir(self):
        """
        Test the ``relative_includes`` and ``root_dir`` configuration options.

        As setting ``relative_includes`` to ``True`` is the default, this is
        already covered by the other tests. Here, we test it with a value of
        ``False``.

        As a side effect, we also test the `root_dir` option because using
        ``relative_includes == False`` without that option does not make a lot
        of sense.
        """
        with TemporaryDirectory() as tmpdir:
            config = {'relative_includes': False, 'root_dir': tmpdir}
            engine = JinjaEngine(config)
            # We have to generate a template file that can be read by the
            # template engine.
            tmpdir_path = pathlib.Path(tmpdir)
            (tmpdir_path / 'testdir').mkdir()
            template_path = tmpdir_path / 'testdir' / 'test.jinja'
            # All includes should be treated as relative to the root directory
            # of the loader. First, we test this with a template name that does
            # not suggest an absolute path.
            _write_file(
                template_path,
                """
                {% include 'include1.jinja' %}
                """)
            # Second, we test it with a template name that suggests an absolute
            # path. This should not make a difference.
            _write_file(
                tmpdir_path / 'include1.jinja',
                """
                {% include '/include2.jinja' %}
                """)
            _write_file(
                tmpdir_path / 'include2.jinja',
                """
                this is from the included template
                """)
            self.assertEqual(
                'this is from the included template',
                engine.render('testdir/test.jinja', {}))
            # Using a template name that starts with a forward slash should not
            # make a difference.
            self.assertEqual(
                'this is from the included template',
                engine.render('/testdir/test.jinja', {}))

    def test_file_not_found(self):
        """
        Test that the `~JinjaEngine.render` method raises a
        ``FileNotFoundError`` if the template file does not exist.
        """
        engine = JinjaEngine({})
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = pathlib.Path(tmpdir)
            template_path = tmpdir_path / 'test.jinja'
            with self.assertRaises(FileNotFoundError):
                engine.render(template_path.as_posix(), {})

    def test_file_permission_denied(self):
        """
        Test that the `~JinjaEngine.render` method raises a ``PermissionError``
        if the template file is not readable.

        This test is limited to platforms where we can actually make the file
        not readable (where ``chmod`` works).
        """
        engine = JinjaEngine({})
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = pathlib.Path(tmpdir)
            template_path = tmpdir_path / 'test.jinja'
            _write_file(template_path, 'We do not care about the content')
            template_path.chmod(0)
            try:
                with open(template_path.as_posix(), 'rb'):
                    file_readable = True
            except PermissionError:
                file_readable = False
            if not file_readable:
                with self.assertRaises(PermissionError):
                    engine.render(template_path.as_posix(), {})

    def test_get_instance(self):
        """
        Test that the template engine can be instantiated via
        `vinegar.template.get_template_engine`.
        """
        engine = vinegar.template.get_template_engine('jinja', {})
        self.assertIsInstance(engine, JinjaEngine)

    def test_include(self):
        """
        Test that included templates are resolved.
        """
        engine = JinjaEngine({})
        with TemporaryDirectory() as tmpdir:
            # We have to generate a template file that can be read by the
            # template engine.
            tmpdir_path = pathlib.Path(tmpdir)
            template_path = tmpdir_path / 'test.jinja'
            # The first include is relative.
            _write_file(
                template_path,
                """
                {% include 'include1.jinja' %}
                """)
            # The second include is absolute.
            _write_file(
                tmpdir_path / 'include1.jinja',
                """
                {% include include2 %}
                """)
            _write_file(
                tmpdir_path / 'include2.jinja',
                """
                this is from the included template
                """)
            context = {
                'include2': os.path.abspath(
                    (tmpdir_path / 'include2.jinja').as_posix())}
            self.assertEqual(
                'this is from the included template',
                engine.render(template_path.as_posix(), context))

def _write_file(path, text):
    """
    Write text to a file, cleaning the text with `inspect.cleandoc` first.

    We use this to generate configuration files for tests.
    """
    if isinstance(path, pathlib.PurePath):
        path = path.as_posix()
    with open(path, mode='w') as file:
        file.write(inspect.cleandoc(text))
