"""
TFTP server component of Vinegar.
"""

import abc
import io
import logging
import os
import re
import socket
import struct
import threading
import time
import typing

from vinegar.tftp.protocol import (
    DEFAULT_BLOCK_SIZE,
    MAX_BLOCK_SIZE,
    MAX_BLOCK_NUMBER,
    MAX_REQUEST_PACKET_SIZE,
    MAX_TIMEOUT,
    MIN_BLOCK_SIZE,
    MIN_TIMEOUT,
    OPTION_BLOCK_SIZE,
    OPTION_TIMEOUT,
    OPTION_TRANSFER_SIZE,
    ErrorCode,
    Opcode,
    TransferMode,
    data_packet,
    decode_ack,
    decode_error,
    decode_read_request,
    error_packet,
    options_ack_packet,
)

from vinegar.utils.socket import socket_address_to_str

# Logger used by this module
logger = logging.getLogger(__name__)


class TftpError(Exception):
    """
    Exception raised by `TftpRequestHandler.handle` to indicate that it cannot
    proceed with processing a request.

    This exception can be constructed with an optional ``message`` and an
    optional ``error_code`` that must be an instance of `ErrorCode`.
    """

    # Error code that shall be sent to the client.
    error_code = ErrorCode.NOT_DEFINED

    # Message that shall be sent to the client.
    message = ""

    def __init__(
        self, message: str = "", error_code: ErrorCode = ErrorCode.NOT_DEFINED
    ):
        if message:
            super().__init__(message)
        else:
            super().__init__()
        self.message = message
        self.error_code = error_code


