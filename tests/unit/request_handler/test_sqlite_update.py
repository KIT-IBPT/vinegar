"""
Tests for `vinegar.request_handler.sqlite_update`.
"""

import contextlib
import io
import json
import os.path
import shutil
import unittest

from http import HTTPStatus
from http.client import HTTPMessage
from tempfile import TemporaryDirectory

from vinegar.data_source import DataSource
from vinegar.request_handler.sqlite_update import (
    HttpSQLiteUpdateRequestHandler,
    get_instance_http,
)
from vinegar.utils.sqlite_store import open_data_store


class TestHttpSQLiteRequestHandler(unittest.TestCase):
    """
    Tests for the `TestHttpSQLiteRequestHandler`.
    """

    def test_config_action(self):
        """
        Test the ``action`` configuration option.
        """
        # We do not set the db_file option because it is set by
        # _data_store_and_handler.
        config = {"request_path": "/test"}
        # First, we check that we get an exception if the action option is not
        # set.
        with self.assertRaises(KeyError):
            with self._data_store_and_handler(config):
                pass
        # Next, we check that an invalid action results in an exception.
        config["action"] = "not_supported"
        with self.assertRaises(ValueError):
            with self._data_store_and_handler(config):
                pass
        # Test the delete_data action.
        config["action"] = "delete_data"
        with self._data_store_and_handler(config) as (data_store, handler):
            system_id = "system"
            data_store.set_value(system_id, "key1", "value1")
            data_store.set_value(system_id, "key2", "value2")
            self.assertEqual(
                {"key1": "value1", "key2": "value2"},
                data_store.get_data(system_id),
            )
            self._call_handle(
                handler, "/test/" + system_id, expect_status=HTTPStatus.OK
            )
            self.assertEqual({}, data_store.get_data(system_id))
        # Test the delete_value action.
        config["action"] = "delete_value"
        config["key"] = "key1"
        with self._data_store_and_handler(config) as (data_store, handler):
            system_id = "system"
            data_store.set_value(system_id, "key1", "value1")
            data_store.set_value(system_id, "key2", "value2")
            self.assertEqual(
                {"key1": "value1", "key2": "value2"},
                data_store.get_data(system_id),
            )
            self._call_handle(
                handler, "/test/" + system_id, expect_status=HTTPStatus.OK
            )
            self.assertEqual(
                {"key2": "value2"}, data_store.get_data(system_id)
            )
        # Test the set_value action.
        config["action"] = "set_value"
        config["key"] = "key1"
        config["value"] = "some value"
        with self._data_store_and_handler(config) as (data_store, handler):
            system_id = "system"
            self.assertEqual({}, data_store.get_data(system_id))
            self._call_handle(
                handler, "/test/" + system_id, expect_status=HTTPStatus.OK
            )
            self.assertEqual(
                {"key1": "some value"}, data_store.get_data(system_id)
            )
        # Test the set_json_value_from_request_body action.
        config["action"] = "set_json_value_from_request_body"
        config["key"] = "key1"
        with self._data_store_and_handler(config) as (data_store, handler):
            system_id = "system"
            value = {"abc": 123}
            body = json.dumps(value).encode()
            self.assertEqual({}, data_store.get_data(system_id))
            self._call_handle(
                handler,
                "/test/" + system_id,
                expect_status=HTTPStatus.OK,
                headers={"Content-Length": str(len(body))},
                body=io.BytesIO(body),
            )
            self.assertEqual({"key1": value}, data_store.get_data(system_id))
        # Test the set_text_value_from_request_body action.
        config["action"] = "set_text_value_from_request_body"
        config["key"] = "key1"
        with self._data_store_and_handler(config) as (data_store, handler):
            system_id = "system"
            value = "{abc"
            body = value.encode()
            self.assertEqual({}, data_store.get_data(system_id))
            self._call_handle(
                handler,
                "/test/" + system_id,
                expect_status=HTTPStatus.OK,
                headers={"Content-Length": str(len(body))},
                body=io.BytesIO(body),
            )
            self.assertEqual({"key1": value}, data_store.get_data(system_id))

    def test_config_db_file(self):
        """
        Test the ``db_file`` configuration option.

        As this option is used in most of the other tests, this test only
        ensures that an exception is raised if this option is missing.
        """
        config = {"action": "delete_data", "request_path": "/test"}
        with self.assertRaises(KeyError):
            get_instance_http(config)

    def test_config_client_address_key(self):
        """
        Test the ``client_address_key`` configuration option.
        """
        # We do not set the db_file option because it is set by
        # _data_store_and_handler. We use the delete_data action for our tests.
        config = {"action": "delete_data", "request_path": "/test"}
        # We do not test that the client address is not checked when
        # the client_address option is not set. This case is already covered by
        # other tests.
        config["client_address_key"] = "net:ip_addr"
        # We need a mock data source. That data souce only has to implement
        # get_data, because find_system is not used by the handler.
        system_data = {}
        data_source = unittest.mock.Mock()
        data_source.find_system.side_effect = AssertionError(
            "find_system should not have been called."
        )
        data_source.get_data.return_value = (system_data, "")
        with self._data_store_and_handler(config, data_source) as (
            data_store,
            handler,
        ):
            system_id = "system"
            data_store.set_value(system_id, "key1", "value1")
            self.assertEqual(
                {"key1": "value1"}, data_store.get_data(system_id)
            )
            # The system data returned by get_data does not contain a client
            # address, so we expect the request to be rejected.
            self._call_handle(
                handler,
                "/test/" + system_id,
                expect_status=HTTPStatus.FORBIDDEN,
            )
            # We expect that get_data has been called with the specified system
            # ID.
            data_source.get_data.assert_called_once_with(system_id, {}, "")
            self.assertEqual(
                {"key1": "value1"}, data_store.get_data(system_id)
            )
            # We set the client address, but not to an address that matches
            # (_call_handle uses an address of 127.0.0.1 by default).
            system_data["net"] = {"ip_addr": "192.168.0.1"}
            self._call_handle(
                handler,
                "/test/" + system_id,
                expect_status=HTTPStatus.FORBIDDEN,
            )
            self.assertEqual(
                {"key1": "value1"}, data_store.get_data(system_id)
            )
            # If we make a request with a client address of 192.168.0.1, there
            # should be a match. We use an IPv4 address that is encoded inside
            # an IPv6 address to test that such an address is decoded
            # correctly.
            self._call_handle(
                handler,
                "/test/" + system_id,
                expect_status=HTTPStatus.OK,
                client_address=("::ffff:192.168.0.1", 12345),
            )
            self.assertEqual({}, data_store.get_data(system_id))
            # Now we repeat the test, but this time we have a list of allowed
            # addresses.
            data_store.set_value(system_id, "key1", "value1")
            self.assertEqual(
                {"key1": "value1"}, data_store.get_data(system_id)
            )
            system_data["net"]["ip_addr"] = ["192.168.0.1", "192.168.0.2"]
            self._call_handle(
                handler,
                "/test/" + system_id,
                expect_status=HTTPStatus.FORBIDDEN,
                client_address=("192.168.0.3", 12345),
            )
            self.assertEqual(
                {"key1": "value1"}, data_store.get_data(system_id)
            )
            self._call_handle(
                handler,
                "/test/" + system_id,
                expect_status=HTTPStatus.OK,
                client_address=("192.168.0.2", 12345),
            )
            self.assertEqual({}, data_store.get_data(system_id))
            # It should also work with a set of allowed addresses and IPv6
            # addresses.
            data_store.set_value(system_id, "key1", "value1")
            self.assertEqual(
                {"key1": "value1"}, data_store.get_data(system_id)
            )
            system_data["net"]["ip_addr"] = {"127.0.0.1", "::1"}
            self._call_handle(
                handler,
                "/test/" + system_id,
                expect_status=HTTPStatus.FORBIDDEN,
                client_address=("192.168.0.3", 12345),
            )
            self.assertEqual(
                {"key1": "value1"}, data_store.get_data(system_id)
            )
            self._call_handle(
                handler,
                "/test/" + system_id,
                expect_status=HTTPStatus.OK,
                client_address=("::1", 12345),
            )
            self.assertEqual({}, data_store.get_data(system_id))

    def test_config_key(self):
        """
        Test the ``db_file`` configuration option.

        As this option is used in `test_config_action`, this test only ensures
        that an exception is raised if this option is missing.
        """
        # We do not set the db_file option because it is set by
        # _data_store_and_handler.
        config = {"request_path": "/test"}
        # Test the delete_value action.
        config["action"] = "delete_value"
        with self.assertRaises(KeyError):
            with self._data_store_and_handler(config):
                pass
        # Test the set_value action.
        config["action"] = "set_value"
        config["value"] = "test"
        with self.assertRaises(KeyError):
            with self._data_store_and_handler(config):
                pass

    def test_config_request_path(self):
        """
        Test the ``request_path`` configuration option.
        """
        # We use the delete_data action for testing the request_path. We do not
        # set the db_file option because it is set by _data_store_and_handler.
        config = {"action": "delete_data"}
        # The request_path option is mandatory, so we expect an error if it is
        # not set.
        with self.assertRaises(KeyError):
            with self._data_store_and_handler(config):
                pass
        # A request path must start with a "/". If it does not, this is an
        # error.
        config["request_path"] = "test"
        with self.assertRaises(ValueError):
            with self._data_store_and_handler(config):
                pass
        # Test a request path of "/".
        config["request_path"] = "/"
        with self._data_store_and_handler(config) as (data_store, handler):
            data_store.set_value("system", "key", "value")
            self._call_handle(
                handler, "/other_system", expect_status=HTTPStatus.OK
            )
            self._call_handle(
                handler, "/other/system", expect_status=HTTPStatus.OK
            )
            self.assertEqual({"key": "value"}, data_store.get_data("system"))
            self._call_handle(handler, "/system", expect_status=HTTPStatus.OK)
            self.assertEqual({}, data_store.get_data("system"))
        # Test a request path of "/my/prefix".
        config["request_path"] = "/my/prefix"
        with self._data_store_and_handler(config) as (data_store, handler):
            data_store.set_value("system", "key", "value")
            self._call_handle(
                handler, "/my/prefix/other_system", expect_status=HTTPStatus.OK
            )
            self._call_handle(
                handler, "/my/prefix/other/system", expect_status=HTTPStatus.OK
            )
            self._call_handle(handler, "/my/system", expect_can_handle=False)
            self._call_handle(handler, "/system", expect_can_handle=False)
            self.assertEqual({"key": "value"}, data_store.get_data("system"))
            self._call_handle(
                handler, "/my/prefix/system", expect_status=HTTPStatus.OK
            )
            self.assertEqual({}, data_store.get_data("system"))

    def test_config_value(self):
        """
        Test the ``db_file`` configuration option.

        As this option is used in `test_config_action`, this test only ensures
        that an exception is raised if this option is missing.
        """
        # We do not set the db_file option because it is set by
        # _data_store_and_handler.
        config = {"request_path": "/test"}
        # Test the set_value action.
        config["action"] = "set_value"
        config["key"] = "test"
        with self.assertRaises(KeyError):
            with self._data_store_and_handler(config):
                pass

    def test_get_request(self):
        """
        Test that ``GET`` requests are rejected.
        """
        # We use the delete_data action for this test. We do not set the
        # db_file option because it is set by _data_store_and_handler.
        config = {"action": "delete_data", "request_path": "/test"}
        with self._data_store_and_handler(config) as (data_store, handler):
            data_store.set_value("system", "key", "value")
            self._call_handle(
                handler,
                "/test/system",
                expect_status=HTTPStatus.METHOD_NOT_ALLOWED,
                method="GET",
            )
            self.assertEqual({"key": "value"}, data_store.get_data("system"))

    def _call_handle(
        self,
        handler,
        filename,
        expect_can_handle=True,
        expect_status=None,
        expect_headers=None,
        client_address=("127.0.0.1", 12345),
        method="POST",
        headers=None,
        body=None,
    ):
        """
        Helper method that we use to call ``prepare_context``, ``can_handle``
        and ``handle`` in succession.
        """
        if headers is None:
            headers = {}
        if body is None:
            body = io.BytesIO(b"")
        context = handler.prepare_context(filename)
        can_handle = handler.can_handle(filename, context)
        self.assertEqual(expect_can_handle, can_handle)
        if can_handle:
            status, headers, file = handler.handle(
                filename, method, headers, body, client_address, context
            )
            try:
                if expect_status is not None:
                    self.assertEqual(expect_status, status)
                if expect_status == HTTPStatus.OK:
                    self.assertIsNotNone(file)
                if expect_status == HTTPStatus.NOT_FOUND:
                    self.assertIsNone(file)
                if expect_headers is not None:
                    self.assertEqual(expect_headers, headers)
                elif expect_status == HTTPStatus.OK:
                    self.assertEqual(
                        {"Content-Type": "text/plain; charset=UTF-8"}, headers
                    )
                if file is None:
                    return None
                file_content = io.BytesIO()
                shutil.copyfileobj(file, file_content)
                file_content = file_content.getvalue()
                if expect_status == HTTPStatus.OK:
                    self.assertEqual(b"success\n", file_content)
                return file_content
            finally:
                if file is not None:
                    file.close()

    @contextlib.contextmanager
    def _data_store_and_handler(self, config, data_source=None):
        """
        Create an SQLite data store and and  request handler using that
        data store.

        This function returns a context manager that in turn provides the data
        source and request handler. The context manager takes care of closing
        both when they are no longer needed.
        """
        with TemporaryDirectory() as tmpdir:
            db_file = os.path.join(tmpdir, "test.db")
            with open_data_store(db_file) as data_store:
                config["db_file"] = db_file
                handler = get_instance_http(config)
                if data_source is not None:
                    handler.set_data_source(data_source)
                try:
                    yield data_store, handler
                finally:
                    handler.close()
