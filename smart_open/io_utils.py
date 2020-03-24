from __future__ import absolute_import

import os
import posixpath

import six

from smart_open import plugins


_FLAGS_RONLY = os.O_RDONLY
_FLAGS_RPLUS = os.O_RDWR
_FLAGS_WONLY = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
_FLAGS_WPLUS = os.O_RDWR | os.O_CREAT | os.O_TRUNC
_FLAGS_AONLY = os.O_APPEND | os.O_WRONLY | os.O_CREAT
_FLAGS_APLUS = os.O_APPEND | os.O_RDWR | os.O_CREAT


def io_mode_string_to_flags(string):
    # type: (str) -> int
    """Convert an I/O mode string into integer flags.

    This function only does minimal validation to ensure the mode string is unambiguous.
    Thus, it's possible to pass in some invalid strings like "r+x" without getting an
    exception. Behavior for invalid mode strings is *undefined*.

    Parameters
    ----------
    string: str
        The mode string to convert to integer flags. Any valid mode string handled by
        the built-in :func:`open` will be accepted.

    Returns
    -------
    The mode string, converted to a Unix-style integer bitfield. On non-Windows
    systems there is no way to indicate whether the mode is binary or text;
    you must do this yourself by examining ``string`` and seeing if "b" or
    "t" is in there.

    Raises
    ------
    ValueError: The mode string is invalid.
    """
    # O_BINARY and O_TEXT are only supported on Windows. We'll set them if possible on
    # the flags, or fall back to 0 if they're missing. There's no way to indicate binary
    # vs text mode in flags on *NIX systems.
    if "b" in string:
        if "U" in string or "t" in string:
            raise ValueError(
                "Mode string specifies binary and text mode at the same time: "
                + repr(string)
            )
        flags = getattr(os, "O_BINARY", 0)
    else:
        flags = getattr(os, "O_TEXT", 0)

    if string[0] == "r":
        if "+" in string:
            flags |= _FLAGS_RPLUS
        else:
            flags |= _FLAGS_RONLY
    elif string[0] == "w":
        if "+" in string:
            flags |= _FLAGS_WPLUS
        else:
            flags |= _FLAGS_WONLY
    elif string[0] == "a":
        if "+" in string:
            flags |= _FLAGS_APLUS
        else:
            flags |= _FLAGS_AONLY
    else:
        raise ValueError(
            "Mode string must have 'r', 'w', or 'a' as the first character: "
            + repr(string)
        )

    if "x" in string:
        flags |= os.O_EXCL

    return flags


def io_mode_flags_to_string(flags, binary=False):
    # type: (int, bool) -> str
    """Convert I/O mode flags into a string.

    Parameters
    ----------

    flags: int
        The I/O mode flags to convert.
    binary: bool
        A boolean indicating if the file is in binary mode or not. Only Windows
        provides explicit flags to indicate whether a file should be opened in
        binary or text mode, which is why we need this. The argument is ignored
        if either :data:`os.O_BINARY` or :data:`os.O_TEXT` is set on ``flags``.

    Returns
    -------

    An I/O mode string.
    """
    # TODO (dargueta): There's gotta be a cleaner way of doing this.
    if flags & _FLAGS_WPLUS == _FLAGS_WPLUS:
        mode = "w+"
    elif flags & _FLAGS_WONLY == _FLAGS_WONLY:
        mode = "w"
    elif flags & _FLAGS_APLUS == _FLAGS_APLUS:
        mode = "a+"
    elif flags & _FLAGS_RPLUS == _FLAGS_RPLUS:
        mode = "r+"
    elif flags & _FLAGS_RONLY == _FLAGS_RONLY:
        mode = "r"
    else:
        raise ValueError("Don't know how to convert flags: %#X" % flags)

    if flags & os.O_EXCL:
        mode += "x"

    if (flags & getattr(os, "O_BINARY", 0)) or binary:
        mode += "b"

    return mode


@six.python_2_unicode_compatible
class IOMode(object):
    """An object representation of an I/O mode string.

    Parameters
    ----------

    mode: str
        An I/O mode string such as passed to Python's built-in ``open()`` function.
    """

    def __init__(self, mode):
        # type: (str) -> None
        self._flags = io_mode_string_to_flags(mode)
        self._is_binary = "b" in mode

    @property
    def text(self):
        # type: () -> bool
        """Is this text mode?"""
        return not self._is_binary

    @property
    def binary(self):
        # type: () -> bool
        """Is this binary mode?"""
        return self._is_binary

    @property
    def read(self):
        # type: () -> bool
        """Is reading from this stream allowed?"""
        return (self._flags & os.O_RDONLY) or (self._flags & os.O_RDWR) != 0

    @property
    def write(self):
        # type: () -> bool
        """Is writing to this stream allowed?"""
        return (self._flags & os.O_WRONLY) or (self._flags & os.O_RDWR) != 0

    @property
    def append(self):
        # type: () -> bool
        """Was the stream opened in append mode?"""
        return self._flags & os.O_APPEND != 0

    @property
    def create(self):
        # type: () -> bool
        return self._flags & os.O_CREAT != 0

    @property
    def excl(self):
        # type: () -> bool
        """When creating a file, is the file to be created exclusively?

        If True, and the file already exists, the code opening the stream must
        throw an exception.
        """
        return self._flags & os.O_EXCL != 0

    @property
    def truncate(self):
        # type: () -> bool
        """Should the file be truncated upon opening?"""
        return self._flags & os.O_TRUNC != 0

    def __int__(self):
        # type: () -> int
        return self._flags

    def __str__(self):
        # type: () -> str
        return io_mode_flags_to_string(self._flags, self._is_binary)


def get_compression_plugin(uri):
    """Guess the compression type used to compress a file using its URI.

    Parameters
    ----------
    uri: smart_open.smart_open_lib.Uri
        The URI of the resource that may be compressed.

    Returns
    -------
    The compression plugin that needs to be used, or ``None`` if the file doesn't seem
    to be compressed based on its name (or no plugin supports that codec).
    """
    extension = posixpath.splitext(uri.uri_path)[-1]
    try:
        return plugins.COMPRESSION_PLUGINS.get_plugin(extension)
    except plugins.NoSuchPluginError:
        return None


def maybe_wrap_binary_stream(uri, io_mode, stream, compression="infer"):
    """Possibly wrap a binary stream with a text stream and/or compressor.

    Parameters
    ----------
    """
