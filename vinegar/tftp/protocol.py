"""
TFTP protocol definitions and utility functions.
"""

import enum
import struct
import typing

#: Default size of a transfer block in bytes. This block size is used if the
#: client does not request a specific block size.
DEFAULT_BLOCK_SIZE = 512

#: Highest possible block number. Beyond this number, the block counter has to
#: wrap back to zero or one.
MAX_BLOCK_NUMBER = 65535

#: Maximum transfer block size that may be requested by a client.
MAX_BLOCK_SIZE = 65464

#: Maximum size of a request packet in bytes. A TFTP request must never exceed
#: that size.
MAX_REQUEST_PACKET_SIZE = 512

#: Maximum timeout interval that is alloed by RFC 2349.
MAX_TIMEOUT = 255

#: Minimum block size that may be requested by a client.
MIN_BLOCK_SIZE = 8

#: Minimum timeout interval that is allowed by RFC 2349.
MIN_TIMEOUT = 1

#: Name of the block-size option.
OPTION_BLOCK_SIZE = 'blksize'

#: Name of the timeout-interval option.
OPTION_TIMEOUT = 'timeout'

#: Name of the transfer-size option.
OPTION_TRANSFER_SIZE = 'tsize'


@enum.unique
class ErrorCode(enum.IntEnum):
    """
    Code identifying the type of of error in a TFTP error packet.
    """

    #: Error does not fall into any of the other well-defined categories.
    NOT_DEFINED = 0

    #: Requested file could not be found.
    FILE_NOT_FOUND = 1

    #: Access to the requested file has been forbidden.
    ACCESS_VIOLATION = 2

    #: The disk is full (for write requests).
    DISK_FULL = 3

    #: The requested operation is not allowed in this context by the protocol
    #: specification.
    ILLEGAL_OPERATION = 4

    #: The packet was received from an unexpected source address or port.
    UNKNOWN_TRANSFER_ID = 5

    #: File does already exist and is not overwritten (for write requests).
    FILE_ALREADY_EXISTS = 6

    #: The specified user is not known by this server (for write requests using
    #: the mail mode).
    NO_SUCH_USER = 7

    @staticmethod
    def from_bytes(data: bytes, offset: int = 0) -> 'ErrorCode':
        """
        Extract the error code from a sequence of bytes. If the sequence
        contains less than offset plus two bytes or the two bytes do not
        represent a valid error code, an exception is thrown.

        :param data:
            sequence of bytes that contains the error code.
        :param offset:
            offset into the sequence of bytes. Default is zero (read from the
            start of the sequence).
        """
        (error_code_num,) = struct.unpack_from('!H', data, offset)
        return Opcode(error_code_num)

    def to_bytes(self) -> bytes:
        """
        Return a byte buffer that contains the two bytes that represent this
        error code.
        """
        return struct.pack('!H', self.value)


@enum.unique
class Opcode(enum.IntEnum):
    """
    Code identifying the type of of a TFTP packet.
    """

    #: Client request for reading a file.
    READ_REQUEST = 1

    #: Client request for writing a file.
    WRITE_REQUEST = 2

    #: Data transfer from the server to the client (read) or from the client to
    #: the server (write).
    DATA = 3

    #: Acknowledgement of a received ``DATA`` packet.
    ACK = 4

    #: Error message.
    ERROR = 5

    #: Acknowledgement of supported options (send from the server to the client
    #: as the first response to a request specifying supported options).
    OPTIONS_ACK = 6

    @staticmethod
    def from_bytes(data: bytes, offset: int = 0) -> 'Opcode':
        """
        Extract the opcode from a sequence of bytes. If the sequence contains
        less than offset plus two bytes or the two bytes do not represent a
        valid opcode, an exception is thrown.

        :param data:
            sequence of bytes that contains the opcode.
        :param offset:
            offset into the sequence of bytes. Default is zero (read from the
            start of the sequence).
        :return:
            ``Opcode`` represented by the two bytes at the specified ``offset``.
        """
        (opcode_num,) = struct.unpack_from('!H', data, offset)
        return Opcode(opcode_num)

    def to_bytes(self) -> bytes:
        """
        Return a byte buffer that contains the two bytes that represent this
        opcode.
        """
        return struct.pack('!H', self.value)


@enum.unique
class TransferMode(enum.IntEnum):
    """
    Transfer mode that can be requested by a client.
    """

    #: Netascii transfer mode. In this mode, all line breaks are converted to
    #: CR LF before sending them over the wire.
    NETASCII = 1

    #: Binary transfer mode. In this mode, bytes are sent without any
    #: conversion.
    OCTET = 2

    #: Deprecated mail transfer mode. This mode could be used by clients to
    #: write a file that would then be sent to a user by e-mail.
    MAIL = 3

    @staticmethod
    def from_str(mode: str) -> 'TransferMode':
        """
        Returns the transfer mode that is equivalent to the specified string.
        The string is not case sensitive and must be one of the three strings
        defined in RFC 1350.

        If the string does not represent one of the well-defined transfer modes,
        an exception is raised.

        :param mode:
            string identifying the transfer mode.
        :return:
            TFTP transfer mode represented by the specified string.
        """
        mode_lower = mode.lower()
        if mode_lower == 'netascii':
            return TransferMode.NETASCII
        elif mode_lower == 'octet':
            return TransferMode.OCTET
        elif mode_lower == 'mail':
            return TransferMode.MAIL
        else:
            raise ValueError('Unsupported transfer mode: {0}'.format(mode))

    def to_str(self) -> str:
        """
        Return a string representing this transfer mode.
        """
        if self == TransferMode.NETASCII:
            return 'netascii'
        elif self == TransferMode.OCTET:
            return 'octet'
        elif self == TransferMode.MAIL:
            return 'mail'
        else:
            raise ValueError('Unhandled transfer mode: {0}'.format(self))


