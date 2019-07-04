"""
Tests for `vinegar.tftp.protocol`.
"""

import unittest

from vinegar.tftp.protocol import ErrorCode, Opcode, TransferMode


class TestErrorCode(unittest.TestCase):
    """
    Tests for the `ErrorCode` class.
    """

    def test_from_bytes(self):
        """
        Test the ``~ErrorCode.from_bytes`` method.
        """
        self.assertEqual(
            ErrorCode.NOT_DEFINED, ErrorCode.from_bytes(b'\x00\x00'))
        self.assertEqual(
            ErrorCode.FILE_NOT_FOUND, ErrorCode.from_bytes(b'\x00\x01'))
        self.assertEqual(
            ErrorCode.ACCESS_VIOLATION, ErrorCode.from_bytes(b'\x00\x02'))
        self.assertEqual(
            ErrorCode.DISK_FULL, ErrorCode.from_bytes(b'\x00\x03'))
        self.assertEqual(
            ErrorCode.ILLEGAL_OPERATION, ErrorCode.from_bytes(b'\x00\x04'))
        self.assertEqual(
            ErrorCode.UNKNOWN_TRANSFER_ID, ErrorCode.from_bytes(b'\x00\x05'))
        self.assertEqual(
            ErrorCode.FILE_ALREADY_EXISTS, ErrorCode.from_bytes(b'\x00\x06'))
        self.assertEqual(
            ErrorCode.NO_SUCH_USER, ErrorCode.from_bytes(b'\x00\x07'))
        # An invalid error code should result in an exception.
        with self.assertRaises(ValueError):
            ErrorCode.from_bytes(b'\x00\x08')
        # We should be able to read an error code with an offset.
        self.assertEqual(
            ErrorCode.FILE_ALREADY_EXISTS,
            ErrorCode.from_bytes(b'\x00\x05\x00\x06', 2))

    def test_to_bytes(self):
        """
        Test the ``~ErrorCode.to_bytes`` method.
        """
        self.assertEqual(ErrorCode.NOT_DEFINED.to_bytes(), b'\x00\x00')
        self.assertEqual(ErrorCode.FILE_NOT_FOUND.to_bytes(), b'\x00\x01')
        self.assertEqual(ErrorCode.ACCESS_VIOLATION.to_bytes(), b'\x00\x02')
        self.assertEqual(ErrorCode.DISK_FULL.to_bytes(), b'\x00\x03')
        self.assertEqual(ErrorCode.ILLEGAL_OPERATION.to_bytes(), b'\x00\x04')
        self.assertEqual(ErrorCode.UNKNOWN_TRANSFER_ID.to_bytes(), b'\x00\x05')
        self.assertEqual(ErrorCode.FILE_ALREADY_EXISTS.to_bytes(), b'\x00\x06')
        self.assertEqual(ErrorCode.NO_SUCH_USER.to_bytes(), b'\x00\x07')


class TestOpcode(unittest.TestCase):
    """
    Tests for the `Opcode` class.
    """

    def test_from_bytes(self):
        """
        Test the ``~Opcode.from_bytes`` method.
        """
        self.assertEqual(
            Opcode.READ_REQUEST, ErrorCode.from_bytes(b'\x00\x01'))
        self.assertEqual(
            Opcode.WRITE_REQUEST, ErrorCode.from_bytes(b'\x00\x02'))
        self.assertEqual(
            Opcode.DATA, ErrorCode.from_bytes(b'\x00\x03'))
        self.assertEqual(
            Opcode.ACK, ErrorCode.from_bytes(b'\x00\x04'))
        self.assertEqual(
            Opcode.ERROR, ErrorCode.from_bytes(b'\x00\x05'))
        self.assertEqual(
            Opcode.OPTIONS_ACK, ErrorCode.from_bytes(b'\x00\x06'))
        # An invalid opcode should result in an exception.
        with self.assertRaises(ValueError):
            Opcode.from_bytes(b'\x00\x07')
        # We should be able to read an opcode with an offset.
        self.assertEqual(
            Opcode.READ_REQUEST,
            Opcode.from_bytes(b'\x00\x05\x00\x01', 2))

    def test_to_bytes(self):
        """
        Test the ``~Opcode.to_bytes`` method.
        """
        self.assertEqual(Opcode.READ_REQUEST.to_bytes(), b'\x00\x01')
        self.assertEqual(Opcode.WRITE_REQUEST.to_bytes(), b'\x00\x02')
        self.assertEqual(Opcode.DATA.to_bytes(), b'\x00\x03')
        self.assertEqual(Opcode.ACK.to_bytes(), b'\x00\x04')
        self.assertEqual(Opcode.ERROR.to_bytes(), b'\x00\x05')
        self.assertEqual(Opcode.OPTIONS_ACK.to_bytes(), b'\x00\x06')


class TestTransferMode(unittest.TestCase):
    """
    Tests for the `TransferMode` class.
    """

    def test_from_str(self):
        """
        Test the ``~TransferMode.from_str`` method.
        """
        self.assertEqual(
            TransferMode.NETASCII, TransferMode.from_str('netascii'))
        self.assertEqual(
            TransferMode.NETASCII, TransferMode.from_str('nEtAsCiI'))
        self.assertEqual(
            TransferMode.OCTET, TransferMode.from_str('octet'))
        self.assertEqual(
            TransferMode.OCTET, TransferMode.from_str('OcTET'))
        self.assertEqual(
            TransferMode.MAIL, TransferMode.from_str('mail'))
        self.assertEqual(
            TransferMode.MAIL, TransferMode.from_str('MaiL'))
        # An invalid opcode should result in an exception.
        with self.assertRaises(ValueError):
            TransferMode.from_str('invalid')

    def test_to_bytes(self):
        """
        Test the ``~TransferMode.to_str`` method.
        """
        self.assertEqual(TransferMode.NETASCII.to_str(), 'netascii')
        self.assertEqual(TransferMode.OCTET.to_str(), 'octet')
        self.assertEqual(TransferMode.MAIL.to_str(), 'mail')
