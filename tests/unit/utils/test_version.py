"""
Tests for `vinegar.utils.version`.
"""

import os.path
import pathlib
import time
import unittest

from tempfile import TemporaryDirectory

from vinegar.utils.version import (
    aggregate_version,
    version_for_file_path,
    version_for_str,
)


class TestVersionModule(unittest.TestCase):
    """
    Tests for the `vinegar.utils.version`.
    """

    def test_aggregate_version(self):
        """
        Test that an aggregate version can be calculated using
        `aggregate_version`.
        """
        # Generated version strings should not be empty and they should not
        # match for different input, even though the latter one is not a strict
        # requirement because due to the use of hashes, there could be
        # accidental collisions.
        version1 = aggregate_version(["1", "2", "3"])
        self.assertTrue(len(version1) > 0)
        version2 = aggregate_version(["1", "2"])
        self.assertTrue(len(version2) > 0)
        self.assertNotEqual(version1, version2)
        version3 = aggregate_version(["4", "2", "3"])
        self.assertTrue(len(version3) > 0)
        self.assertNotEqual(version1, version3)
        self.assertNotEqual(version2, version3)

    def test_version_for_file_path(self):
        """
        Test the `version_for_file_path` function.
        """
        with TemporaryDirectory() as tmpdir:
            test_file_path = os.path.join(tmpdir, "test")
            # First, we test that generating a version number for a file, that
            # does not exist, does not result in an exception.
            version1 = version_for_file_path(test_file_path)
            self.assertTrue(len(version1) > 0)
            # The same thing should work when using a path-like object.
            version2 = version_for_file_path(pathlib.Path(tmpdir) / "test")
            self.assertTrue(len(version2) > 0)
            # In fact both ways should result in the same version number.
            self.assertEqual(version1, version2)
            # Even getting a version number for a directory should not result
            # in an exception
            version3 = version_for_file_path(tmpdir)
            self.assertTrue(len(version3) > 0)
            # Now we write to the file. In fact, we just open it for writing
            # because the content does not matter, we just care about creating
            # it.
            with open(test_file_path, mode="w"):
                pass
            # The version number should have changed now.
            version4 = version_for_file_path(test_file_path)
            self.assertTrue(len(version4) > 0)
            self.assertNotEqual(version1, version4)
            # We do the same thing again. We actually write something because
            # simply opening a file for writing might not be enough to update
            # its modified time. We also sleep for a short amount of time
            # because the precision of the time stamp stored in the file system
            # might be limited.
            # We actually try several times with increasing sleep times. On
            # systems, where the time stamp is very precise, the test finishes
            # quickly, on other ones it takes a bit longer.
            sleep_time = 0.01
            while sleep_time < 3.0:
                with open(test_file_path, mode="w") as file:
                    file.write("test")
                version5 = version_for_file_path(test_file_path)
                if version5 != version4:
                    break
                time.sleep(sleep_time)
                sleep_time *= 2
            self.assertTrue(len(version5) > 0)
            self.assertNotEqual(version1, version5)
            self.assertNotEqual(version4, version5)

    def test_version_for_str(self):
        """
        Test the `version_for_str` function.
        """
        # Getting a version string should even work for an empty string.
        version1 = version_for_str("")
        self.assertTrue(len(version1) > 0)
        # Different strings should result in different versions.
        version2 = version_for_str("abc")
        self.assertTrue(len(version2) > 0)
        self.assertNotEqual(version1, version2)
        version3 = version_for_str("123")
        self.assertTrue(len(version3) > 0)
        self.assertNotEqual(version1, version3)
        self.assertNotEqual(version2, version3)
        # Same strings, however, should result in identical versions.
        version4 = version_for_str("123")
        self.assertTrue(len(version4) > 0)
        self.assertEqual(version3, version4)