def data_packet(block_number: int, data: bytes) -> bytes:
    """
    Create a data packet using the given block number and data.

    :param block_number:
        consecutive number of the block being sent.
    :param data:
        data to be transferred in this block.
    :return:
        byte sequence representing a data packet.
    """
    return Opcode.DATA.to_bytes() + struct.pack('!H', block_number) + data


def decode_ack(data: bytes) -> int:
    """
    Decode a packet that represents an ACK. Throws an exception if the packet
    does not represent a valid ACK.

    The return value is the acknowledged block number.

    :param data:
        data representing the packet.
    :return:
        acknowledged block number specified by the packet.
    """
    if Opcode.from_bytes(data) != Opcode.ACK:
        raise ValueError(
            'Data does not represent an ACK (wrong opcode).')
    if len(data) != 4:
        raise ValueError('Packet does not have the right size for an ACK.')
    (block_number,) = struct.unpack_from('!H', data, 2)
    return block_number


def decode_error(data: bytes) -> typing.Tuple[ErrorCode, str]:
    """
    Decode a packet that represents an error message. This function does not
    raise an exception of the data does not represent a valid error message.
    Instead, it tries to reconstruct as much of it as possible.

    The returned tuple contains the error code and the error message. If the
    error code cannot be decoded, ``None`` is returned instead. If the error
    message cannot be decoded, an empty string is returned instead.

    :param data:
        data representing the packet.
    :return:
        tuple where the first element is the error code and the second element
        is the error message sent by the peer.
    """
    if len(data) < 4:
        return (None, '')
    try:
        error_code = ErrorCode.from_bytes(data, offset=2)
    except struct.error:
        error_code = None
    data_parts = data[4:].split(b'\0')
    if data_parts:
        return (error_code, data_parts[0].decode('ascii', 'ignore'))
    else:
        return (error_code, '')


def decode_read_request(data: bytes) \
        -> typing.Tuple[str, TransferMode, typing.Mapping[str, str]]:
    """
    Decode a packet that represents a read request. Throws an exception if the
    packet does not represent a valid read request.

    The returned tuple contains the requested filename, the requested transfer
    mode and the specified options.

    :param data:
        data representing the packet.
    :return:
        tuple where the first element is the requested filename, the second
        element is the requested transfer-mode, and the thir element are
        additional options that have been specified by the client.
    """
    if Opcode.from_bytes(data) != Opcode.READ_REQUEST:
        raise ValueError(
            'Data does not represent a read request (wrong opcode).')
    data_parts = data[2:].split(b'\0')
    # There must be at least three parts: The filename, the transfer mode, and
    # an empty part because of the terminating null-byte.
    if len(data_parts) < 3:
        raise ValueError('Read request is not well-formed')
    filename = data_parts[0].decode('ascii', 'ignore')
    transfer_mode = TransferMode.from_str(
        data_parts[1].decode('ascii', 'ignore'))
    next_index = 2
    options = {}
    # If there is one more option, there must be three more parts: The first
    # part is for the option name, the second part is for the option value, and
    # the third part is an empty part that is present because of the terminating
    # null-byte.
    while next_index <= len(data_parts) - 3:
        option_name = data_parts[next_index].decode('ascii', 'ignore')
        option_value = data_parts[next_index + 1].decode('ascii', 'ignore')
        options[option_name] = option_value
        next_index += 2
    # If the packet was well-formed, there should be only one empty part left.
    if (next_index != len(data_parts) - 1) or len(data_parts[next_index]):
        raise ValueError('Read request is not well-formed.')
    return (filename, transfer_mode, options)


def error_packet(error_code: ErrorCode, error_message: str = '') -> bytes:
    """
    Create an error packet using the given error code and message string.

    :param error_code:
        code that indicates the kind of error.
    :param error_message:
        optional error message.
    :return:
        sequence of bytes representing the error packet.
    """
    return (Opcode.ERROR.to_bytes() + error_code.to_bytes()
            + error_message.encode('ascii') + b'\0')


def options_ack_packet(options: typing.Mapping[str, str]) -> bytes:
    """
    Create a packet acknowledging options.

    :param options:
        options that shall be acknowledged. Options are mappings from
        option name strings to value strings. Option names must be non-empty
        strings and there must be at least one option present.
    :return:
        sequence of bytes representing the options acknowledgement packet.
    """
    if not options:
        raise ValueError('The options mapping must not be empty.')
    data = Opcode.OPTIONS_ACK.to_bytes()
    for (name, value) in options.items():
        data += name.encode('ascii') + b'\0'
        data += value.encode('ascii') + b'\0'
    return data
