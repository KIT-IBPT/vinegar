"""
Tests for `vinegar.request_handler.file`.
"""

import abc
import inspect
import io
import pathlib
import shutil
import unittest

from http import HTTPStatus
from http.client import HTTPMessage
from tempfile import TemporaryDirectory

from vinegar.data_source import DataSource
from vinegar.request_handler.file import (
    HttpFileRequestHandler,
    TftpFileRequestHandler,
    get_instance_http,
    get_instance_tftp)
from vinegar.tftp.protocol import ErrorCode as TftpErrorCode
from vinegar.tftp.server import TftpError


class TestFileRequestHandlerBase(unittest.TestCase, abc.ABC):
    """
    Base class for `TestHttpFileRequestHandler` and
    `TestTftpFileRequestHandler`.
    """

    @abc.abstractmethod
    def call_handle(
            self,
            handler,
            filename,
            expect_can_handle=True,
            expect_status=None,
            expect_headers=None,
            method='GET'):
        """
        Helper method that we use to call ``prepare_context``, ``can_handle``
        and ``handle`` in succession.

        As the signature of this methods depends on the type of the handler
        (HTTP or TFTP), this method is abstract in the base class.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_request_handler(self, config, data_source=None):
        """
        Create a request handler for the specific configuration.

        This is an abstract method because depending on the sub-class, we want
        to create an instance of `HttpFileRequestHandler` or
        `TftpFileRequestHandler`.
        """
        raise NotImplementedError()

    def test_config_file(self):
        """
        Test the ``file`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create a single file that can be served by the handler.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            _write_file(file_path, 'Test 123')
            # We only test the handler with a prefix because attaching it to the
            # root is only allowed for HTTP when operating in file mode.
            config = {'request_path': '/test', 'file': str(file_path)}
            handler = self.get_request_handler(config)
            file_content = self.call_handle(
                handler, '/test', expect_status=HTTPStatus.OK)
            self.assertEqual('Test 123', file_content.decode())
            self.call_handle(handler, '/test/', expect_can_handle=False)
            self.call_handle(handler, '/test/abc', expect_can_handle=False)
            # We test that the handler returns a "not found" result if the file
            # does not exist.
            config['file'] = str(temp_path / 'no_such_file.txt')
            handler = self.get_request_handler(config)
            self.call_handle(
                handler, '/test', expect_status=HTTPStatus.NOT_FOUND)
            # We repeat this test while using a template engine.
            config['template'] = 'jinja'
            handler = self.get_request_handler(config)
            self.call_handle(
                handler, '/test', expect_status=HTTPStatus.NOT_FOUND)
            del config['template']
            # We test that the handler correctly indicates when a file exists,
            # but is not readable. We can only test this on platforms where we
            # can make the file "not readable" by using chmod.
            saved_mode = file_path.stat().st_mode
            file_path.chmod(0)
            # On some platforms, the temporary directory cannot be deleted if
            # there is a file for which we lack the permissions, so we change it
            # back when we are done.
            try:
                try:
                    with open(str(file_path), 'rb'):
                        file_readable = True
                except PermissionError:
                    file_readable = False
                if not file_readable:
                    config['file'] = str(file_path)
                    handler = self.get_request_handler(config)
                    self.call_handle(
                        handler, '/test', expect_status=HTTPStatus.FORBIDDEN)
                    # We repeat this test while using a template engine.
                    config['template'] = 'jinja'
                    handler = self.get_request_handler(config)
                    self.call_handle(
                        handler, '/test', expect_status=HTTPStatus.FORBIDDEN)
                    del config['template']
            finally:
                file_path.chmod(saved_mode)
            # Next, we test that the handler correctly detects when the file
            # option actually refers to a directory.
            config['file'] = str(temp_path)
            handler = self.get_request_handler(config)
            self.call_handle(
                handler, '/test', expect_status=HTTPStatus.NOT_FOUND)
            # And the same with a template engine.
            config['template'] = 'jinja'
            handler = self.get_request_handler(config)
            self.call_handle(
                handler, '/test', expect_status=HTTPStatus.NOT_FOUND)
            del config['template']
            # We also test that we cannot create a handler when
            # neither file nor root_dir are set or when both are set.
            config['root_dir'] = tmpdir
            with self.assertRaises(ValueError):
                handler = self.get_request_handler(config)
            del config['file']
            del config['root_dir']
            with self.assertRaises(KeyError):
                handler = self.get_request_handler(config)

    def test_config_data_source_error_action(self):
        """
        Test the ``data_source_error_action`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create a single file that can be served by the handler.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            # For this test, we are only interested in whether we get a system
            # id and data.
            _write_file(file_path, '{{ id is defined }}:{{ data is defined }}')
            config = {
                'file': str(file_path),
                'lookup_key': 'test_key',
                'request_path': '/test/...',
                'template': 'jinja'}
            # First, we create a mock data source that raises an exception for
            # the find_system method. When not using
            # lookup_key == ':system_id:', this method is always called first.
            data_source = unittest.mock.Mock(spec=DataSource)
            data_source.find_system.side_effect = RuntimeError(
                'find_system error')
            data_source.get_data.return_value = {}
            handler = self.get_request_handler(config, data_source)
            # The default option for data_source_error_action is "error", which
            # means that the exception should bubble up.
            with self.assertRaises(RuntimeError) as assertion:
                self.call_handle(handler, '/test/lookup_value')
            self.assertEqual('find_system error', assertion.exception.args[0])
            # Now we try the same again, but this time we set the "error" action
            # explicitly.
            config['data_source_error_action'] = 'error'
            handler = self.get_request_handler(config, data_source)
            with self.assertRaises(RuntimeError) as assertion:
                self.call_handle(handler, '/test/lookup_value')
            self.assertEqual('find_system error', assertion.exception.args[0])
            # Next, we test the 'ignore' action. In this case, the exception
            # should be ignored, and the handler should return "not found",
            # as lookup_no_result_action is "not_found" by default.
            config['data_source_error_action'] = 'ignore'
            handler = self.get_request_handler(config, data_source)
            with unittest.mock.patch(
                    'vinegar.request_handler.file.logger',
                    autospec=True) as mock_logger:
                self.call_handle(
                    handler,
                    '/test/lookup_value',
                    expect_status=HTTPStatus.NOT_FOUND)
                mock_logger.warning.assert_not_called()
            # Finally, we test the 'warn' action. In this case, the exception
            # should be ignored (but logged), and the handler should return "not
            # found", as lookup_no_result_action is "not_found" by default.
            config['data_source_error_action'] = 'warn'
            handler = self.get_request_handler(config, data_source)
            with unittest.mock.patch(
                    'vinegar.request_handler.file.logger',
                    autospec=True) as mock_logger:
                self.call_handle(
                    handler,
                    '/test/lookup_value',
                    expect_status=HTTPStatus.NOT_FOUND)
                # assert_called_once does not exist in Python 3.5, so we use a
                # workaround here.
                self.assertEqual(1, mock_logger.warning.call_count)
            # Now, we repeat these tests, but we have find_system return a
            # proper value and have get_data raise an exception instead.
            data_source.find_system.return_value = 'system'
            data_source.find_system.side_effect = None
            data_source.get_data.side_effect = RuntimeError('get_data error')
            # First, we again test with data_source_error_action at its default
            # value.
            del config['data_source_error_action']
            handler = self.get_request_handler(config, data_source)
            with self.assertRaises(RuntimeError) as assertion:
                self.call_handle(handler, '/test/lookup_value')
            self.assertEqual('get_data error', assertion.exception.args[0])
            # Next, we test a setting of "error", which should have the same
            # effects.
            config['data_source_error_action'] = 'error'
            handler = self.get_request_handler(config, data_source)
            with self.assertRaises(RuntimeError) as assertion:
                self.call_handle(handler, '/test/lookup_value')
            self.assertEqual('get_data error', assertion.exception.args[0])
            # Next, we test a setting of "ignore". This should have the effect
            # that the error is ignored and the template is rendered without the
            # system data. No warning should be logged.
            config['data_source_error_action'] = 'ignore'
            handler = self.get_request_handler(config, data_source)
            with unittest.mock.patch(
                    'vinegar.request_handler.file.logger',
                    autospec=True) as mock_logger:
                file_content = self.call_handle(
                    handler,
                    '/test/lookup_value',
                    expect_status=HTTPStatus.OK)
                self.assertEqual('True:False', file_content.decode())
                mock_logger.warning.assert_not_called()
            # Finally, we test the "warn" setting. This should have the same
            # effects as the "ignore" setting, but a warning should be logged.
            config['data_source_error_action'] = 'warn'
            handler = self.get_request_handler(config, data_source)
            with unittest.mock.patch(
                    'vinegar.request_handler.file.logger',
                    autospec=True) as mock_logger:
                file_content = self.call_handle(
                    handler,
                    '/test/lookup_value',
                    expect_status=HTTPStatus.OK)
                self.assertEqual('True:False', file_content.decode())
                # assert_called_once does not exist in Python 3.5, so we use a
                # workaround here.
                self.assertEqual(1, mock_logger.warning.call_count)
            # We also test that we cannot create a handler when
            # data_source_error_action is set to an invalid value.
            config['data_source_error_action'] = 'not_valid'
            with self.assertRaises(ValueError):
                handler = self.get_request_handler(config, data_source)

    def test_config_lookup_key(self):
        """
        Test the ``lookup_key`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create a single file that can be served by the handler.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            # At first, we are only interested in whether we get an ID or data
            # at all.
            _write_file(file_path, '{{ id is defined }}:{{ data is defined }}')
            config = {
                'file': str(file_path),
                'request_path': '/test/...',
                'template': 'jinja'}
            # If the lookup_key is not set, we expect no lookup to be run. We
            # verify this through two means: First, we make the data source
            # raise an exception and second we check the rendering result.
            data_source = unittest.mock.Mock(spec=DataSource)
            data_source.find_system.side_effect = AssertionError(
                'find_system should not have been called.')
            data_source.get_data.side_effect = AssertionError(
                'get_data should not have been called.')
            handler = self.get_request_handler(config, data_source)
            # As the lookup key is not set, the place holder should be used as a
            # verbatim part of the request path.
            file_content = self.call_handle(
                handler, '/test/...', expect_status=HTTPStatus.OK)
            self.assertEqual('False:False', file_content.decode())
            # When the lookup_key has the special value ":system_id:", the
            # data value specified in the request should directly be used as
            # the system ID and the find_system method should not be called.
            data_source.reset_mock()
            data_source.get_data.return_value = ({}, '')
            data_source.get_data.side_effect = None
            config['lookup_key'] = ':system_id:'
            handler = self.get_request_handler(config, data_source)
            file_content = self.call_handle(
                handler, '/test/test_id', expect_status=HTTPStatus.OK)
            self.assertEqual('True:True', file_content.decode())
            data_source.get_data.assert_called_once_with('test_id', {}, '')
            # Whe the lookup key is a regular key, the find_system value should
            # be called with that key and the value extracted from the path.
            # get_data should be called with the return value of find_system.
            # First we test the simpler case that find_system returns None. In
            # that case, the handler should return "not found".
            data_source.reset_mock()
            data_source.find_system.return_value = None
            data_source.find_system.side_effect = None
            config['lookup_key'] = 'test_key'
            handler = self.get_request_handler(config, data_source)
            file_content = self.call_handle(
                handler, '/test/test_value', expect_status=HTTPStatus.NOT_FOUND)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            data_source.get_data.assert_not_called()
            # Now we have find_system return a system ID and expect that
            # get_data is called with that ID.
            data_source.reset_mock()
            data_source.find_system.return_value = 'test_id'
            file_content = self.call_handle(
                handler, '/test/test_value', expect_status=HTTPStatus.OK)
            self.assertEqual('True:True', file_content.decode())
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            data_source.get_data.assert_called_once_with('test_id', {}, '')

    def test_config_lookup_no_result_action(self):
        """
        Test the ``lookup_no_result_action`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create a single file that can be served by the handler.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            # At first, we are only interested in whether we get an ID or data
            # at all.
            _write_file(file_path, '{{ id is defined }}:{{ data is defined }}')
            config = {
                'file': str(file_path),
                'lookup_key': 'test_key',
                'request_path': '/test/...',
                'template': 'jinja'}
            # We have find_system return None so that the lookup has no result.
            # We have get_data raise an exception because that method should
            # never be called if there is no lookup result.
            data_source = unittest.mock.Mock(spec=DataSource)
            data_source.find_system.return_value = None
            data_source.get_data.side_effect = AssertionError(
                'get_data should not have been called.')
            # By default, lookup_no_result_action is set to "not_found", so we
            # expect the handler to return a "not found" result.
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/test/test_value', expect_status=HTTPStatus.NOT_FOUND)
            # The same applies when we set lookup_no_result_action to
            # "not_found" explicitly.
            config['lookup_no_result_action'] = 'not_found'
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/test/test_value', expect_status=HTTPStatus.NOT_FOUND)
            # If the set the option to "continue", the template should be
            # rendered with no system ID and data.
            config['lookup_no_result_action'] = 'continue'
            handler = self.get_request_handler(config, data_source)
            file_content = self.call_handle(
                handler, '/test/test_value', expect_status=HTTPStatus.OK)
            self.assertEqual('False:False', file_content.decode())
            # Finally, we test that we cannot create a handler when
            # lookup_no_result_action is set to an invalid value.
            config['lookup_no_result_action'] = 'not_valid'
            with self.assertRaises(ValueError):
                handler = self.get_request_handler(config, data_source)

    def test_config_lookup_value_placeholder(self):
        """
        Test the ``lookup_value_placeholder`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create a single file that can be served by the handler.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            # We are not interested in the contents of the file because we only
            # want to test the extraction of lookup values.
            _write_file(file_path, '{{ id is defined }}:{{ data is defined }}')
            config = {
                'file': str(file_path),
                'lookup_key': 'test_key'}
            # We have find_system return None so that the lookup has no result.
            # We have get_data raise an exception because that method should
            # never be called if there is no lookup result.
            data_source = unittest.mock.Mock(spec=DataSource)
            data_source.find_system.return_value = None
            data_source.get_data.side_effect = AssertionError(
                'get_data should not have been called.')
            # By default, lookup_no_result_action is set to "not_found", so we
            # expect the handler to return a "not found" result.
            # The default placeholder is "...".
            config['request_path'] = '/test/...'
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/test/test_value', expect_status=HTTPStatus.NOT_FOUND)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            # If we change the placeholder, the request path should be
            # considered to contain a placeholder any longer. This is an error
            # if there is a lookup key.
            config['lookup_value_placeholder'] = '{}'
            with self.assertRaises(ValueError):
                self.get_request_handler(config, data_source)
            # If we use the new placeholder, everything should work again.
            config['request_path'] = '/test/{}'
            handler = self.get_request_handler(config, data_source)
            data_source.reset_mock()
            self.call_handle(
                handler, '/test/test_value', expect_status=HTTPStatus.NOT_FOUND)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')

    def test_config_lookup_value_transform(self):
        """
        Test the ``lookup_value_transform`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create a single file that can be served by the handler.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            # The content of the template file does not matter because it is not
            # going to be rendered.
            _write_file(file_path, '')
            config = {
                'file': str(file_path),
                'lookup_key': 'test_key',
                'request_path': '/test/...'}
            # We have find_system return None so that the lookup has no result.
            # We have get_data raise an exception because that method should
            # never be called if there is no lookup result.
            data_source = unittest.mock.Mock(spec=DataSource)
            data_source.find_system.return_value = None
            # By default, the lookup value should not be transformed.
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/test/abc', expect_status=HTTPStatus.NOT_FOUND)
            data_source.find_system.assert_called_once_with('test_key', 'abc')
            # Now we add a transformation configuration.
            data_source.reset_mock()
            config['lookup_value_transform'] = [
                'string.to_upper',
                {'string.add_prefix': 'test:'}]
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/test/abc', expect_status=HTTPStatus.NOT_FOUND)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test:ABC')

    def test_config_request_path(self):
        """
        Test the ``request_path`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create a directory structure, where we have one file in the
            # root directory and one file in a sub directory.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            _write_file(file_path, 'Test 123')
            sub_dir_path = temp_path / 'sub'
            sub_dir_path.mkdir()
            sub_file_path = sub_dir_path / 'sub.txt'
            _write_file(sub_file_path, 'ABC')
            config = {'root_dir': str(temp_path)}
            # If the request_path option is missing, we should not be able to
            # create the handler.
            with self.assertRaises(KeyError):
                self.get_request_handler(config)
            # First, we test a configuration where the request path is "/" and
            # there is no placeholder in the path.
            config['request_path'] = '/'
            handler = self.get_request_handler(config)
            self.call_handle(handler, '/test.txt', expect_status=HTTPStatus.OK)
            # Next, we test a configuration where we have prefix.
            config['request_path'] = '/test'
            handler = self.get_request_handler(config)
            self.call_handle(
                handler, '/test/test.txt', expect_status=HTTPStatus.OK)
            # In order to test place holders, we need a lookup key and a data
            # source. If we have no template engine, get_data is not used, so it
            # is sufficient to mock find_system.
            config['lookup_key'] = 'test_key'
            data_source = unittest.mock.Mock(spec=DataSource)
            data_source.find_system.return_value = 'system_id'
            data_source.get_data.side_effect = AssertionError(
                'get_data should not have been called.')
            # We test a placeholder directly at the root and no suffix.
            config['request_path'] = '/...'
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/test_value', expect_can_handle=False)
            self.call_handle(
                handler, '//test.txt', expect_can_handle=False)
            self.call_handle(
                handler, '/test_value/test.txt', expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/test_value/xyz.txt',
                expect_status=HTTPStatus.NOT_FOUND)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            # Next, we add a suffix.
            config['request_path'] = '/.../xyz'
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/test_value', expect_can_handle=False)
            self.call_handle(
                handler, '/test_value/test.txt', expect_can_handle=False)
            self.call_handle(
                handler, '//xyz/test.txt', expect_can_handle=False)
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/test_value/xyz/test.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/test_value/xyz/sub/sub.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            self.call_handle(
                handler,
                '/test_value/xyz/xyz.txt',
                expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler,
                '/test_value/xyz/test.txt/',
                expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler,
                '/test_value/test/xyz/xyz.txt',
                expect_can_handle=False)
            # Now we use a prefix.
            config['request_path'] = '/xyz/...'
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/test_value', expect_can_handle=False)
            self.call_handle(
                handler, '/test_value/test.txt', expect_can_handle=False)
            self.call_handle(
                handler, '//xyz/test.txt', expect_can_handle=False)
            self.call_handle(
                handler, '/xyz//test.txt', expect_can_handle=False)
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/xyz/test_value/test.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/xyz/test_value/sub/sub.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            self.call_handle(
                handler,
                '/xyz/test_value/xyz.txt',
                expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler,
                '/xyz/test_value/test.txt/',
                expect_status=HTTPStatus.NOT_FOUND)
            # We also test using both a prefix and a suffix.
            config['request_path'] = '/abc/.../xyz'
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/abc/test_value', expect_can_handle=False)
            self.call_handle(
                handler, '/test_value/xyz', expect_can_handle=False)
            self.call_handle(
                handler, '/abc/test_value/test.txt', expect_can_handle=False)
            self.call_handle(
                handler, '/test_value/xyz/test.txt', expect_can_handle=False)
            self.call_handle(
                handler,
                '/abc//xyz/test.txt',
                expect_can_handle=False)
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/abc/test_value/xyz/test.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/abc/test_value/xyz/sub/sub.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            self.call_handle(
                handler,
                '/abc/test_value/xyz/xyz.txt',
                expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler,
                '/abc/test_value/xyz/test.txt/',
                expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler,
                '/abc/test_value/test/xyz/xyz.txt',
                expect_can_handle=False)
            # Even the segment that contains the placeholder can have a prefix
            # and a suffix. We test the prefix first.
            config['request_path'] = '/abc...'
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/test_value', expect_can_handle=False)
            self.call_handle(
                handler, '/test_value/test.txt', expect_can_handle=False)
            self.call_handle(
                handler, '/abc/test.txt', expect_can_handle=False)
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/abctest_value/test.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/abctest_value/sub/sub.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            self.call_handle(
                handler,
                '/abctest_value/xyz.txt',
                expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler,
                '/abctest_value/test.txt/',
                expect_status=HTTPStatus.NOT_FOUND)
            # Next we test with a suffix.
            config['request_path'] = '/...xyz'
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/test_value', expect_can_handle=False)
            self.call_handle(
                handler, '/test_value/test.txt', expect_can_handle=False)
            self.call_handle(
                handler, '/xyz/test.txt', expect_can_handle=False)
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/test_valuexyz/test.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/test_valuexyz/sub/sub.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            self.call_handle(
                handler,
                '/test_valuexyz/xyz.txt',
                expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler,
                '/test_valuexyz/test.txt/',
                expect_status=HTTPStatus.NOT_FOUND)
            # We also test with both a prefix and a suffix.
            config['request_path'] = '/abc...xyz'
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/test_value', expect_can_handle=False)
            self.call_handle(
                handler, '/test_value/test.txt', expect_can_handle=False)
            self.call_handle(
                handler, '/abcxyz/test.txt', expect_can_handle=False)
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/abctest_valuexyz/test.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/abctest_valuexyz/sub/sub.txt',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            self.call_handle(
                handler,
                '/abctest_valuexyz/xyz.txt',
                expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler,
                '/abctest_valuexyz/test.txt/',
                expect_status=HTTPStatus.NOT_FOUND)
            # Things work a bit different when operating in file mode, so we
            # want to run some tests for that mode as well.
            del config['root_dir']
            config['file'] = str(file_path)
            # Even for TFTP, we allow attaching directly to the root in file
            # mode when we expect a lookup value.
            config['request_path'] = '/...'
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/', expect_can_handle=False)
            self.call_handle(
                handler, '/test_value/', expect_can_handle=False)
            self.call_handle(
                handler, '/test_value/abc', expect_can_handle=False)
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/test_value',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            # We also try a more complex request path.
            config['request_path'] = '/abc/123...456/xyz'
            handler = self.get_request_handler(config, data_source)
            self.call_handle(
                handler, '/abc', expect_can_handle=False)
            self.call_handle(
                handler, '/abc/123456/xyz', expect_can_handle=False)
            self.call_handle(
                handler, '/abc/123test_value456/xyz/', expect_can_handle=False)
            self.call_handle(
                handler,
                '/abc/123test_value456/xyz/test',
                expect_can_handle=False)
            data_source.reset_mock()
            self.call_handle(
                handler,
                '/abc/123test_value456/xyz',
                expect_status=HTTPStatus.OK)
            data_source.find_system.assert_called_once_with(
                'test_key', 'test_value')
            # A request path that ends with "/" and is not the special path "/"
            # should result in an error.
            config['request_path'] = '/test/'
            with self.assertRaises(ValueError):
                self.get_request_handler(config)
            # A request path that does not start with a "/" should be rejected
            # as well
            config['request_path'] = 'test'
            with self.assertRaises(ValueError):
                self.get_request_handler(config)

    def test_config_root_dir(self):
        """
        Test the ``root_dir`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create a directory structure, where we have one file in the
            # root directory and one file in a sub directory.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            _write_file(file_path, 'Test 123')
            sub_dir_path = temp_path / 'sub'
            sub_dir_path.mkdir()
            sub_file_path = sub_dir_path / 'sub.txt'
            _write_file(sub_file_path, 'ABC')
            # First, we test the handler when it is attached at the webroot.
            config = {'request_path': '/', 'root_dir': str(temp_path)}
            handler = self.get_request_handler(config)
            file_content = self.call_handle(handler, '/test.txt')
            self.assertEqual('Test 123', file_content.decode())
            file_content = self.call_handle(handler, '/sub/sub.txt')
            self.assertEqual('ABC', file_content.decode())
            self.call_handle(
                handler,
                '/no-such-file.txt',
                expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler, '/sub', expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler, '/sub/', expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler, '/sub/sub.txt/', expect_status=HTTPStatus.NOT_FOUND)
            # Now, we test the handler when it is attached to a path below the
            # root.
            config['request_path'] = '/test'
            handler = self.get_request_handler(config)
            file_content = self.call_handle(handler, '/test/test.txt')
            self.assertEqual('Test 123', file_content.decode())
            file_content = self.call_handle(handler, '/test/sub/sub.txt')
            self.assertEqual('ABC', file_content.decode())
            self.call_handle(
                handler,
                '/test/no-such-file.txt',
                expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler, '/test/sub', expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler, '/test/sub/', expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler,
                '/test/sub/sub.txt/',
                expect_status=HTTPStatus.NOT_FOUND)

    def test_config_template(self):
        """
        Test the ``template`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create a single file that can be served by the handler.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            # We want to see that the system ID and the system data are
            # available to the template.
            _write_file(
                file_path, '{{ id }}:{{ data.get("nested:key:value") }}')
            # We set lookup_key to ":system_id:" so that we do not have to mock
            # find_system.
            config = {
                'file': str(file_path),
                'lookup_key': ':system_id:',
                'request_path': '/test/...'}
            data_source = unittest.mock.Mock(spec=DataSource)
            data_source.find_system.side_effect = AssertionError(
                'find_system should not have been called.')
            # We use a nested value so that we can verify that the data object
            # in the context is actually a smart lookup dict.
            data_source.get_data.return_value = (
                {'nested': {'key': {'value': 'abc'}}},
                '')
            handler = self.get_request_handler(config, data_source)
            # By default, no template engine is configured, so the file content
            # should be returned verbatim.
            file_content = self.call_handle(
                handler, '/test/test_id', expect_status=HTTPStatus.OK)
            self.assertEqual(
                '{{ id }}:{{ data.get("nested:key:value") }}',
                file_content.decode())
            # If we use the template engine, the template should be rendered
            # with the data.
            config['template'] = 'jinja'
            handler = self.get_request_handler(config, data_source)
            file_content = self.call_handle(
                handler, '/test/test_id', expect_status=HTTPStatus.OK)
            self.assertEqual('test_id:abc', file_content.decode())

    def test_config_template_config(self):
        """
        Test the ``template_config`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create a single file that can be served by the handler.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            # The easiest thing that we can test is that replacing the variable
            # start and end strings (default '{{' and '}}') has the expected
            # effect.
            _write_file(file_path, '{! id !}')
            # We set lookup_key to ":system_id:" so that we do not have to mock
            # find_system.
            config = {
                'file': str(file_path),
                'lookup_key': ':system_id:',
                'request_path': '/test/...',
                'template': 'jinja'}
            data_source = unittest.mock.Mock(spec=DataSource)
            data_source.find_system.side_effect = AssertionError(
                'find_system should not have been called.')
            data_source.get_data.return_value = ({'test': 'abc'}, '')
            handler = self.get_request_handler(config, data_source)
            # By default, Jinja should not recognize "{!" and "!}", so the
            # template content should be returned verbatim.
            file_content = self.call_handle(
                handler, '/test/test_id', expect_status=HTTPStatus.OK)
            self.assertEqual('{! id !}', file_content.decode())
            # If we replace variable_start_string and variable_end_string, the
            # ID should be rendered.
            config['template_config'] = {
                'env': {
                    'variable_start_string': '{!',
                    'variable_end_string': '!}'}}
            handler = self.get_request_handler(config, data_source)
            file_content = self.call_handle(
                handler, '/test/test_id', expect_status=HTTPStatus.OK)
            self.assertEqual('test_id', file_content.decode())

    def test_path_security(self):
        """
        Test that that the request handler is not vulnerable to path
        manipulation attacks. This includes path traversal attacks.

        Specifically, this test checks for vulnerabilities of the following
        kinds:

        * encoding and double encoding
        * null-byte injection
        * Unicode-based attacks
        """
        with TemporaryDirectory() as tmpdir:
            # We create a directory structure, where we have one file above the
            # root directory configured for the handler, one file in that
            # directory, and one file in a sub directory.
            temp_path = pathlib.Path(tmpdir)
            root_path = temp_path / 'root'
            root_path.mkdir()
            sub_path = root_path / 'sub'
            sub_path.mkdir()
            parent_file_path = temp_path / 'parent.txt'
            root_file_path = root_path / 'root.txt'
            sub_file_path = sub_path / 'sub.txt'
            _write_file(parent_file_path, 'parent')
            _write_file(root_file_path, 'root')
            _write_file(sub_file_path, 'sub')
            # First, we test the handler when it is attached at the webroot.
            config = {'request_path': '/', 'root_dir': str(root_path)}
            handler = self.get_request_handler(config)
            self._test_path_security_run_checks(handler, '')
            # Second, we test the handler when it is using a prefix.
            config = {
                'request_path': '/prefix', 'root_dir': str(root_path)}
            handler = self.get_request_handler(config)
            self._test_path_security_run_checks(handler, '/prefix')

    def _test_path_security_run_checks(self, handler, prefix):
        """
        Helper method for `test_path_security`.

        This method implements the parts of the test that are run again for
        different prefixes in the request path.
        """
        # As a very basic test, we check that we can read the two files that
        # should be exposed.
        file_content = self.call_handle(
            handler, prefix + '/root.txt', expect_status=HTTPStatus.OK)
        self.assertEqual('root', file_content.decode())
        file_content = self.call_handle(
            handler, prefix + '/sub/sub.txt', expect_status=HTTPStatus.OK)
        self.assertEqual('sub', file_content.decode())
        # Now we try accessing the file root.txt, but with a layer of
        # indirection. This should not work.
        self.call_handle(
            handler,
            prefix + '/sub/../root.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler, prefix + '/./root.txt', expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/../root/root.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        # It should not work for parent.txt either.
        self.call_handle(
            handler,
            prefix + '/../parent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        # A path that contains a null byte, should not be resolved.
        self.call_handle(
            handler, prefix + '/root.txt\0', expect_can_handle=False)
        # Now we try things again, but with encoded characters.
        self.call_handle(
            handler,
            prefix + '/sub/%2e%2e/root.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub%2f..%2froot.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub%2f%2e%2e%2froot.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/%2e%2e/parent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '%2f..%2fparent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '%2f%2e%2e%2fparent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/root.txt%00',
            expect_can_handle=False)
        # Next, we try double-encoded characters.
        self.call_handle(
            handler,
            prefix + '/sub%252fsub.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub/%252e%252e/root.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub%252f..%252froot.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub%252f%252e%252e%252froot.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/%252e%252e/parent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/..%252fparent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/%252e%252e%252fparent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/root.txt%2500',
            expect_status=HTTPStatus.NOT_FOUND)
        # Try things again with backslashes instead of forward slashes. On
        # UNIX-like platforms, this should not make a difference, but it could
        # on Windows.
        self.call_handle(
            handler,
            prefix + '/sub\\..\\root.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/.\\root.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/..\\root\\root.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/..\\parent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub\\%2e%2e\\root.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub%5c..%5croot.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub%5c%2e%2e%5croot.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/%2e%2e\\parent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/..%5cparent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '%2f%2e%2e%5cparent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub/%252e%252e/root.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub%255c..%255croot.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub%255c%252e%252e%255croot.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/%252e%252e/parent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/..%255cparent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/%252e%252e%255cparent.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        # We also want to try some unicode characters.
        self.call_handle(
            handler,
            prefix + '/sub%u2216sub.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub%c0%afsub.txt',
            expect_status=HTTPStatus.NOT_FOUND)
        self.call_handle(
            handler,
            prefix + '/sub%c1%9csub.txt',
            expect_status=HTTPStatus.NOT_FOUND)


class TestHttpFileRequestHandler(TestFileRequestHandlerBase):
    """
    Tests for the `HttpFileRequestHandler`.
    """

    def call_handle(
            self,
            handler,
            filename,
            expect_can_handle=True,
            expect_status=None,
            expect_headers=None,
            method='GET'):
        context = handler.prepare_context(filename)
        can_handle = handler.can_handle(filename, context)
        self.assertEqual(expect_can_handle, can_handle)
        if can_handle:
            status, headers, file = handler.handle(
                filename, method, None, None, None, context)
            try:
                if expect_status is not None:
                    self.assertEqual(expect_status, status)
                if expect_status == HTTPStatus.OK and method != 'HEAD':
                    self.assertIsNotNone(file)
                if expect_status == HTTPStatus.NOT_FOUND:
                    self.assertIsNone(file)
                if expect_headers is not None:
                    self.assertEqual(expect_headers, headers)
                if file is None:
                    return None
                else:
                    file_content = io.BytesIO()
                    shutil.copyfileobj(file, file_content)
                return file_content.getvalue()
            finally:
                if file is not None:
                    file.close()

    def get_request_handler(self, config, data_source=None):
        handler = get_instance_http(config)
        if data_source is not None:
            handler.set_data_source(data_source)
        return handler

    def test_config_content_type(self):
        """
        Test the ``content_type`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create a single file only. This is sufficient for this test.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            _write_file(file_path, 'Test 123')
            # We disable content-type guessing, because that might interfere
            # with this test.
            config = {
                'request_path': '/test',
                'file': str(file_path)}
            handler = self.get_request_handler(config)
            # If the content type is not set explicitly, we expect a content
            # type of "application/octet-stream" when not using a template
            # engine.
            self.call_handle(
                handler,
                '/test',
                expect_headers={'Content-Type': 'application/octet-stream'},
                expect_status=HTTPStatus.OK)
            # When using a template engine, the default content type is
            # "text/plain; charset=UTF-8".
            config['template'] = 'jinja'
            handler = self.get_request_handler(config)
            self.call_handle(
                handler,
                '/test',
                expect_headers={'Content-Type': 'text/plain; charset=UTF-8'},
                expect_status=HTTPStatus.OK)
            # When explicitly setting a content type, that type should be used
            # regardless of whether we use a template engine or not.
            config['content_type'] = 'text/html; charset=UTF-8'
            handler = self.get_request_handler(config)
            self.call_handle(
                handler,
                '/test',
                expect_headers={'Content-Type': 'text/html; charset=UTF-8'},
                expect_status=HTTPStatus.OK)
            del config['template']
            handler = self.get_request_handler(config)
            self.call_handle(
                handler,
                '/test',
                expect_headers={'Content-Type': 'text/html; charset=UTF-8'},
                expect_status=HTTPStatus.OK)

    def test_config_content_type_map(self):
        """
        Test the ``content_type_map`` configuration option.
        """
        with TemporaryDirectory() as tmpdir:
            # We create three different files with different extensions. We need
            # this to test the different content types.
            temp_path = pathlib.Path(tmpdir)
            text_path = temp_path / 'test.txt'
            _write_file(text_path, 'Test 123')
            bin_path = temp_path / 'test.bin'
            _write_file(bin_path, 'Test 123')
            html_path = temp_path / 'test.html'
            _write_file(html_path, 'Test 123')
            special_path = temp_path / 'special_file'
            _write_file(special_path, 'Test 123')
            config = {
                'request_path': '/test',
                'root_dir': str(temp_path)}
            handler = self.get_request_handler(config)
            # If the content_type_map option is not set, everything should
            # default to the content_type option, which is
            # "application/octet-stream" by default if no template engine is
            # used.
            self.call_handle(
                handler,
                '/test/test.txt',
                expect_headers={'Content-Type': 'application/octet-stream'},
                expect_status=HTTPStatus.OK)
            self.call_handle(
                handler,
                '/test/test.bin',
                expect_headers={'Content-Type': 'application/octet-stream'},
                expect_status=HTTPStatus.OK)
            self.call_handle(
                handler,
                '/test/test.html',
                expect_headers={'Content-Type': 'application/octet-stream'},
                expect_status=HTTPStatus.OK)
            self.call_handle(
                handler,
                '/test/special_file',
                expect_headers={'Content-Type': 'application/octet-stream'},
                expect_status=HTTPStatus.OK)
            # If we use a content_type_map, the value of content_type should
            # only be used for files that do not match any of the patterns in
            # the map.
            config['content_type_map'] = {
                '.txt': 'text/plain; charset=UTF-8',
                '.html': 'text/html; charset=UTF-8',
                'special_file': 'application/x-super-special'}
            handler = self.get_request_handler(config)
            self.call_handle(
                handler,
                '/test/test.txt',
                expect_headers={'Content-Type': 'text/plain; charset=UTF-8'},
                expect_status=HTTPStatus.OK)
            self.call_handle(
                handler,
                '/test/test.bin',
                expect_headers={'Content-Type': 'application/octet-stream'},
                expect_status=HTTPStatus.OK)
            self.call_handle(
                handler,
                '/test/test.html',
                expect_headers={'Content-Type': 'text/html; charset=UTF-8'},
                expect_status=HTTPStatus.OK)
            self.call_handle(
                handler,
                '/test/special_file',
                expect_headers={'Content-Type': 'application/x-super-special'},
                expect_status=HTTPStatus.OK)
            # We should get an exception when we try to set
            # the content_type_map while operating in file mode.
            del config['root_dir']
            config['file'] = str(text_path)
            with self.assertRaises(ValueError):
                self.get_request_handler(config)

    def test_config_file(self):
        """
        Test the ``file`` configuration option.
        """
        # First, we run the tests from the base class, then we run the tests
        # that are specific to TFTP
        super().test_config_file()
        with TemporaryDirectory() as tmpdir:
            # We only create a single file. This is sufficent for this test.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            _write_file(file_path, 'Test 123')
            # We test the handler when it is attached at the webroot. This test
            # is specific to the HTTP version because such a setup is not
            # allowed for TFTP.
            config = {'request_path': '/', 'file': str(file_path)}
            handler = self.get_request_handler(config)
            file_content = self.call_handle(
                handler, '/', expect_status=HTTPStatus.OK)
            self.assertEqual('Test 123', file_content.decode())
            self.call_handle(handler, '/test', expect_can_handle=False)

    def test_head_request(self):
        """
        Test that a HEAD request is handled correctly.
        """
        with TemporaryDirectory() as tmpdir:
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            _write_file(file_path, 'Test 123')
            config = {'request_path': '/test', 'file': str(file_path)}
            handler = self.get_request_handler(config)
            file_content = self.call_handle(
                handler, '/test', expect_status=HTTPStatus.OK, method='HEAD')
            self.assertIsNone(file_content)


