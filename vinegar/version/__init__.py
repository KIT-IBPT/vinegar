"""
Provides the version of the Vinegar distribution.
"""

# For a beta version, we use a negative offset for the last component of the
# version number. This has two consequences: First, a beta version always
# compares less than the final version. Second, we can detect this when
# generating the version string and insert a "b" in the string. For example, a
# version of (1, 0, 1 + BETA_VERSION_OFFSET) will result in the version string
# "1.0b1".
BETA_VERSION_OFFSET = -1000

#: Version (as a tuple).
#:
#: When changing the version here, it also has to be changed in
#: debian/changelog.
VERSION = (2, 0, 1 + BETA_VERSION_OFFSET)


def _version_string():
    """
    Generate the version string based on the version number.
    """
    version_string = ""
    for component in VERSION:
        if component >= 0:
            version_string += f".{component}"
        else:
            # We assume that there is only one negative component in the
            # version number.
            version_string += f"b{component - BETA_VERSION_OFFSET}"
    return version_string[1:]


#: Version (as a string)
VERSION_STRING = _version_string()
