"""
Utility functions for calculating version strings.

Version strings provide a simple tool for finding out whether a specific
resource has changed.

Internally, they are calculated using the Murmur 3 hash function (if the `mmh3`
module is available) or the MD5 hash function. Both these hash functions are
designed in a way that accidental collisions are very unlikely.

Due to the nature of hash functions, a collision can never be avoided with
absolute certainty, so version strings should only be used when the risk
associated with using an outdated resource is acceptable.
"""

import os
import pathlib
import sys
import typing


def aggregate_version(versions: typing.Iterable[str]) -> str:
    """
    Calculate an aggregate version from several version strings.

    The aggregate version string is created by calculated a hash over the input
    version numbers. The hash function is chosen so that accidental collisions
    are very unlikely.

    :param versions:
        iterable object that provides ``str`` objects that represent the input
        version strings.
    :return:
        aggregate version string based on the input versions.
    """
    return _hash_str('|'.join(versions))


def version_for_file_path(
        file_path: typing.Union[str, pathlib.PurePath]) -> str:
    """
    Return a version string for a file.

    The returned version string is calculated based on the file path and the
    file's ``ctime`` and ``mtime`` (if the file exists).

    By principle, this function cannot detect when the file content changes
    without changing the ``ctime`` or ``mtime``. This might happen, if the
    ``ctime`` and ``mtime`` are deliberately reset to their old values or if
    the file is changed in rapid succession and the time precision of the
    underlying file-system is not sufficient to detect that.

    :param file_path:
        string or `~pathlib.PurePath` instance that represents the path to the
        file.
    :return:
        version string based on the file's ``ctime`` and ``mtime``.
    """
    if isinstance(file_path, pathlib.PurePath):
        file_path = str(file_path)
    try:
        file_stat = os.stat(file_path)
        file_info = \
            'file_path={0},ctime={1},mtime={2},dev={3},ino={4},size={5}'.format(
                file_path,
                file_stat.st_ctime_ns,
                file_stat.st_mtime_ns,
                file_stat.st_dev,
                file_stat.st_ino,
                file_stat.st_size)
        return _hash_str(file_info)
    except Exception:
        # If we cannot stat the file, we calculate the version based on the
        # file path only. We also encode the exception type, so that a file that
        # cannot be found has a different version string than a file that exists
        # but cannot be read.
        return _hash_str(
            'file_path={0},exception={1}'.format(
                file_path, str(sys.exc_info()[0])))


def version_for_str(data: str) -> str:
    """
    Returns a version string for a string.

    Effectively, this function simply calculates a hash on the string. This has
    the effect that different strings should (typically) result in different
    version strings, unless a hash collision occurs.

    :param data:
        string to be hashed.
    :return:
        hash-based version string.
    """
    return _hash_str(data)


# Murmur3 is about twice as fast as MD5, but it is not available in the core
# Python library. There is a Python-only variant of Murmur3, but that one is
# actually slower than the built-in MD5. For this reason, we only use Murmur3
# if the mmh3 package is available on the system. Otherwise, we use MD5.
try:
    import mmh3

    def _hash_str(data: str):
        return mmh3.hash_bytes(data).hex()

except ImportError:
    import hashlib

    def _hash_str(data: str):
        hasher = hashlib.md5()
        hasher.update(data.encode(errors='ignore'))
        return hasher.hexdigest()