class TftpRequestHandler(abc.ABC):
    """
    Interface for a request handler. A request handler should be derived from
    this class and implement the ``can_handle`` and ``handle`` methods.

    The ``can_handle`` and ``handle`` methods are separate, so that the TFTP
    server only has to create a new socket and thread when it can actually
    handle the request.

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
            filename that has been requested by the client.
        :param context:
            context object that was returned by ``prepare_context``.
        :return:
            ``True`` if this request handler can handle the specified request,
            ``False`` if the request should be deferred to the next handler.
        """
        return False

    @abc.abstractmethod
    def handle(
        self, filename: str, client_address: typing.Tuple, context: typing.Any
    ) -> io.BufferedIOBase:
        """
        Handle the request. This method returns a file-like object from which
        the data for the requested file can be read. The returned file-like
        object must supply its data in binary form.

        If the request handler detects that it actually cannot send data to the
        client (e.g. because the client lacks the required permissions), it
        should signal that by raising a `TftpError`.

        :param filename:
            filename that has been requested by the client.
        :param client_address:
            client address. The structure of the tuple depends on the address
            family in use, but typically the first element is the client's
            host address and the second element is the client's port number.
        :param context:
            context object that was returned by ``prepare_context``.
        :return:
            file-like object that provides the data that is transferred to the
            client. The file-like object must provide binary data.
        """
        raise NotImplementedError()

    def prepare_context(self, filename: str) -> typing.Any:
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
            filename that has been requested by the client.
        :return:
            context object that is passed to ``can_handle`` and ``handle``.
        """
        return None


class TftpServer:
    """
    Server implementing the TFTP (RFC 1350) protocol. This server can serve
    arbitrary resources (read-only), not just files on the file system.

    This implementation supports the TFTP blocksize option (RFC 2348), the TFTP
    timeout interval option (RFC 2349), and the TFTP transfer size option.
    Support for the transfer size option is limited to binary transfers and
    request handlers that provide a file object for which we can actually
    determine the size.

    The server internally uses a daemon thread that processes incoming
    requests. For each request, it creates a new thread that processes this
    request and sends the requested data to the client.
    """

    def __init__(
        self,
        request_handlers: typing.List[TftpRequestHandler],
        bind_address: str = "::",
        bind_port: int = 69,
        default_timeout: float = 10.0,
        max_timeout: float = 30.0,
        max_retries: int = 3,
        max_block_size: int = MAX_BLOCK_SIZE,
        block_counter_wrap_value: int = 0,
    ):
        """
        Creates a new TFTP server. The server is not started and its socket
        is not opened or bound when constructing the server object. Instead,
        ``start()`` must be called to start the server.

        :param request_handlers:
            List of request handlers than can handle read requests for this
            server. The request handlers are tried in order. The first request
            handler that can handle a request is used. If no request handler
            that can handle the request is found, an error is signaled to the
            client.
        :param bind_address:
            Address of the interface on which the TFTP server shall listen for
            incoming connections. By default, the server listens on all local
            interfaces.
        :param bind_port:
            Number of the UDP port on which the TFTP server shall listen for
            incoming connections. By default, the server listens on UDP port
            69, this is the officially registered port for TFTP.
        :param default_timeout:
            Timeout (in seconds) that is used for connections if the client
            does not specify a timeout.  This number must be greater than or
            equal to 1 and less than ``max_timeout``. If it it is outside this
            range, it is silently changed to be within this range. The default
            is 10.
        :param max_timeout:
            Max. timeout interval (in seconds) that may be specified by a
            client. If a client requests a timeout that is greater, the timeout
            is limited to this number. This number must be greater than or
            equal to 1 and less than or equal to 255. The default is 30.
        :param max_retries:
            Max. number of attempts to resend a packet before giving up. This
            limit is important because it keeps a connection (and the
            associated thread) from stalling forever when the connection to a
            client is lost. This number must be greater than or equal to 1. The
            default value is 3.
        :param max_block_size:
            Max. size of a single block (in bytes). This setting is only used
            when a client requests a different than the default block size
            (512 bytes). In that case, if the client requests a block size that
            is greater than this setting, the block size is reduces to this
            setting. This can be useful when a client requests a block size
            that would result in IP fragmentation, but IP fragmentation is not
            desired. This setting must be a number between 512 (the default
            block size) and 65464 (the max. block size allowed by the
            protocol). The default value is 65464.
        :param block_counter_wrap_value:
            Block at which to start counting again after reaching the max.
            possible block count. This value should be 0 or 1. As the TFTP
            standard (RFC 1350) does not specify what should happen if the
            block count range is exceeded, some clients expect it to wrap
            around to 0 while other expect it to wrap around to 1. If this
            parameter is set to ``None``, the block counter will never wrap
            which means that large files cannot be transferred. This is only
            necessary if dealing with clients that show unexpected behavior
            when the block counter wraps. In the context of PXE boot, most
            clients seem to expect 0, so that is what we use by default.
        """
        for request_handler in request_handlers:
            if not isinstance(request_handler, TftpRequestHandler):
                raise ValueError(
                    "All request handlers must implement the "
                    "TftpRequestHandler interface."
                )
        self._request_handlers = request_handlers
        self._bind_address = bind_address
        self._bind_port = bind_port
        if max_timeout < MIN_TIMEOUT:
            self._max_timeout = MIN_TIMEOUT
        elif max_timeout > MAX_TIMEOUT:
            self._max_timeout = MAX_TIMEOUT
        else:
            self._max_timeout = max_timeout
        if default_timeout < MIN_TIMEOUT:
            self._default_timeout = MIN_TIMEOUT
        elif default_timeout > self._max_timeout:
            self._default_timeout = self._max_timeout
        else:
            self._default_timeout = default_timeout
        if max_retries < 1:
            self._max_retries = 1
        else:
            self._max_retries = max_retries
        if max_block_size < DEFAULT_BLOCK_SIZE:
            self._max_block_size = DEFAULT_BLOCK_SIZE
        elif max_block_size > MAX_BLOCK_SIZE:
            self._max_block_size = MAX_BLOCK_SIZE
        else:
            self._max_block_size = max_block_size
        self._block_counter_wrap_value = block_counter_wrap_value
        self._running = False
        self._shutdown_requested = False
        self._running_lock = threading.Lock()

    def start(self):
        """
        Starts this server instance. This opens the server socket, binds it,
        and creates a deamon thread that processes requests.

        If the server is already running, this method does nothing.
        """
        with self._running_lock:
            if self._running:
                return
            self._socket = socket.socket(
                family=socket.AF_INET6, type=socket.SOCK_DGRAM
            )
            try:
                self._socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
                )
                # This timeout specifies how quickly we can shutdown the
                # server.
                self._socket.settimeout(0.1)
                # socket.IPPROTO_IPV6 is not available when running on Windows
                # and using Python < 3.8, so we fall back to a fixed value if
                # it is not available.
                try:
                    ipproto_ipv6 = socket.IPPROTO_IPV6
                except AttributeError:
                    ipproto_ipv6 = 41
                # socket.IPV6_V6ONLY, on the other hand, should be available on
                # Windows, at least for the Python versions we care about
                # (>= 3.5). If it is not available or if the call to setsockopt
                # fails, we log a warning, but continue.
                try:
                    self._socket.setsockopt(
                        ipproto_ipv6, socket.IPV6_V6ONLY, 0
                    )
                except Exception:
                    logger.warning(
                        "Cannot set IPV6_V6ONLY socket option to 0, socket "
                        "might not be reachable via IPv4."
                    )
                self._socket.bind((self._bind_address, self._bind_port))
                logger.info(
                    "TFTP server is listening on %s.",
                    socket_address_to_str(
                        (self._bind_address, self._bind_port)
                    ),
                )
                self._main_thread = threading.Thread(
                    target=self._run, daemon=True
                )
                self._main_thread.start()
                self._running = True
            except BaseException:
                self._socket.close()
                self._socket = None
                raise

    def stop(self):
        """
        Stops this server instance.

        This closes the server socket and stops the daemon thread that has been
        created. Please note that this will not close the sockets or shutdown
        the threads that have been created for requests. Each of these threads
        will shutdown when its associated request is fully processed or its
        timeout is reached.
        """
        with self._running_lock:
            if not self._running or self._shutdown_requested:
                return
            self._shutdown_requested = True
        # We cannot hold the lock while waiting for the thread to quit because
        # the thread might try to acquire the lock.
        try:
            self._main_thread.join()
            self._main_thread = None
            logger.info("TFTP server has been shutdown.")
        finally:
            with self._running_lock:
                self._running = False
                self._shutdown_requested = False

    def _handle_read(
        self,
        filename,
        transfer_mode,
        options,
        client_address,
        handler_function,
        handler_context,
    ):
        # If debugging is enabled, we make the info message more verbose.
        if logger.isEnabledFor(logging.DEBUG):
            logger.info(
                'Received read request for file "%s" from client %s using '
                "mode %s and options %s.",
                filename,
                socket_address_to_str(client_address),
                transfer_mode,
                options,
            )
        else:
            logger.info(
                'Handling read request for file "%s" from client %s.',
                filename,
                socket_address_to_str(client_address),
            )
        # Constructing the request object is sufficient for handling the
        # request. The actual request handling is done by a daemon thread that
        # is created when constructing the object.
        _TftpReadRequest(
            filename,
            transfer_mode,
            options,
            client_address,
            handler_function,
            handler_context,
            self._default_timeout,
            self._max_timeout,
            self._max_retries,
            self._max_block_size,
            self._block_counter_wrap_value,
        )

    def _process_invalid_request(self, opcode, req_addr):
        logger.debug(
            "Received request from %s with opcode %s, but only READ or WRITE "
            "requests are allowed on this server port.",
            socket_address_to_str(req_addr),
            opcode,
        )
        data = error_packet(
            ErrorCode.ILLEGAL_OPERATION,
            "Only read or write requests are allowed on this port.",
        )
        self._socket.sendto(data, req_addr)

    def _process_read_request(self, req_data, req_addr):
        try:
            (filename, transfer_mode, options) = decode_read_request(req_data)
        except Exception:
            # If we cannot decode the read request, this is an error, but in
            # the client, not the server, so we log it with a level of INFO.
            logger.info(
                "Decoding read request from %s resulted in an exception.",
                socket_address_to_str(req_addr),
            )
            data = error_packet(
                ErrorCode.ILLEGAL_OPERATION, "Malformed read request."
            )
            self._socket.sendto(data, req_addr)
            return
        # The mail transfer mode is only valid for write requests (and we do
        # not support it anyway).
        if transfer_mode == TransferMode.MAIL:
            # If the client requests transfer mode "mail" this is not an error
            # in the server, so we log it with a level of INFO.
            logger.info(
                "Read request from %s requested unsupported transfer mode "
                '"mail".',
                socket_address_to_str(req_addr),
            )
            data = error_packet(
                ErrorCode.ILLEGAL_OPERATION,
                "Transfer mode mail is not allowed for read requests.",
            )
            self._socket.sendto(data, req_addr)
            return
        # We try the request handlers in order until we find one that can
        # handle the request.
        for request_handler in self._request_handlers:
            handler_context = request_handler.prepare_context(filename)
            if request_handler.can_handle(filename, handler_context):
                self._handle_read(
                    filename,
                    transfer_mode,
                    options,
                    req_addr,
                    request_handler.handle,
                    handler_context,
                )
                return
        # If we cannot find such a request handler, we tell the client that the
        # file does not exist.
        logger.info(
            'No handler can fulfill request for file "%s" from client %s.',
            filename,
            socket_address_to_str(req_addr),
        )
        data = error_packet(
            ErrorCode.FILE_NOT_FOUND, "The requested file does not exist."
        )
        self._socket.sendto(data, req_addr)

    def _process_request(self, req_data, req_addr):
        # The TFTP specification (RFC 1350) says that a request that is denied
        # should result in an error packet being sent. It also specifies that
        # an invalid packet received as part of a connection should result in
        # an error packet being sent. However, it does not specify what should
        # happen if an invalid packet is sent to the request port.
        # Most other implementations seem to ignore requests with an invalid
        # opcode, so we choose to do the same. We still log a debug message in
        # these cases.
        # A request must have at least two bytes for the opcode.
        if len(req_data) < 2:
            logger.debug(
                "Invalid request from %s: The request was too short.",
                socket_address_to_str(req_addr),
            )
            return
        (opcode_num,) = struct.unpack_from("!H", req_data)
        try:
            opcode = Opcode(opcode_num)
        except Exception:
            logger.debug(
                "Invalid request from %s: Opcode %s is not recognized.",
                socket_address_to_str(req_addr),
                opcode_num,
            )
            return
        if opcode == Opcode.READ_REQUEST:
            self._process_read_request(req_data, req_addr)
        elif opcode == Opcode.WRITE_REQUEST:
            self._process_write_request(req_data, req_addr)
        else:
            self._process_invalid_request(opcode, req_addr)

    def _process_write_request(self, req_data, req_addr):
        logger.error(
            "Received write request from %s, but this server only supports "
            "read requests",
            socket_address_to_str(req_addr),
        )
        data = error_packet(
            ErrorCode.ACCESS_VIOLATION,
            "Write requests are not allowed by this server.",
        )
        self._socket.sendto(data, req_addr)

    def _run(self):
        try:
            while True:
                with self._running_lock:
                    if self._shutdown_requested:
                        break
                try:
                    (req_data, req_addr) = self._socket.recvfrom(
                        MAX_REQUEST_PACKET_SIZE
                    )
                    self._process_request(req_data, req_addr)
                except socket.timeout:
                    # A timeout is not an error, it just means that we should
                    # check the _shutdown_requested flag again.
                    pass
                except Exception:
                    # We do not want a problem with a request to stop the whole
                    # server, so we log the problem and continue.
                    logger.exception("Request processing failed.")
        finally:
            self._socket.close()


class _TftpReadRequest:
    """
    Represents the connection associated with a read request. This object wraps
    the underlying UDP socket and the daemon thread communicating through that
    socket.

    A new instance of this class is created for each read request.
    """

    class _BlockCounterOverflow(Exception):
        """
        Exception signaling that a transferred file was so large that the block
        counter reached its limit, but wrapping was disabled.
        """

        pass

    class _ClientError(Exception):
        """
        Exception signaling that an error message was received from the client.
        """

        pass

    class _InvalidPacket(Exception):
        """
        Exception signaling an invalid packet was received from the client.
        """

        pass

    class _NetasciiReader:
        """
        Reader utility that wraps a binary file-like object and converts to
        netascii (converting single instances of carriage return (CR) and line
        feed (LF) to CR LF sequences).
        """

        CR = 13
        LF = 10

        def __init__(self, file):
            self._file = file
            self._data = b""
            self._last_byte_was_cr = False

        def read(self, size):
            while size > len(self._data):
                new_data = self._file.read(size - len(self._data))
                # If new_data is empty, we have reached end-of-file.
                if not new_data:
                    break
                else:
                    start_index = 0
                    index = 0
                    # If the last byte that we read was a CR we have to check
                    # whether the next byte is an LF. If so, we skip it,
                    # because we already inserted that LF when we read the CR.
                    if self._last_byte_was_cr:
                        start_index += 1
                        index += 1
                        self._last_byte_was_cr = False
                    while index < len(new_data):
                        if new_data[index] == self.CR:
                            if index + 1 == len(new_data):
                                # If we find a CR but it is the last byte, we
                                # cannot know whether it is going to be
                                # followed by an LF, so we have to remember
                                # that we saw a CR so that we can skip the LF
                                # if we read it later.
                                self._last_byte_was_cr = True
                                self._data += (
                                    new_data[start_index:index] + b"\r\n"
                                )
                                index += 1
                                start_index = index
                            elif new_data[index + 1] == self.LF:
                                # If the CR is followed by an LF, everything is
                                # fine and we can continue.
                                index += 2
                            else:
                                # If the CR is not followed by an LF, we have
                                # to insert one.
                                self._data += (
                                    new_data[start_index:index] + b"\r\n"
                                )
                                index += 1
                                start_index = index
                        elif new_data[index] == self.LF:
                            # We already handled the case that an LF is
                            # preceded by a CR, so we know that we have to
                            # insert a CR.
                            self._data += new_data[start_index:index] + b"\r\n"
                            index += 1
                            start_index = index
                        else:
                            # For every regular byte, we simply continue with
                            # the next one.
                            index += 1
                    # Finally, we have to append the remaining new data.
                    self._data += new_data[start_index:index]
            data = self._data[0:size]
            self._data = self._data[size:]
            return data

    class _OctetReader:
        """
        Reader utility that wraps a binary file-like object and returns the
        bytes as-is.
        """

        def __init__(self, file):
            self._file = file
            self._data = b""

        def read(self, size):
            while size > len(self._data):
                new_data = self._file.read(size - len(self._data))
                # If new_data is empty, we have reached end-of-file.
                if not new_data:
                    break
                else:
                    self._data += new_data
            data = self._data[0:size]
            self._data = self._data[size:]
            return data

    class _TransferAborted(Exception):
        """
        Exception signaling that the transfer has been aborted by the client.
        """

        pass

    def __init__(
        self,
        filename,
        transfer_mode,
        options,
        client_address,
        handler_function,
        handler_context,
        default_timeout,
        max_timeout,
        max_retries,
        max_block_size,
        block_counter_wrap_value,
    ):
        self._filename = filename
        if transfer_mode == TransferMode.NETASCII:
            self._netascii_mode = True
        elif transfer_mode == TransferMode.OCTET:
            self._netascii_mode = False
        else:
            raise ValueError(
                "Unsupported transfer mode: {0}".format(transfer_mode)
            )
        self._client_address = client_address
        self._handler_function = handler_function
        self._handler_context = handler_context
        self._max_retries = max_retries
        self._block_counter_wrap_value = block_counter_wrap_value
        # We convert all option names to lower case so that we can compare more
        # easily.
        options = {name.lower(): value for name, value in options.items()}
        # We only use those options that we can support.
        supported_options = {}
        # For the block-size option, we can use a smaller value than the one
        # suggested by the client (but we must always use at least 8 bytes).
        # We still verify that the string specified by the client actually
        # represents a valid integer number in order to avoid funny behavior.
        self._block_size = DEFAULT_BLOCK_SIZE
        if OPTION_BLOCK_SIZE in options and _REGEXP_POSITIVE_INT.fullmatch(
            options[OPTION_BLOCK_SIZE]
        ):
            requested_block_size = int(options[OPTION_BLOCK_SIZE])
            if (
                requested_block_size >= MIN_BLOCK_SIZE
                and requested_block_size <= max_block_size
            ):
                supported_options[OPTION_BLOCK_SIZE] = str(
                    requested_block_size
                )
                self._block_size = requested_block_size
        # For the timeout option, we may only accept the option as suggested by
        # the client or reject it all together. Sending a smaller value back to
        # the client is not allowed by the specification.
        self._timeout = default_timeout
        if OPTION_TIMEOUT in options and _REGEXP_POSITIVE_INT.fullmatch(
            options[OPTION_TIMEOUT]
        ):
            requested_timeout = int(options[OPTION_TIMEOUT])
            if (
                requested_timeout >= MIN_TIMEOUT
                and requested_timeout <= max_timeout
            ):
                supported_options[OPTION_TIMEOUT] = str(requested_timeout)
                self._timeout = requested_timeout
        # When the client specifies the transfer size option, it has to send a
        # value of 0 with the read request.
        if (
            OPTION_TRANSFER_SIZE in options
            and options[OPTION_TRANSFER_SIZE] == "0"
        ):
            supported_options[OPTION_TRANSFER_SIZE] = None
        self._options = supported_options
        # After we have setup everything, we can start the processing thread.
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _calc_next_block_number(self, block_number):
        if block_number == MAX_BLOCK_NUMBER:
            if self._block_counter_wrap_value is None:
                raise _TftpReadRequest._BlockCounterOverflow()
            else:
                return self._block_counter_wrap_value
        else:
            return block_number + 1

    def _process_request(self):
        try:
            if self._options:
                self._send_options_ack()
            self._send_data()
        except socket.timeout:
            # If we got a timeout the max. number of retries has been reached
            # and we give up.
            logger.info(
                'Request for file "%s" from client %s timed out.',
                self._filename,
                socket_address_to_str(self._client_address),
            )
        except _TftpReadRequest._BlockCounterOverflow:
            # This exception is raised if a file is so large that the limit of
            # the block counter is reached, but wrapping of the counter is not
            # allowed.
            logger.error(
                'Processing of request for file "%s" from client %s was '
                "aborted due the block counter reaching its limit.",
                self._filename,
                socket_address_to_str(self._client_address),
            )
            # When sending the error, we want to use a fresh timeout value.
            self._socket.settimeout(self._timeout)
            self._send(
                error_packet(
                    ErrorCode.NOT_DEFINED,
                    "File is too large to complete the transfer.",
                )
            )
        except _TftpReadRequest._ClientError as e:
            # If the client sent an error message, we log it and abort this
            # connection.
            logger.info(
                'Processing of request for file "%s" from client %s was '
                "aborted due to a client error: %s",
                self._filename,
                socket_address_to_str(self._client_address),
                e.args[0],
            )
        except _TftpReadRequest._InvalidPacket as e:
            message = e.args[0]
            # If we received an invalid packet, we log this, send an error to
            # the client, and abort this connection.
            logger.info(
                'Processing of request for file "%s" from client %s was '
                "aborted due to an invalid client packet: %s",
                self._filename,
                socket_address_to_str(self._client_address),
                message,
            )
            # When sending the error, we want to use a fresh timeout value.
            self._socket.settimeout(self._timeout)
            self._send(error_packet(ErrorCode.NOT_DEFINED, message))
        except _TftpReadRequest._TransferAborted:
            # The client aborting a transfer is not an error, but we log a
            # simple informational message.
            logger.info(
                'Processing of request for file "%s" from client %s was '
                "aborted on client request.",
                self._filename,
                socket_address_to_str(self._client_address),
            )
        except Exception:
            # Otherwise, there must be some kind of internal error, so we log
            # the exception and send an error code to the client.
            logger.exception(
                'Exception while processing read request for file "%s" from '
                "client %s.",
                self._filename,
                socket_address_to_str(self._client_address),
            )
            data = error_packet(
                ErrorCode.NOT_DEFINED,
                "An internal error occurred while trying to fulfill the "
                "request.",
            )
            # When sending the error, we want to use a fresh timeout value.
            self._socket.settimeout(self._timeout)
            self._send(data)

    def _process_transfer_size_option(self):
        # If the client did not specify the transfer size option, we do not
        # have to do anything.
        if OPTION_TRANSFER_SIZE not in self._options:
            return
        # In text mode, determing the file size is hard because the size might
        # might change due to line breaks being converted. For this reason, we
        # do not support the transfer size option in text mode. This is
        # consistent with what other TFTP servers (e.g. tftpd-hpa) do.
        if self._netascii_mode:
            # We have to delete the transfer size option so that we do not try
            # to send the option back to the client.
            del self._options[OPTION_TRANSFER_SIZE]
            return
        # In binary mode, we can try to determine the transfer size for two
        # cases: If it is an instance of BytesIO or if it is backed by a real
        # file.
        if isinstance(self._file, io.BytesIO):
            # An instance of bytes IO should have a getbuffer() method that
            # returns a memoryview instance. The length of that memoryview is
            # the size of the buffer and we substract the current position
            # because in theory the code that returned the file object could
            # already have read from it.
            try:
                self._options[OPTION_TRANSFER_SIZE] = str(
                    len(self._file.getbuffer()) - self._file.tell()
                )
            except Exception:
                # We ignore any exception that might happen here: We can still
                # transfer the file, we just cannot tell its size.
                del self._options[OPTION_TRANSFER_SIZE]
        else:
            # For any other file, we check whether we can get the backing file
            # descriptor. If we can, we try to get the size of the associated
            # file. This might fail if the file descriptor does not refer to a
            # regular file, but something like a pipe. If we can get the file
            # size, we substract the current position from it because in
            # theory, the code that returned the file object might already have
            # read some data.
            try:
                file_stat = os.fstat(self._file.fileno())
                self._options[OPTION_TRANSFER_SIZE] = str(file_stat.st_size)
            except Exception:
                # We ignore any exception that might happen here: We can still
                # transfer the file, we just cannot tell its size.
                del self._options[OPTION_TRANSFER_SIZE]

    def _receive(self):
        self._set_socket_timeout()
        (data, from_addr) = self._socket.recvfrom(MAX_REQUEST_PACKET_SIZE)
        # The TFTP specification demands that we send an error packet to each
        # client that sends a packet to a port that belongs to the connection
        # of a different client. For this connection, we are supposed to ignore
        # such a packet and continue waiting for a packet from the right
        # client.
        while from_addr != self._client_address:
            logger.debug(
                "Received unexpected packet from %s on socket handling "
                "connection from %s.",
                socket_address_to_str(from_addr),
                socket_address_to_str(self._client_address),
            )
            data = error_packet(
                ErrorCode.UNKNOWN_TRANSFER_ID,
                "This port is associated with a different client connection.",
            )
            self._socket.sendto(data, from_addr)
            # Some time has already passed, so we have to reset the socket
            # timeout.
            self._set_socket_timeout()
            (data, from_addr) = self._socket.recvfrom(MAX_REQUEST_PACKET_SIZE)
        return data

    def _receive_ack(self):
        data = self._receive()
        if len(data) < 2:
            raise _TftpReadRequest._InvalidPacket("Short packet received.")
        (opcode_num,) = struct.unpack_from("!H", data)
        try:
            opcode = Opcode(opcode_num)
        except ValueError:
            raise _TftpReadRequest._InvalidPacket(
                "Received packet with invalid opcode %s.", opcode_num
            )
        if opcode == Opcode.ACK:
            try:
                block_number = decode_ack(data)
                logger.debug(
                    "Received ACK for block # %s from %s.",
                    block_number,
                    socket_address_to_str(self._client_address),
                )
                return block_number
            except ValueError:
                raise _TftpReadRequest._InvalidPacket(
                    "Received malformed ACK packet."
                )
        elif opcode == Opcode.ERROR:
            (error_code, error_message) = decode_error(data)
            if error_code == ErrorCode.TRANSFER_ABORTED:
                raise _TftpReadRequest._TransferAborted()
            if error_code is not None and error_message:
                raise _TftpReadRequest._ClientError(
                    "Error code {0}: {1}".format(
                        error_code.value, error_message
                    )
                )
            elif error_code is not None:
                raise _TftpReadRequest._ClientError(
                    "Error code {0}.".format(error_code.value)
                )
            elif error_message:
                raise _TftpReadRequest._ClientError(
                    "Error code unknown: {0}".format(error_message)
                )
            else:
                raise _TftpReadRequest._ClientError("Unknown error.")

    def _reset_timeout(self):
        self._time_limit = time.monotonic() + self._timeout

    def _run(self):
        try:
            self._socket = socket.socket(
                family=socket.AF_INET6, type=socket.SOCK_DGRAM
            )
        except Exception:
            logger.exception(
                'Error creating socket for read request for file "%s" from '
                "client %s.",
                self._filename,
                socket_address_to_str(self._client_address),
            )
            return
        # We want to make sure that we always close the socket, so we use it in
        # a with statement.
        with self._socket:
            self._socket.settimeout(self._timeout)
            # socket.IPPROTO_IPV6 is not available when running on Windows and
            # using Python < 3.8, so we fall back to a fixed value if it is not
            # available.
            try:
                ipproto_ipv6 = socket.IPPROTO_IPV6
            except AttributeError:
                ipproto_ipv6 = 41
            # socket.IPV6_V6ONLY, on the other hand, should be available on
            # Windows, at least for the Python versions we care about (>= 3.5).
            # If it is not available or if the call to setsockopt fails, we do
            # not even log a warning because we most likely already logged that
            # warning for the main socket.
            try:
                self._socket.setsockopt(ipproto_ipv6, socket.IPV6_V6ONLY, 0)
            except Exception:
                pass
            try:
                self._file = self._handler_function(
                    self._filename, self._client_address, self._handler_context
                )
            except TftpError as e:
                # A TftpError is not necessarily a "real" error, so we only log
                # it with a level of info.
                logger.info(
                    'Request handler for read request for file "%s" from '
                    "client %s signalled an error with error code %s and "
                    'message "%s".',
                    self._filename,
                    socket_address_to_str(self._client_address),
                    e.error_code,
                    e.message,
                )
                data = error_packet(e.error_code, e.message)
                # When sending the error, we want to use a fresh timeout value.
                self._socket.settimeout(self._timeout)
                self._send(data)
                return
            except Exception:
                logger.exception(
                    'Request handler for read request for file "%s" from '
                    "client %s raised an exception.",
                    self._filename,
                    socket_address_to_str(self._client_address),
                )
                data = error_packet(
                    ErrorCode.NOT_DEFINED,
                    "An internal error occurred while trying to fulfill the "
                    "request.",
                )
                # When sending the error, we want to use a fresh timeout value.
                self._socket.settimeout(self._timeout)
                self._send(data)
                return
            # We always want to close the file-like object, so we use it in a
            # with statement.
            with self._file:
                # If the client requested the file size, we tell it if
                # possible. We do this here because we need access to the file
                # in order to determine its size.
                self._process_transfer_size_option()
                if self._netascii_mode:
                    self._file_reader = _TftpReadRequest._NetasciiReader(
                        self._file
                    )
                else:
                    self._file_reader = _TftpReadRequest._OctetReader(
                        self._file
                    )
                self._process_request()

    def _send(self, data):
        self._socket.sendto(data, self._client_address)

    def _send_data(self):
        block_number = 0
        data = self._file_reader.read(self._block_size)
        while len(data) == self._block_size:
            block_number = self._calc_next_block_number(block_number)
            self._send_data_block(block_number, data)
            data = self._file_reader.read(self._block_size)
        # Finally, we have to send the last block. If the last block is empty,
        # we still have to send it in order to signal end-of-file.
        block_number = self._calc_next_block_number(block_number)
        self._send_data_block(block_number, data)

    def _send_data_block(self, block_number, data):
        packet_data = data_packet(block_number, data)
        tries_left = self._max_retries + 1
        ack_received = False
        while not ack_received and tries_left > 0:
            # With each try, we have to reset the timeout.
            self._reset_timeout()
            logger.debug(
                "Sending DATA with block # %s and %s bytes of data to %s.",
                block_number,
                len(data),
                socket_address_to_str(self._client_address),
            )
            try:
                self._send(packet_data)
                while not ack_received:
                    ack_block_number = self._receive_ack()
                    # The block number in the ACK packet has to match the
                    # block number in the DATA packet.
                    ack_received = ack_block_number == block_number
            except socket.timeout:
                if tries_left > 0:
                    tries_left -= 1
                else:
                    raise

    def _send_options_ack(self):
        data = options_ack_packet(self._options)
        tries_left = self._max_retries + 1
        ack_received = False
        while not ack_received and tries_left > 0:
            # With each try, we have to reset the timeout.
            self._reset_timeout()
            logger.debug(
                "Sending OACK with options %s to %s.",
                self._options,
                socket_address_to_str(self._client_address),
            )
            self._send(data)
            try:
                while not ack_received:
                    block_number = self._receive_ack()
                    # The ACK for the options ACK has to use a block number of
                    # zero.
                    ack_received = block_number == 0
            except socket.timeout:
                if tries_left > 0:
                    tries_left -= 1
                else:
                    raise

    def _set_socket_timeout(self):
        now = time.monotonic()
        time_remaining = self._time_limit - now
        if time_remaining > 0.0:
            self._socket.settimeout(time_remaining)
        else:
            # If no time is remaining, we set the socket timeout to 1 ms. If we
            # set it to 0, we would switch the socket into the non-blocking
            # mode, which would have undesired side effects.
            self._socket.settimeout(0.001)


# We use this regular expression to verify that an option that must be a
# positive integer has been specified correctly.
_REGEXP_POSITIVE_INT = re.compile("[1-9][0-9]*")


def create_tftp_server(
    request_handlers: typing.List[TftpRequestHandler],
    bind_address: str = "::",
    bind_port: int = 69,
    default_timeout: float = 10.0,
    max_timeout: float = 30.0,
    max_retries: int = 3,
    max_block_size: int = MAX_BLOCK_SIZE,
    block_counter_wrap_value: int = 0,
):
    """
    Create a new TFTP server. The server is not started and its socket
    is not opened or bound when constructing the server object. Instead,
    `~TftpServer.start()` must be called to start the server.

    :param request_handlers:
        List of request handlers than can handle read requests for this
        server. The request handlers are tried in order. The first request
        handler that can handle a request is used. If no request handler
        that can handle the request is found, an error is signaled to the
        client.
    :param bind_address:
        Address of the interface on which the TFTP server shall listen for
        incoming connections. By default, the server listens on all local
        interfaces.
    :param bind_port:
        Number of the UDP port on which the TFTP server shall listen for
        incoming connections. By default, the server listens on UDP port 69,
        this is the officially registered port for TFTP.
    :param default_timeout:
        Timeout (in seconds) that is used for connections if the client does
        not specify a timeout.  This number must be greater than or equal to
        1 and less than ``max_timeout``. If it it is outside this range, it
        is silently changed to be within this range. The default is 10.
    :param max_timeout:
        Max. timeout interval (in seconds) that may be specified by a
        client. If a client requests a timeout that is greater, the timeout
        is limited to this number. This number must be greater than or equal
        to 1 and less than or equal to 255. The default is 30.
    :param max_retries:
        Max. number of attempts to resend a packet before giving up. This
        limit is important because it keeps a connection (and the associated
        thread) from stalling forever when the connection to a client is
        lost. This number must be greater than or equal to 1. The default
        value is 3.
    :param max_block_size:
        Max. size of a single block (in bytes). This setting is only used
        when a client requests a different than the default block size (512
        bytes). In that case, if the client requests a block size that is
        greater than this setting, the block size is reduces to this
        setting. This can be useful when a client requests a block size that
        would result in IP fragmentation, but IP fragmentation is not
        desired. This setting must be a number between 512 (the default
        block size) and 65464 (the max. block size allowed by the protocol).
        The default value is 65464.
    :param block_counter_wrap_value:
        Block at which to start counting again after reaching the max.
        possible block count. This value should be 0 or 1. As the TFTP
        standard (RFC 1350) does not specify what should happen if the block
        count range is exceeded, some clients expect it to wrap around to 0
        while other expect it to wrap around to 1. If this parameter is set
        to ``None``, the block counter will never wrap which means that
        large files cannot be transferred. This is only necessary if dealing
        with clients that show unexpected behavior when the block counter
        wraps. In the context of PXE boot, most clients seem to expect 0, so
        that is what we use by default.
    :return:
        server object that is ready to be started.
    """
    return TftpServer(
        request_handlers,
        bind_address,
        bind_port,
        default_timeout,
        max_timeout,
        max_retries,
        max_block_size,
        block_counter_wrap_value,
    )
