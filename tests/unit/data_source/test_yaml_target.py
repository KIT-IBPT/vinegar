"""
Tests for `vinegar.data_source.yaml_target`.
"""

import inspect
import os
import pathlib
import time
import unittest

from tempfile import TemporaryDirectory

import vinegar.data_source
import vinegar.data_source.yaml_target

from vinegar.data_source.yaml_target import YamlTargetSource


class TestYamlTargetSource(unittest.TestCase):
    """
    Tests for the `YamlTargetSource`.
    """

    def test_cache_invalidation(self):
        """
        Test that files are reread when they have changed (instead of reusing)
        cached values. This also tests that resulting version numbers change
        when files change.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                key: 1
                """,
            )
            (data, version1) = ds.get_data("dummy", {}, "")
            self.assertEqual({"key": 1}, data)
            # Now we update a.yaml.
            # We actually try several times with increasing sleep times. On
            # systems, where the time stamp is very precise, the test finishes
            # quickly, on other ones it takes a bit longer.
            sleep_time = 0.01
            while sleep_time < 3.0:
                _write_file(
                    root_dir_path / "a.yaml",
                    """
                    key: 2
                    """,
                )
                (data, version2) = ds.get_data("dummy", {}, "")
                if version1 != version2:
                    break
                time.sleep(sleep_time)
                sleep_time *= 2
            self.assertEqual({"key": 2}, data)
            self.assertNotEqual(version1, version2)
            # Now we update top.yaml.
            # We actually try several times with increasing sleep times. On
            # systems, where the time stamp is very precise, the test finishes
            # quickly, on other ones it takes a bit longer.
            sleep_time = 0.01
            while sleep_time < 3.0:
                _write_file(
                    root_dir_path / "top.yaml",
                    """
                    '*':
                        - b
                    """,
                )
                _write_file(
                    root_dir_path / "b.yaml",
                    """
                    key: 3
                    """,
                )
                (data, version3) = ds.get_data("dummy", {}, "")
                if version2 != version3:
                    break
                time.sleep(sleep_time)
                sleep_time *= 2
            self.assertEqual({"key": 3}, data)
            self.assertNotEqual(version2, version3)

    def test_cache_invalidation_import(self):
        """
        Test that a template is rendered again when a template that is imported
        by that template changes. This specifically tests for a bug that we had
        in a pre-release version.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                {% from 'b.yaml' import value %}
                key: {{ value }}
                """,
            )
            _write_file(
                root_dir_path / "b.yaml",
                """
                {% set value = 1 %}
                """,
            )
            (data, version1) = ds.get_data("dummy", {}, "")
            self.assertEqual({"key": 1}, data)
            # Now we update b.yaml.
            # We actually try several times with increasing sleep times. On
            # systems, where the time stamp is very precise, the test finishes
            # quickly, on other ones it takes a bit longer.
            sleep_time = 0.01
            while sleep_time < 3.0:
                _write_file(
                    root_dir_path / "b.yaml",
                    """
                    {% set value = 2 %}
                    """,
                )
                (data, version2) = ds.get_data("dummy", {}, "")
                if version1 != version2:
                    break
                time.sleep(sleep_time)
                sleep_time *= 2
            self.assertEqual({"key": 2}, data)
            self.assertNotEqual(version1, version2)

    def test_config_allow_empty_top(self):
        """
        Test the 'allow_empty_top' configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We disable the cache for this test because it causes problems
            # when we rapidly make changes to the files. We also have to
            # disable the template cache, because that could cause problems,
            # too.
            ds = YamlTargetSource(
                {
                    "cache_size": 0,
                    "root_dir": tmpdir,
                    "template_config": {"cache_enabled": False},
                }
            )
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                """,
            )
            # Without allow_empty_top set, an empty top file should result in a
            # type error.
            with self.assertRaises(TypeError):
                ds.get_data("dummy", {}, "")
            # Now we enable the option and test again.
            ds = YamlTargetSource(
                {
                    "allow_empty_top": True,
                    "cache_size": 0,
                    "root_dir": tmpdir,
                    "template_config": {"cache_enabled": False},
                }
            )
            ds.get_data("dummy", {}, "")
            # A top file that is invalid (e.g. provides a list instead of a
            # dict) should still result in a type error.
            _write_file(
                root_dir_path / "top.yaml",
                """
                - foo
                - bar
                """,
            )
            with self.assertRaises(TypeError):
                ds.get_data("dummy", {}, "")

    def test_config_cache_size(self):
        """
        Test the 'cache_size' configuration option.

        In fact, there is no simple way of testing that changes in the size
        actually have the desired effect, but we can test that disabling the
        cache by setting the size to zero works.

        We do not test here that caching works for a non-zero this. This test
        is handled by `test_cache`.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir, "cache_size": 0})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                key: {{ data['input'] }}
                """,
            )
            (data, _) = ds.get_data("dummy", {"input": 1}, "1")
            self.assertEqual({"key": 1}, data)
            # Now we change the input, but do not update the corresponding
            # version number. If the cache was enabled, we would still get the
            # old data (as tested in test_cache).
            # Please note that we cannot test the version number here because
            # it might actually be the same (we did not change the input
            # version, so the code cannot know that a different version number
            # should be generated).
            (data, _) = ds.get_data("dummy", {"input": 2}, "1")
            self.assertEqual({"key": 2}, data)

    def test_config_merge_lists(self):
        """
        Test the 'merge_lists' configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                    - b
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                key:
                    - 3
                    - 4
                    - 5
                """,
            )
            _write_file(
                root_dir_path / "b.yaml",
                """
                key:
                    - 1
                    - 2
                    - 3
                """,
            )
            (data, _) = ds.get_data("dummy", {}, "")
            # We expect that the lists have not been merged and the second
            # definition has replaced the first definition instead.
            self.assertEqual([1, 2, 3], data["key"])
            # Now we repeat the test, but this time we set merge_lists to True.
            ds = YamlTargetSource({"root_dir": tmpdir, "merge_lists": True})
            (data, _) = ds.get_data("dummy", {}, "")
            # Now the elements that are defined later should be appended, but
            # only those elements that were not already present.
            self.assertEqual([3, 4, 5, 1, 2], data["key"])

    def test_config_merge_sets(self):
        """
        Test the 'merge_sets' configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                    - b
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                key: !!set
                    1: null
                    2: null
                    3: null
                """,
            )
            _write_file(
                root_dir_path / "b.yaml",
                """
                key: !!set
                    2: null
                    4: null
                    5: null
                """,
            )
            (data, _) = ds.get_data("dummy", {}, "")
            # We expect that the lists have not been merged and the second
            # definition has replaced the first definition instead.
            self.assertEqual({1, 2, 3, 4, 5}, data["key"])
            # Now we repeat the test, but this time we set merge_sets to False.
            ds = YamlTargetSource({"root_dir": tmpdir, "merge_sets": False})
            (data, _) = ds.get_data("dummy", {}, "")
            # Now the elements that are defined later should be appended, but
            # only those elements that were not already present.
            self.assertEqual({2, 4, 5}, data["key"])

    def test_config_template(self):
        """
        Test the 'template' configuration option.

        We cannot possibly test all template engines and the default Jinja
        engine is already covered by `test_jinja`, so we only test that setting
        ``template`` to ``None`` disables templating.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir, "template": None})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                key: {{ data['input'] }}
                """,
            )
            # As the file is not rendered by Jinja, we end up with invalid
            # YAML, so we expect an exception.
            with self.assertRaises(RuntimeError):
                ds.get_data("dummy", {"input": 1}, "1")
            # Now we fix the file so that it does not use Jinja and we expect
            # that we now get the data.
            _write_file(
                root_dir_path / "a.yaml",
                """
                key: test
                """,
            )
            self.assertEqual(
                {"key": "test"}, ds.get_data("dummy", {"input": 1}, "1")[0]
            )

    def test_config_template_config(self):
        """
        Test the 'template_config' configuration option.

        This test simply tests that the options are passed on to the template
        engine.
        """
        with TemporaryDirectory() as tmpdir:
            # The easiest thing that we can test is that replacing the variable
            # start and end strings (default '{{' and '}}') has the expected
            # effect.
            template_config = {
                "env": {
                    "variable_start_string": "{!",
                    "variable_end_string": "!}",
                }
            }
            ds = YamlTargetSource(
                {"root_dir": tmpdir, "template_config": template_config}
            )
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                key: {! data['input'] !}
                """,
            )
            self.assertEqual(
                {"key": 1}, ds.get_data("dummy", {"input": 1}, "1")[0]
            )

    def test_deep_copy(self):
        """
        Test that modifying the data returned by ``get_data`` or modifying an
        object passed to the template context does not affect future calls or
        other templates.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                    - b
                """,
            )
            # We modify one of the context objects in the first template. This
            # change should not be visible in the second template.
            _write_file(
                root_dir_path / "a.yaml",
                """
                {%- do data['key'].update({'abc': 'def'}) -%}
                a: {{ data['key']['abc'] }}
                """,
            )
            _write_file(
                root_dir_path / "b.yaml",
                """
                b: {{ data['key']['abc'] }}
                """,
            )
            data, _ = ds.get_data("dummy", {"key": {"abc": "abc"}}, "")
            self.assertEqual({"a": "def", "b": "abc"}, data)
            # Now we modify the returned data and check that the (cached) data
            # returned by get_data does not change.
            data["other"] = 123
            data, _ = ds.get_data("dummy", {"key": {"abc": "abc"}}, "")
            self.assertEqual({"a": "def", "b": "abc"}, data)

    def test_get_instance(self):
        """
        Test that the data source can be instantiated via
        `vinegar.data_source.get_data_source`.
        """
        with TemporaryDirectory() as tmpdir:
            ds = vinegar.data_source.get_data_source(
                "yaml_target", {"root_dir": tmpdir}
            )
            self.assertIsInstance(ds, YamlTargetSource)

    def test_include_dot_only(self):
        """
        Test that an include name must not only contain dots.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a.b
                """,
            )
            (root_dir_path / "a").mkdir()
            _write_file(
                root_dir_path / "a" / "init.yaml",
                """
                some_key: 123
                """,
            )
            (root_dir_path / "a" / "b").mkdir()
            _write_file(
                root_dir_path / "a" / "b" / "init.yaml",
                """
                include:
                    - ..
                """,
            )
            # We expect a RuntimeError because ".." is not a valid reference
            # (it only consits of dots).
            with self.assertRaises(RuntimeError) as assertion:
                ds.get_data("dummy", {}, "")
            self.assertTrue(
                str(assertion.exception).startswith(
                    "Invalid reference in include section "
                )
            )

    def test_include_empty_name(self):
        """
        Test that an include name must not be empty.
        """
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = pathlib.Path(tmpdir)
            root_dir = tmpdir_path / "root"
            root_dir.mkdir()
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                include:
                    - ''
                """,
            )
            _write_file(
                tmpdir_path / ".yaml",
                """
                some_key: 123
                """,
            )
            _write_file(
                tmpdir_path / "init.yaml",
                """
                some_key: 456
                """,
            )
            # We expect a RuntimeError because the file name in the include
            # section is empty.
            with self.assertRaises(RuntimeError) as assertion:
                ds.get_data("dummy", {}, "")
            self.assertTrue(
                str(assertion.exception).startswith(
                    "Invalid reference in include section "
                )
            )

    def test_include_merging(self):
        """
        Test that the precedence order is maintained when merging included
        files.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                'dum*':
                    - c
                'dummy':
                    - b
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                a_before_include: 1
                include:
                    - a_inc
                a_after_include: 2
                """,
            )
            _write_file(
                root_dir_path / "a_inc.yaml",
                """
                a_before_include: 3
                a_after_include: 4
                a_from_include: 5
                """,
            )
            _write_file(
                root_dir_path / "b.yaml",
                """
                include:
                    - b_inc
                b_after_include: 1
                """,
            )
            _write_file(
                root_dir_path / "b_inc.yaml",
                """
                b_after_include: 2
                b_from_include: 3
                """,
            )
            _write_file(
                root_dir_path / "c.yaml",
                """
                c_before_include: 1
                include:
                    - c_inc
                """,
            )
            _write_file(
                root_dir_path / "c_inc.yaml",
                """
                c_before_include: 2
                c_from_include: 3
                """,
            )
            verify_data = {}
            verify_data["a_before_include"] = 3
            verify_data["a_after_include"] = 2
            verify_data["a_from_include"] = 5
            verify_data["c_before_include"] = 2
            verify_data["c_from_include"] = 3
            verify_data["b_after_include"] = 1
            verify_data["b_from_include"] = 3
            data = ds.get_data("dummy", {}, "")[0]
            self.assertEqual(verify_data, data)
            # We also want to check that the keys have the expected order.
            self.assertEqual(list(verify_data.keys()), list(data.keys()))

    def test_jinja(self):
        """
        Test that Jinja templates can be used in the top.yaml and data files.
        """
        with TemporaryDirectory() as tmpdir:
            # We have to set the allow_empty_top option in order to avoid an
            # error message when the Jinja if statement does not match.
            ds = YamlTargetSource(
                {"root_dir": tmpdir, "allow_empty_top": True}
            )
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                # '*' would target all systems, but we only generate it when
                # the system ID matches
                {% if id == 'specific' %}
                '*':
                    - a
                {% endif %}
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                key:
                {% for value in [1, 2, 3] %}
                    - {{ value }}
                {% endfor %}
                """,
            )
            self.assertEqual({}, ds.get_data("dummy", {}, "")[0])
            self.assertEqual(
                {"key": [1, 2, 3]}, ds.get_data("specific", {}, "")[0]
            )

    def test_key_order(self):
        """
        Test that the key order is preserved.

        This should always happen because dicts are ordered, but we still test
        it in order to make sure nothing funny happens in the YAML parser or
        data-source implementation.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                z: 1
                y: 2
                a: 3
                b: 4
                h: 5
                d: 6
                i: 7
                m: 8
                l: 9
                n: 10
                """,
            )
            data = ds.get_data("dummy", {}, "")[0]
            keys = list(data.keys())
            values = list(data.values())
            self.assertEqual(
                ["z", "y", "a", "b", "h", "d", "i", "m", "l", "n"], keys
            )
            self.assertEqual(list(range(1, 11)), values)

    def test_recursion_loop(self):
        """
        Test that recursive includes result in an exception.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                include:
                    - b

                some_key: abc
                """,
            )
            _write_file(
                root_dir_path / "b.yaml",
                """
                include:
                    - a

                some_other_key: 123
                """,
            )
            # We expect a RuntimeError because of the include loop.
            with self.assertRaises(RuntimeError) as assertion:
                ds.get_data("dummy", {}, "")
            self.assertTrue(
                str(assertion.exception).startswith("Recursion loop detected")
            )

    def test_recursion_loop_with_init_file(self):
        """
        Test that an ``init.yaml`` file cannot include itself.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                """,
            )
            (root_dir_path / "a").mkdir()
            _write_file(
                root_dir_path / "a" / "init.yaml",
                """
                include:
                    - a.init

                some_key: abc
                """,
            )
            # We expect a RuntimeError because of the include loop.
            with self.assertRaises(RuntimeError) as assertion:
                ds.get_data("dummy", {}, "")
            self.assertTrue(
                str(assertion.exception).startswith("Recursion loop detected")
            )
        # We test the same thing again, but this time we use “a.init” the top
        # file and “a” in the includes list.
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a.init
                """,
            )
            (root_dir_path / "a").mkdir()
            _write_file(
                root_dir_path / "a" / "init.yaml",
                """
                include:
                    - a

                some_key: abc
                """,
            )
            # We expect a RuntimeError because of the include loop.
            with self.assertRaises(RuntimeError) as assertion:
                ds.get_data("dummy", {}, "")
            self.assertTrue(
                str(assertion.exception).startswith("Recursion loop detected")
            )

    def test_relative_include(self):
        """
        Test that relative include names can be used.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                """,
            )
            (root_dir_path / "a").mkdir()
            _write_file(
                root_dir_path / "a" / "init.yaml",
                """
                include:
                    - ..b.sub1
                """,
            )
            (root_dir_path / "b").mkdir()
            _write_file(
                root_dir_path / "b" / "sub1.yaml",
                """
                include:
                  - .sub2
                """,
            )
            _write_file(
                root_dir_path / "b" / "sub2.yaml",
                """
                include:
                  - .init
                """,
            )
            _write_file(
                root_dir_path / "b" / "init.yaml",
                """
                include:
                  - ..c
                """,
            )
            _write_file(
                root_dir_path / "c.yaml",
                """
                test_key: 12345
                """,
            )
            verify_data = {"test_key": 12345}
            data = ds.get_data("dummy", {}, "")[0]
            self.assertEqual(verify_data, data)

    def test_relative_include_outside_root(self):
        """
        Test that a relative include cannot point outside the file tree.
        """
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = pathlib.Path(tmpdir)
            root_dir_path = tmpdir_path / "root"
            root_dir_path.mkdir()
            ds = YamlTargetSource({"root_dir": os.fspath(root_dir_path)})
            # We have to fill the configuration directory with files that the
            # data source can read.
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a.b
                """,
            )
            (root_dir_path / "a").mkdir()
            _write_file(
                root_dir_path / "a" / "b.yaml",
                """
                include:
                    - ...c

                some_key: abc
                """,
            )
            _write_file(
                tmpdir_path / "c.yaml",
                """
                some_key: 123
                """,
            )
            # We expect a RuntimeError because "...c" references a file that is
            # outside the root directory of the file tree.
            with self.assertRaises(RuntimeError) as assertion:
                ds.get_data("dummy", {}, "")
            self.assertTrue(
                str(assertion.exception).startswith(
                    "Invalid reference in include section "
                )
            )

    def test_template_context(self):
        """
        Test that the template gets the expected context objects.

        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - a
                """,
            )
            _write_file(
                root_dir_path / "a.yaml",
                """
                id: {{ id }}
                data: {{ data.get('abc:def:ghi') }}
                """,
            )
            # We use nested dicts for the input data so that we can test that
            # the data object is indeed a smart lookup dict.
            input_data = {"abc": {"def": {"ghi": 123}}}
            self.assertEqual(
                {"id": "dummy", "data": 123},
                ds.get_data("dummy", input_data, "1")[0],
            )

    def test_top_empty_name(self):
        """
        Test that the top file must not reference an empty file name.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - ''
                """,
            )
            _write_file(
                root_dir_path / ".yaml",
                """
                some_key: 123
                """,
            )
            _write_file(
                root_dir_path / "init.yaml",
                """
                some_key: 456
                """,
            )
            # We expect a RuntimeError because the file name in the include
            # section is empty.
            with self.assertRaises(RuntimeError) as assertion:
                ds.get_data("dummy", {}, "")
            self.assertTrue(
                str(assertion.exception).startswith("Invalid file list in ")
            )

    def test_top_targeting(self):
        """
        Tests that the targeting mechanism in ``top.yaml`` works.
        """
        with TemporaryDirectory() as tmpdir:
            ds = YamlTargetSource({"root_dir": tmpdir})
            # If there is no top file, we expect an exception when we try to
            # get data for a system.
            with self.assertRaises(FileNotFoundError):
                ds.get_data("dummy", {}, "")
            # We have to fill the configuration directory with files that the
            # data source can read.
            root_dir_path = pathlib.Path(tmpdir)
            app_dir_path = root_dir_path / "app"
            app_dir_path.mkdir()
            common_dir_path = root_dir_path / "common"
            common_dir_path.mkdir()
            domain_dir_path = root_dir_path / "domain"
            domain_dir_path.mkdir()
            _write_file(
                root_dir_path / "top.yaml",
                """
                '*':
                    - common
                '*.example.com':
                    - domain.com
                '*.example.net':
                    - domain.net
                'db-* or database-*':
                    - app.db
                'www.* or web.* or @data_glob/i:roles:web@true':
                    - app.web
                """,
            )
            # We make a quick test before creating the state files, where we
            # expect a FileNotFoundError due to the data file missing.
            with self.assertRaises(FileNotFoundError):
                ds.get_data("dummy", {}, "")
            # We add the data file needed by all systems.
            _write_file(
                common_dir_path / "init.yaml",
                """
                disks:
                  root: 16G
                  var: 100G
                """,
            )
            # Now it should be possible to get data for a host that only
            # matches the '*' pattern.
            self.assertEqual(
                {"disks": {"root": "16G", "var": "100G"}},
                ds.get_data("dummy", {}, "")[0],
            )
            # Getting data for one of the systems that needs additional files
            # should still fail.
            with self.assertRaises(FileNotFoundError):
                ds.get_data("myhost.example.com", {}, "")
            # We add the remaining data files.
            _write_file(
                domain_dir_path / "com.yaml",
                """
                dnsdomain: example.com
                """,
            )
            _write_file(
                domain_dir_path / "net.yaml",
                """
                dnsdomain: example.net
                """,
            )
            _write_file(
                app_dir_path / "db.yaml",
                """
                disks:
                    var: 1T
                """,
            )
            _write_file(
                app_dir_path / "web.yaml",
                """
                disks:
                    home: 200G
                """,
            )
            # Now we can test that the returned data is okay for other hosts.
            self.assertEqual(
                {
                    "disks": {"root": "16G", "var": "100G"},
                    "dnsdomain": "example.com",
                },
                ds.get_data("foo.example.com", {}, "")[0],
            )
            self.assertEqual(
                {
                    "disks": {"root": "16G", "var": "1T"},
                    "dnsdomain": "example.com",
                },
                ds.get_data("db-1.example.com", {}, "")[0],
            )
            self.assertEqual(
                {
                    "disks": {"root": "16G", "var": "1T"},
                    "dnsdomain": "example.net",
                },
                ds.get_data("database-4.example.net", {}, "")[0],
            )
            self.assertEqual(
                {
                    "disks": {"home": "200G", "root": "16G", "var": "100G"},
                    "dnsdomain": "example.com",
                },
                ds.get_data("www.example.com", {}, "")[0],
            )
            # The system should also be treated as a web server if the
            # roles:web flag is set in the system data from the preceding
            # sources.
            self.assertEqual(
                {
                    "disks": {"home": "200G", "root": "16G", "var": "100G"},
                    "dnsdomain": "example.net",
                },
                ds.get_data(
                    "some-server.example.net", {"roles": {"web": True}}, "v1"
                )[0],
            )
            # If the flag is not set, the system should not be treated as a web
            # server. We have to given a different version string in order to
            # avoid using a cached result.
            self.assertEqual(
                {
                    "disks": {"root": "16G", "var": "100G"},
                    "dnsdomain": "example.net",
                },
                ds.get_data(
                    "some-server.example.net", {"roles": {"web": False}}, "v2"
                )[0],
            )


def _write_file(path, text):
    """
    Write text to a file, cleaning the text with `inspect.cleandoc` first.

    We use this to generate configuration files for tests.
    """
    if isinstance(path, pathlib.PurePath):
        path = str(path)
    with open(path, mode="w") as file:
        file.write(inspect.cleandoc(text))
