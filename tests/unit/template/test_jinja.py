"""
Tests for `vinegar.template.jinja`.
"""

import inspect
import os.path
import pathlib
import time
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
                'some text', engine.render(str(template_path), {}))
            # Now we change the template.
            # We actually try several times with increasing sleep times. On
            # systems, where the time stamp is very precise, the test finishes
            # quickly, on other ones it takes a bit longer.
            sleep_time = 0.01
            while sleep_time < 3.0:
                _write_file(
                    template_path,
                    """
                    {{ 'other text' }}
                    """)
                new_render_result = engine.render(str(template_path), {})
                if 'some text' != new_render_result:
                    break
                time.sleep(sleep_time)
                sleep_time *= 2
            self.assertEqual('other text', new_render_result)

    def test_config_context(self):
        """
        Test the that context objects passed through the ``context``
        configuration option are made available.
        """
        config = {'context': {'abc': 123, 'def': 456}}
        engine = JinjaEngine(config)
        with TemporaryDirectory() as tmpdir:
            # We have to generate a template file that can be read by the
            # template engine.
            tmpdir_path = pathlib.Path(tmpdir)
            template_path = tmpdir_path / 'test.jinja'
            _write_file(
                template_path,
                """
                {{ abc ~ def }}
                """)
            self.assertEqual(
                '123456', engine.render(str(template_path), {}))
            # Context objects supplied to render should not override the context
            # objects from the configuration.
            self.assertEqual(
                '123456',
                engine.render(str(template_path), {'abc': 789}))

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
                'some text', engine.render(str(template_path), {}))

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
            # We disable the cache for this test because it causes problems when
            # we rapidly change files.
            engine = JinjaEngine({'cache_enabled': False})
            self.assertEqual(
                'SOME TEXT',
                engine.render(str(template_path), {}))
            # Explicitly setting provide_transform_functions should not make a
            # difference.
            engine = JinjaEngine(
                {'cache_enabled': False, 'provide_transform_functions': True})
            self.assertEqual(
                'SOME TEXT',
                engine.render(str(template_path), {}))
            # If we provide our own transform object in the context, this should
            # be hidden by the transform object provided by the template engine.
            self.assertEqual(
                'SOME TEXT',
                engine.render(
                    str(template_path),
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
                engine.render(str(template_path), {}))
            # Now, we set provide_transform_functions to False, which should
            # remove the transform object from the context.
            engine = JinjaEngine(
                {'cache_enabled': False, 'provide_transform_functions': False})
            self.assertEqual(
                'False',
                engine.render(str(template_path), {}))
            # If we provide our own transform object, that object should be
            # available.
            _write_file(
                template_path,
                """
                {{ transform }}
                """)
            self.assertEqual(
                'text from context',
                engine.render(
                    str(template_path),
                    {'transform': 'text from context'}))

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
                engine.render(str(template_path), {})

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
            saved_mode = template_path.stat().st_mode
            template_path.chmod(0)
            # On some platforms, the temporary directory cannot be deleted if
            # there is a file for which we lack the permissions, so we change it
            # back when we are done.
            try:
                try:
                    with open(str(template_path), 'rb'):
                        file_readable = True
                except PermissionError:
                    file_readable = False
                if not file_readable:
                    with self.assertRaises(PermissionError):
                        engine.render(str(template_path), {})
            finally:
                template_path.chmod(saved_mode)

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
                    str(tmpdir_path / 'include2.jinja'))}
            self.assertEqual(
                'this is from the included template',
                engine.render(str(template_path), context))

def _write_file(path, text):
    """
    Write text to a file, cleaning the text with `inspect.cleandoc` first.

    We use this to generate configuration files for tests.
    """
    if isinstance(path, pathlib.PurePath):
        path = str(path)
    with open(path, mode='w') as file:
        file.write(inspect.cleandoc(text))
