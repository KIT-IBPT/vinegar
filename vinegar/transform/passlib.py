"""
Transformations for encrypting passwords.

The transformations provided by this module use the ``passlib`` library, so they
are only available if that library is installed.
"""

import passlib.hash


def hash(plaintext: str, method: str = 'sha512_crypt', **kwargs) -> str:
    """
    Hash a password using one of the methods supported by ``passlib.hash``.

    .. note::

        ``passlib`` may use different default parameters when hashing a
        password. For example, the ``sha512_crypt`` will use a higher number of
        of rounds than the default value used by most Linux system's ``crypt``.
        If you want to use the same parameters, you have to set the keyword
        argument ``rounds`` to 5000.

    Usage example (when specified in a YAML configuration file):

    .. code-block:: yaml

        transform:
            - passlib.hash:
                plaintext: "mypassword"
                method: sha256_crypt
                rounds: 5000

    :param plaintext:
        password string to be enrcypted / hashed.
    :param method:
        hash method to be used. This must be a string that identifies one of the
        methods that are supported passlib. For example, if ``method``
        is ``sha256_crypt``, ``passlib.hash.sha256_crypt`` is going to be used.
        The default is ``sha512_crypt``.
    :param kwargs:
        additional keyword arguments that are passed to the ``hash`` or
        ``encrypt`` method of the hashing object specified by ``method``.
    :return:
        encrypted (hashed) password.
    """
    hasher = getattr(passlib.hash, method)
    # Since version 1.7, passlib expects the additional parameters to be passed
    # to the using method instead of the hash method, but that method does not
    # exist in older versions.
    try:
        hasher = hasher.using(**kwargs)
        kwargs = {}
    except AttributeError:
        pass
    # The hash method is only available in recent versions of passlib. We want
    # to support older versions, so we fall back to encrypt if hash is not
    # available. We do not always use encrypt because this will cause a warning
    # in version 1.7 and an error in version 2.x.
    try:
        return hasher.hash(plaintext, **kwargs)
    except AttributeError:
        return hasher.encrypt(plaintext, **kwargs)
