"""
Tests for `vinegar.datasource.text_file`.
"""

import inspect
import os.path
import unittest
import unittest.mock

import vinegar.datasource

from tempfile import TemporaryDirectory

from vinegar.datasource.text_file import TextFileSource

class TestTextFileSource(unittest.TestCase):
    """
    Tests for the `TextFileSource`.
    """

    def test_config_duplicate_system_id_action(self):
        """
        Test the ``duplicate_system_id_action`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            config = _get_base_config(
                tmpdir,
                """
                02:00:00:00:00:01;192.168.0.1;System1
                02:00:00:00:00:02;192.168.0.2;system2,alias1,Alias2
                02:00:00:00:00:0a;192.168.000.3;system3
                02:00:00:00:00:0A;192.168.0.4;system4
                02:00:00:00:00:0b;192.168.0.5;system4
                """)
            # When we do not specify the duplicate_system_id option, it should
            # default to warn.
            ds = TextFileSource(config)
            with unittest.mock.patch(
                    'vinegar.datasource.text_file.logger',
                    autospec=True) as mock_logger:
                ds.get_data('system', {}, '')
                mock_logger.warning.assert_called_once()
            # If the option is set to error, we expect an exception.
            config['duplicate_system_id_action'] = 'error'
            ds = TextFileSource(config)
            with self.assertRaises(ValueError):
                ds.get_data('system', {}, '')
            # If the option is set to ignore, we do not expect a warning to be
            # logged.
            config['duplicate_system_id_action'] = 'ignore'
            ds = TextFileSource(config)
            with unittest.mock.patch(
                    'vinegar.datasource.text_file.logger',
                    autospec=True) as mock_logger:
                ds.get_data('system', {}, '')
                mock_logger.warning.assert_not_called()
            # If the option is explicitly set to warn, we expect the default
            # behavior.
            config['duplicate_system_id_action'] = 'warn'
            ds = TextFileSource(config)
            with unittest.mock.patch(
                    'vinegar.datasource.text_file.logger',
                    autospec=True) as mock_logger:
                ds.get_data('system', {}, '')
                mock_logger.warning.assert_called_once()

    def test_config_find_first_match(self):
        """
        Test the ``find_first_match`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            config = _get_base_config(
                tmpdir,
                """
                02:00:00:00:00:01;192.168.0.1;System1
                02:00:00:00:00:02;192.168.0.2;system2,alias1,Alias2
                02:00:00:00:00:0a;192.168.000.3;system3
                02:00:00:00:00:0A;192.168.0.4;system4
                """)
            # When we do not specify the find_first_match option, it should
            # default to False.
            ds = TextFileSource(config)
            self.assertIsNone(
                ds.find_system('net:mac_addr', '02:00:00:00:00:0A'))
            # If the option is set to True, we expect the first of the two
            # systems to be returned.
            config['find_first_match'] = True
            ds = TextFileSource(config)
            self.assertEqual(
                'system3.mydomain.example.com',
                ds.find_system('net:mac_addr', '02:00:00:00:00:0A'))
            # If we explicitly set the option to False, we expect the default
            # behavior.
            config['find_first_match'] = False
            ds = TextFileSource(config)
            self.assertIsNone(
                ds.find_system('net:mac_addr', '02:00:00:00:00:0A'))

    def test_config_mismatch_action(self):
        """
        Test the ``mismatch_action`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            config = _get_base_config(
                tmpdir,
                """
                # This line should be ignored.
                02:00:00:00:00:01;192.168.0.1;System1

                xx:00:00:00:00:02;192.168.0.2;system2,alias1,Alias2
                02:00:00:00:00:0a;192.168.000.3;system3
                02:00:00:00:00:0A;192.168.0.4;system4
                """)
            # The default mismatch_action is warn, so we should receive a
            # warning about the line with the invalid MAC address.
            ds = TextFileSource(config)
            with unittest.mock.patch(
                    'vinegar.datasource.text_file.logger',
                    autospec=True) as mock_logger:
                ds.get_data('system', {}, '')
                mock_logger.warning.assert_called_once()
            # If we set it to error, we expect an exception.
            config['mismatch_action'] = 'error'
            ds = TextFileSource(config)
            with self.assertRaises(ValueError):
                ds.get_data('system', {}, '')
            # If we set it to ignore, we expect no warning.
            config['mismatch_action'] = 'ignore'
            ds = TextFileSource(config)
            with unittest.mock.patch(
                    'vinegar.datasource.text_file.logger',
                    autospec=True) as mock_logger:
                ds.get_data('system', {}, '')
                mock_logger.warning.assert_not_called()
            # Setting it to warn should have the same effects as the default
            # setting.
            config['mismatch_action'] = 'warn'
            ds = TextFileSource(config)
            with unittest.mock.patch(
                    'vinegar.datasource.text_file.logger',
                    autospec=True) as mock_logger:
                ds.get_data('system', {}, '')
                mock_logger.warning.assert_called_once()

    def test_config_regular_expression_ignore(self):
        """
        Test the ``regular_expression_ignore`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            config = _get_base_config(
                tmpdir,
                """
                # This line should be ignored.
                02:00:00:00:00:01;192.168.0.1;System1

                02:00:00:00:00:02;192.168.0.2;system2,alias1,Alias2
                02:00:00:00:00:0a;192.168.000.3;system3
                02:00:00:00:00:0A;192.168.0.4;system4
                """)
            # Our base configuration already sets a regular expression that
            # ignores empty lines and lines starting with #, so we test that
            # first.
            ds = TextFileSource(config)
            with unittest.mock.patch(
                    'vinegar.datasource.text_file.logger',
                    autospec=True) as mock_logger:
                ds.get_data('system', {}, '')
                mock_logger.warning.assert_not_called()
            # Now we set regular_expression_ignore to None. This should result
            # in two warnings as mismatch_action is set to warn by default.
            config['regular_expression_ignore'] = None
            ds = TextFileSource(config)
            with unittest.mock.patch(
                    'vinegar.datasource.text_file.logger',
                    autospec=True) as mock_logger:
                ds.get_data('system', {}, '')
                self.assertEqual(2, mock_logger.warning.call_count)

    def test_find_system(self):
        """
        Test the `~TextFileSource.find_system` method.
        """
        with TemporaryDirectory() as tmpdir:
            config = _get_base_config(
                tmpdir,
                """
                02:00:00:00:00:01;192.168.0.1;System1
                02:00:00:00:00:0a;192.168.0.2;system2,alias1,Alias2
                02:00:00:00:00:0b;192.168.000.3;system3
                02:00:00:00:00:0B;192.168.0.4;system4
                """)
            ds = TextFileSource(config)
            # We should be able to find system1 and system2 based on the MAC
            # address.
            self.assertEqual(
                'system1.mydomain.example.com',
                ds.find_system('net:mac_addr', '02:00:00:00:00:01'))
            self.assertEqual(
                'system2.mydomain.example.com',
                ds.find_system('net:mac_addr', '02:00:00:00:00:0A'))
            # We should not be able to find system3 and system4 because they
            # share the same MAC address and find_first_match is not set. The
            # effects of setting find_first_match to True are covered by a
            # separate test.
            self.assertIsNone(
                ds.find_system('net:mac_addr', '02:00:00:00:00:0B'))
            # However, we should be able to find both systems by their IP
            # addresses.
            self.assertEqual(
                'system3.mydomain.example.com',
                ds.find_system('net:ipv4_addr', '192.168.0.3'))
            self.assertEqual(
                'system4.mydomain.example.com',
                ds.find_system('net:ipv4_addr', '192.168.0.4'))
            # We should be able to find system2 by its extra names. We do this
            # tests because finding non-hashable values (like lists) has a
            # different code path.
            self.assertEqual(
                'system2.mydomain.example.com',
                ds.find_system('info:extra_names', ['alias1', 'alias2']))

    def test_get_data(self):
        """
        Test the `~TextFileSource.get_data method.
        """
        with TemporaryDirectory() as tmpdir:
            config = _get_base_config(
                tmpdir,
                """
                # This line should be ignored.
                02:00:00:00:00:01;192.168.0.1;System1

                02:00:00:00:00:02;192.168.0.2;system2,alias1,Alias2
                xx:00:00:00:00:0a;192.168.000.3;system3
                02:00:00:00:00:0a;192.168.000.3;system3
                02:00:00:00:00:0A;192.168.0.4;system4
                02:00:00:00:00:0b;192.168.0.5;system4
                """)
            # We disable warnings about duplicate system IDs and mismatches.
            # We test these in separate tests. This test is only about finding
            # that those lines are ignored and other lines are still parsed
            # correctly.
            config['duplicate_system_id_action'] = 'ignore'
            config['mismatch_action'] = 'ignore'
            ds = TextFileSource(config)
            expected_data1a = {
                'net': {
                    'fqdn': 'system1.mydomain.example.com',
                    'hostname': 'system1',
                    'ipv4_addr': '192.168.0.1',
                    'mac_addr': '02:00:00:00:00:01'}}
            data, version1a = ds.get_data(
                'system1.mydomain.example.com', {}, '')
            self.assertEqual(expected_data1a, data)
            expected_data2 = {
                'info': {
                    'extra_names': ['alias1', 'alias2']},
                'net': {
                    'fqdn': 'system2.mydomain.example.com',
                    'hostname': 'system2',
                    'ipv4_addr': '192.168.0.2',
                    'mac_addr': '02:00:00:00:00:02'}}
            data, version2a = ds.get_data(
                'system2.mydomain.example.com', {}, '')
            self.assertEqual(expected_data2, data)
            expected_data3 = {
                'net': {
                    'fqdn': 'system3.mydomain.example.com',
                    'hostname': 'system3',
                    'ipv4_addr': '192.168.0.3',
                    'mac_addr': '02:00:00:00:00:0A'}}
            data, version3a = ds.get_data(
                'system3.mydomain.example.com', {}, '')
            self.assertEqual(expected_data3, data)
            expected_data4 = {
                'net': {
                    'fqdn': 'system4.mydomain.example.com',
                    'hostname': 'system4',
                    'ipv4_addr': '192.168.0.4',
                    'mac_addr': '02:00:00:00:00:0A'}}
            data, version4a = ds.get_data(
                'system4.mydomain.example.com', {}, '')
            self.assertEqual(expected_data4, data)
            # Now we write a fresh data file that uses the same lines for most
            # systems, but changes the line for system1. This should result in
            # a change of the version number for that system only.
            data_file = os.path.join(tmpdir, 'test.txt')
            _write_file(
                data_file,
                """
                02:00:00:00:00:01;192.168.0.6;System1
                02:00:00:00:00:02;192.168.0.2;system2,alias1,Alias2
                02:00:00:00:00:0a;192.168.000.3;system3
                02:00:00:00:00:0A;192.168.0.4;system4
                """)
            expected_data1b = {
                'net': {
                    'fqdn': 'system1.mydomain.example.com',
                    'hostname': 'system1',
                    'ipv4_addr': '192.168.0.6',
                    'mac_addr': '02:00:00:00:00:01'}}
            data, version1b = ds.get_data(
                'system1.mydomain.example.com', {}, '')
            self.assertEqual(expected_data1b, data)
            self.assertNotEqual(version1a, version1b)
            data, version2b = ds.get_data(
                'system2.mydomain.example.com', {}, '')
            self.assertEqual(expected_data2, data)
            self.assertEqual(version2a, version2b)
            data, version3b = ds.get_data(
                'system3.mydomain.example.com', {}, '')
            self.assertEqual(expected_data3, data)
            self.assertEqual(version3a, version3b)
            data, version4b = ds.get_data(
                'system4.mydomain.example.com', {}, '')
            self.assertEqual(expected_data4, data)
            self.assertEqual(version4a, version4b)

def _get_base_config(dir_path, data_text):
    """
    Call `_write_test_data_file` and return a basic configuration that uses the
    generated file.
    """
    file_path = os.path.join(dir_path, 'test.txt')
    _write_file(file_path, data_text)
    return {
        'file': file_path,
        'regular_expression':
            inspect.cleandoc(
                '''
                (?x)
                # We expect a CSV file with three columns that are separated by
                # semicolons.
                # The first column specifies the MAC address.
                (?P<mac>[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5});
                # The second column specifies the IP address.
                (?P<ip>[0-9]{1,3}(?:\.[0-9]{1,3}){3});
                # The third column specifies the hostname and an optional list
                # of additional names.
                (?P<hostname>[^,]+)
                (,(?P<extra_names>.+))?
                '''),
        'regular_expression_ignore': '|(?:#.*)',
        'system_id': {
            'source': 'hostname',
            'transform': [
                {'string.add_suffix': '.mydomain.example.com'},
                'string.to_lower',
            ],
        },
        'variables': {
            'info:extra_names': {
                'source': 'extra_names',
                'transform': [
                    'string.to_lower',
                    {'string.split': ','},
                ],
            },
            'net:fqdn': {
                'source': 'hostname',
                'transform': [
                    {'string.add_suffix': '.mydomain.example.com'},
                    'string.to_lower',
                ],
            },
            'net:hostname': {
                'source': 'hostname',
                'transform': ['string.to_lower'],
            },
            'net:ipv4_addr': {
                'source': 'ip',
                'transform': ['ipv4_address.normalize'],
            },
            'net:mac_addr': {
                'source': 'mac',
                'transform': ['mac_address.normalize'],
            },
        },
    }

def _write_file(path, text):
    """
    Write text to a file, cleaning the text with `inspect.cleandoc` first.

    We use this to generate files for tests.
    """
    with open(path, mode='w') as file:
        file.write(inspect.cleandoc(text))
