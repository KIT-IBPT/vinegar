"""
HTTP server component of Vinegar.
"""

import abc
import http
import http.client
import http.server
import io
import logging
import shutil
import socket
import socketserver
import threading
import typing

from vinegar.utils.socket import ipv6_address_unwrap, socket_address_to_str

# Logger used by this module
logger = logging.getLogger(__name__)


class _DelegatingRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    Request handler passed to the internal ``HTTPServer``. This request handler
    gets the list of actual request handlers from the ``server`` object and
    delegates to the first handler that can handle the request.

    If there is no handler that can handle the request, HTTP status code 404
    (not found) is sent to the client.

    This request handler overrides the `log_request` and `log_error` methods to
    direct messages to the module logger. It does not override`log_message`
    because that method is not used directly by the base class.
    """

    def __init__(
        self,
        request: socket.socket,
        client_address: typing.Tuple[typing.Union[str, bytes, bytearray], int],
        # Probably because it is defined later, Pylance complains that
        # _ThreadingHttpServer is undefined.
        server: "_ThreadingHttpServer",  # type: ignore
    ):
        super().__init__(request, client_address, server)
        self.server: _ThreadingHTTPServer = server

    def address_string(self):
        # We override this method so that we can unwrap an IPv4 address wrapped
        # in an IPv6 address
        return ipv6_address_unwrap(self.client_address[0])

    # For compatibility, we have to use the method signature from the base
    # class, so we have to disable the warnings that go along with this
    # signature.
    #
    # pylint: disable=redefined-builtin,unused-argument
    def log_error(self, format, *args):
        # We do not use log_error directly and the base class does not use it
        # for anything that we want logged, so we simply do nothing here.
        pass

    def log_request(self, code="-", size="-"):
        if isinstance(code, http.HTTPStatus):
            code = code.value
        logger.info(
            'Processed HTTP request "%s" from %s with status code %s.',
            self.requestline,
            self.address_string(),
            str(code),
        )

    def _delegate_request(self):
        response_started = False
        try:
            # No sane HTTP client will ever send a request path that does not
            # start with a slash or contains a null byte. We do not check that
            # the request path does not contain a null byte after decoding,
            # this is the job of the handler that does the decoding.
            if (not self.path.startswith("/")) or ("\0" in self.path):
                response_started = True
                self.send_error(http.HTTPStatus.BAD_REQUEST)
                return
            for handler in self.server.real_request_handlers:
                context = handler.prepare_context(self.path)
                if handler.can_handle(self.path, context):
                    try:
                        (status, headers, body) = handler.handle(
                            self.path,
                            self.command,
                            # Due to the base class not having property type
                            # hints, the types cannot be guessed correctly, so
                            # we have to ignore them in order to avoid
                            # warnings.
                            self.headers,  # type: ignore
                            self.rfile,  # type: ignore
                            self.client_address,
                            context,
                        )
                    # We really want to catch almost all exceptions here. If we
                    # did not, the server thread would simply crash, and the
                    # error would not be communicated to the client and
                    # wouldn’t be logged properly either.
                    except Exception:  # pylint: disable=broad-exception-caught
                        logger.exception(
                            'Request handler for %s request for file "%s" '
                            "from client %s raised an exception.",
                            self.command,
                            self.path,
                            socket_address_to_str(self.client_address),
                        )
                        response_started = True
                        self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR)
                        return
                    # If status is an error code and there is neither a body
                    # nor are there headers, we use send_error instead of
                    # send_response.
                    response_started = True
                    if (
                        (status.value >= 400)
                        and (not headers)
                        and (body is None)
                    ):
                        self.send_error(status)
                        return
                    self.send_response(status)
                    if headers is not None:
                        for header_name, header_value in headers.items():
                            self.send_header(header_name, header_value)
                        self.end_headers()
                    if body is not None:
                        shutil.copyfileobj(body, self.wfile)
                    return
            self.send_error(http.HTTPStatus.NOT_FOUND)
        # We really want to catch almost all exceptions here. If we did not,
        # the server thread would simply crash, and the error would not be
        # communicated to the client and wouldn’t be logged properly either.
        except Exception:  # pylint: disable=broad-exception-caught
            # We do not want a problem with a request to bubble up into the
            # calling code, so we log the problem and continue.
            logger.exception("Request processing failed.")
            if not response_started:
                self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR)
            return

    # For each support HTTP method, the handle_one_request() method expects a
    # corresponding do_... method.
    do_GET = _delegate_request
    do_HEAD = _delegate_request
    do_POST = _delegate_request
    do_PUT = _delegate_request
    do_DELETE = _delegate_request


# We have to define _ThreadingHTTPServer first because we reference it in
# _DelegatingRequestHandler.
class _ThreadingHTTPServer(
    socketserver.ThreadingMixIn, http.server.HTTPServer
):
    """
    Subclass of ``http.server.HTTPServer`` that uses the
    ``socketserver.ThreadingMixIn``. This means that this server spawns a new
    daemon thread for each request.

    This server also sets the address family to ``socket.AF_INET6`` so that
    IPv6 connections are supported and overrides the `server_bind` method to
    set the ``IPPROTO_IPV6`` ``IPV6_V6ONLY`` socket option to 0.
    """

    def __init__(
        self,
        server_address: typing.Tuple[typing.Union[str, bytes, bytearray], int],
        request_handler_class: typing.Callable[
            [typing.Any, typing.Any, typing.Self],
            socketserver.BaseRequestHandler,
        ],
        bind_and_activate: bool = True,
    ) -> None:
        super().__init__(
            server_address, request_handler_class, bind_and_activate
        )
        self.address_family = socket.AF_INET6
        self.daemon_threads = True
        self.real_request_handlers: typing.List[HttpRequestHandler] = []

    def server_bind(self):
        # socket.IPPROTO_IPV6 is not available when running on Windows and
        # using Python < 3.8, so we fall back to a fixed value if it is not
        # available.
        try:
            ipproto_ipv6 = socket.IPPROTO_IPV6
        except AttributeError:
            ipproto_ipv6 = 41
        # socket.IPV6_V6ONLY, on the other hand, should be available on
        # Windows, at least for the Python versions we care about (>= 3.5). If
        # it is not available or if the call to setsockopt fails, we log a
        # warning, but continue.
        try:
            self.socket.setsockopt(ipproto_ipv6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            logger.warning(
                "Cannot set IPV6_V6ONLY socket option to 0, socket might not "
                "be reachable via IPv4."
            )
        super().server_bind()


class HttpRequestHandler(abc.ABC):
    """
    Interface for a request handler. A request handler should be derived from
    this class and implement the ``can_handle`` and ``handle`` methods.

    The ``can_handle`` and ``handle`` methods are separate, because a request
    handler should only decided whether it can handle a request based on the
    requested filename. If it later finds that it actually cannot handle the
    request due to an unsupport HTTP method, it should simply signal an
    error.

    A request handler can also implement ``prepare_context``. In this case,
    ``prepare_context`` is called before calling ``can_handle`` and the object
    returned by it is passed to ``can_handle`` and ``handle``. This is useful
    when both function need to do some processing on the filename or client
    address. This processing can be implemented in ``prepare_context`` and
    passed to the two other methods through the context so that it does not
    have to be done twice.
    """

    @abc.abstractmethod
    def can_handle(self, filename: str, context: typing.Any) -> bool:
        """
        Tell whether the request can be handled by this request handler.

        Returns ``True`` if the request can be handled and ``False`` if it
        cannot be handled and the next request handler should be tried.

        :param filename:
            filename that has been requested by the client. The filename
            includes the full request path including the query string (if
            present) and has not been URL decoded.
        :param context:
            context object that was returned by ``prepare_context``.
        :return:
            ``True`` if this request handler can handle the specified request,
            ``False`` if the request should be deferred to the next handler.
        """
        return False

    @abc.abstractmethod
    def handle(
        self,
        filename: str,
        method: str,
        headers: http.client.HTTPMessage,
        body: io.BufferedIOBase,
        client_address: typing.Tuple,
        context: typing.Any,
    ) -> typing.Tuple[
        http.HTTPStatus,
        typing.Optional[typing.Mapping[str, str]],
        typing.Optional[io.BufferedIOBase],
    ]:
        """
        Handle the request.

        This method returns a tuple of three items. The first item is the HTTP
        status code, the second item are the headers that shall be sent to the
        client, and the third is a file-like object from which the data for the
        requested file can be read. The returned file-like object must supply
        its data in binary form.

        :param filename:
            filename that has been requested by the client. The filename
            includes the full request path including the query string (if
            present) and has not been URL decoded.
        :param method:
            the HTTP method used for the request (e.g. "GET").
        :param headers:
            HTTP headers provided by the client.
        :param body:
            file-like object that provides the request body sent by the client.
            This file-like object returns ``bytes`` when reading.
        :param client_address:
            client address. The structure of the tuple depends on the address
            family in use, but typically the first element is the client's
            host address and the second element is the client's port number.
        :param context:
            context object that was returned by ``prepare_context``.
        :return:
            tuple of the HTTP status code, the response headers, and a
            file-like object that provides the data that is transferred to the
            client. The file-like object must provide binary data. The response
            headers may be ``None``, which has the same effect as supplying an
            empty dict (no headers are added to the response). The file-like
            object may also be ``None``, which means that the body of the
            response is empty. Typically, this is only useful when indicating
            an error (status code >= 400). In this case, a body with an
            appropriate error message for the status code is generated by the
            server.
        """
        raise NotImplementedError()

    def prepare_context(
        self,
        filename: str,  # pylint: disable=unused-argument
    ) -> typing.Any:
        """
        Prepare a context object for use by ``can_handle`` and ``handle``. This
        method is called for each request before calling ``can_handle``.

        This is useful when both function need to do some processing on the
        filename or client address. This processing can be implemented in
        ``prepare_context`` and passed to the two other methods through the
        context so that it does not have to be done twice.

        The return value of this method is passed to ``can_handle`` and
        ``handle``. The default implementation simply returns ``None``.

        :param filename:
            filename that has been requested by the client. The filename
            includes the full request path including the query string (if
            present) and has not been URL decoded.
        :return:
            context object that is passed to ``can_handle`` and ``handle``.
        """
        return None


class HttpServer:
    """
    HTTP server. This server can serve arbitrary resources, not just files on
    the file system. At the moment, it only supports the ``DELETE``,  ``GET``,
    ``HEAD``, ``POST``, and ``PUT`` request methods.

    This server is internally implemented using the ``http.server.HTTPServer``
    class.

    The server internally uses a daemon thread that processes incoming
    requests. For each request, it creates a new thread that processes this
    request and sends the requested data to the client.
    """

    def __init__(
        self,
        request_handlers: typing.List[HttpRequestHandler],
        bind_address: str = "::",
        bind_port: int = 80,
    ):
        """
        Creates a new HTTP server. The server is not started and its socket is
        not opened or bound when constructing the server object. Instead,
        ``start()`` must be called to start the server.

        :param request_handlers:
            List of request handlers than can handle read requests for this
            server. The request handlers are tried in order. The first request
            handler that can handle a request is used. If no request handler
            that can handle the request is found, an error is signaled to the
            client.
        :param bind_address:
            Address of the interface on which the HTTP server shall listen for
            incoming connections. By default, the server listens on all local
            interfaces.
        :param bind_port:
            Number of the TCP port on which the HTTP server shall listen for
            incoming connections. By default, the server listens on TCP port
            80, this is the officially registered port for HTTP.
        """
        for request_handler in request_handlers:
            if not isinstance(request_handler, HttpRequestHandler):
                raise ValueError(
                    "All request handlers must implement the "
                    "HttpRequestHandler interface."
                )
        self._request_handlers = request_handlers
        self._bind_address = bind_address
        self._bind_port = bind_port
        self._main_thread: typing.Optional[threading.Thread] = None
        self._running = False
        self._running_lock = threading.Lock()
        self._server: typing.Optional[_ThreadingHTTPServer] = None

    def start(self):
        """
        Start this server instance.

        If the server is already running, this method does nothing.
        """
        with self._running_lock:
            if self._running:
                return

            self._server = _ThreadingHTTPServer(
                (self._bind_address, self._bind_port),
                _DelegatingRequestHandler,
            )
            logger.info(
                "HTTP server is listening on %s.",
                socket_address_to_str((self._bind_address, self._bind_port)),
            )
            self._server.real_request_handlers = self._request_handlers
            self._main_thread = threading.Thread(target=self._run, daemon=True)
            self._main_thread.start()
            self._running = True

    def stop(self):
        """
        Stop this server instance.

        If the server is not running, this method does nothing.
        """
        with self._running_lock:
            if not self._running:
                return
            if self._server is not None:
                self._server.shutdown()
            logger.info("HTTP server has been shutdown.")
            self._running = False

    def _run(self):
        if self._server is not None:
            self._server.serve_forever(0.1)


def create_http_server(
    request_handlers: typing.List[HttpRequestHandler],
    bind_address: str = "::",
    bind_port: int = 80,
):
    """
    Create a new HTTP server. The server is not started and its socket is not
    opened or bound when constructing the server object. Instead,
    `~HttpServer.start` must be called to start the server.

    :param request_handlers:
        List of request handlers than can handle read requests for this server.
        The request handlers are tried in order. The first request handler that
        can handle a request is used. If no request handler that can handle the
        request is found, an error is signaled to the client.
    :param bind_address:
        Address of the interface on which the HTTP server shall listen for
        incoming connections. By default, the server listens on all local
        interfaces.
    :param bind_port:
        Number of the TCP port on which the HTTP server shall listen for
        incoming connections. By default, the server listens on TCP port 80,
        this is the officially registered port for HTTP.
    """
    return HttpServer(request_handlers, bind_address, bind_port)
