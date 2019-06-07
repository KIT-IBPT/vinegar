"""
Handlers that handle HTTP or TFTP requests.

Different handlers can be used for different purposes. The most common one is
the `vinegar.request_handler.file` handler, which can serve resources from the
file system.

All handler modules have in common that they must specify a ``get_instance_http``
or ``get_instance_tftp`` function (or both). Each of these functions takes a
`dict` with configuration data as its only argument. These functions must return
an instance of `HttpRequestHandler` or `TftpRequestHandler`.

Request handlers are thread safe.
"""

import importlib

from typing import Any, Mapping

from vinegar.http.server import HttpRequestHandler
from vinegar.tftp.server import TftpRequestHandler

def get_http_request_handler(
    name: str, config: Mapping[Any, Any]) -> HttpRequestHandler:
    """
    Create an instance of the HTTP request handler with the specified name,
    using the specified configuration.

    :param name:
        name of the request handler. If the name contains a dot, it is treated
        as an absolute module name. Otherwise it is treated as a name of one of
        the modules inside the `vinegar.request_handler` module.
    :param: config:
        configuration data for the request handler. The meaning of that data is
        up to the implementation of the request handler.
    :return:
        newly created HTTP request handler.
    """
    module_name = name if '.' in name else '{0}.{1}'.format(__name__, name)
    data_source_module = importlib.import_module(module_name)
    return data_source_module.get_instance_http(config)

def get_tftp_request_handler(
    name: str, config: Mapping[Any, Any]) -> TftpRequestHandler:
    """
    Create an instance of the TFP request handler with the specified name, using
    the specified configuration.

    :param name:
        name of the request handler. If the name contains a dot, it is treated
        as an absolute module name. Otherwise it is treated as a name of one of
        the modules inside the `vinegar.request_handler` module.
    :param: config:
        configuration data for the request handler. The meaning of that data is
        up to the implementation of the request handler.
    :return:
        newly created TFTP request handler.
    """
    module_name = name if '.' in name else '{0}.{1}'.format(__name__, name)
    data_source_module = importlib.import_module(module_name)
    return data_source_module.get_instance_tftp(config)