class TestTftpFileRequestHandler(TestFileRequestHandlerBase):
    """
    Tests for the `TftpFileRequestHandler`.
    """

    def call_handle(
            self,
            handler,
            filename,
            expect_can_handle=True,
            expect_status=None,
            expect_headers=None,
            method=None):
        context = handler.prepare_context(filename)
        can_handle = handler.can_handle(filename, context)
        self.assertEqual(expect_can_handle, can_handle)
        if can_handle:
            ok = True
            forbidden = False
            not_found = False
            try:
                file = handler.handle(filename, None, context)
            except TftpError as e:
                file = None
                ok = False
                if e.error_code == TftpErrorCode.FILE_NOT_FOUND:
                    not_found = True
                elif e.error_code == TftpErrorCode.ACCESS_VIOLATION:
                    forbidden = True
            try:
                if expect_status == HTTPStatus.OK:
                    self.assertTrue(ok)
                    self.assertIsNotNone(file)
                if expect_status == HTTPStatus.FORBIDDEN:
                    self.assertTrue(forbidden)
                if expect_status == HTTPStatus.NOT_FOUND:
                    self.assertTrue(not_found)
                if file is None:
                    return None
                else:
                    file_content = io.BytesIO()
                    shutil.copyfileobj(file, file_content)
                    return file_content.getvalue()
            finally:
                if file is not None:
                    file.close()

    def get_request_handler(self, config, data_source=None):
        handler = get_instance_tftp(config)
        if data_source is not None:
            handler.set_data_source(data_source)
        return handler

    def test_config_file(self):
        """
        Test the ``file`` configuration option.
        """
        # First, we run the tests from the base class, then we run the tests
        # that are specific to TFTP
        super().test_config_file()
        with TemporaryDirectory() as tmpdir:
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            _write_file(file_path, 'Test 123')
            # First, we test the handler when it is attached at the webroot.
            config = {'request_path': '/', 'file': str(file_path)}
            # In TFTP mode, attaching a request handler directly to the root is
            # not allowed when operating in file mode.
            with self.assertRaises(ValueError):
                handler = self.get_request_handler(config)
            # Now, we test the handler when it is attached to a path below the
            # root.
            config['request_path'] = '/test'
            handler = self.get_request_handler(config)
            file_content = self.call_handle(handler, 'test')
            self.assertEqual('Test 123', file_content.decode())
            self.call_handle(handler, 'test/', expect_can_handle=False)
            self.call_handle(handler, 'test/abc', expect_can_handle=False)

    def test_config_root_dir(self):
        """
        Test the ``root_dir`` configuration option.
        """
        # First, we run the tests from the base class, then we run the tests
        # that are specific to TFTP
        super().test_config_root_dir()
        with TemporaryDirectory() as tmpdir:
            # We create a directory structure, where we have one file in the
            # root directory and one file in a sub directory.
            temp_path = pathlib.Path(tmpdir)
            file_path = temp_path / 'test.txt'
            _write_file(file_path, 'Test 123')
            sub_dir_path = temp_path / 'sub'
            sub_dir_path.mkdir()
            sub_file_path = sub_dir_path / 'sub.txt'
            _write_file(sub_file_path, 'ABC')
            # First, we test the handler when it is attached at the webroot.
            config = {'request_path': '/', 'root_dir': str(temp_path)}
            handler = self.get_request_handler(config)
            file_content = self.call_handle(handler, 'test.txt')
            self.assertEqual('Test 123', file_content.decode())
            file_content = self.call_handle(handler, 'sub/sub.txt')
            self.assertEqual('ABC', file_content.decode())
            self.call_handle(
                handler, 'no-such-file.txt', expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler, 'sub', expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler, 'sub/', expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler, 'sub/sub.txt/', expect_status=HTTPStatus.NOT_FOUND)
            # Now, we test the handler when it is attached to a path below the
            # root.
            config['request_path'] = '/test'
            handler = self.get_request_handler(config)
            file_content = self.call_handle(handler, 'test/test.txt')
            self.assertEqual('Test 123', file_content.decode())
            file_content = self.call_handle(handler, 'test/sub/sub.txt')
            self.assertEqual('ABC', file_content.decode())
            self.call_handle(
                handler,
                'test/no-such-file.txt',
                expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler, 'test/sub', expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler, 'test/sub/', expect_status=HTTPStatus.NOT_FOUND)
            self.call_handle(
                handler,
                'test/sub/sub.txt/',
                expect_status=HTTPStatus.NOT_FOUND)


# We delete the base class from the module so that it is not automatically run
# (which would fail, because it is abstract).
del TestFileRequestHandlerBase


def _write_file(path, text):
    """
    Write text to a file, cleaning the text with `inspect.cleandoc` first.

    We use this to generate configuration files for tests.
    """
    if isinstance(path, pathlib.PurePath):
        path = str(path)
    with open(path, mode='w') as file:
        file.write(inspect.cleandoc(text))
