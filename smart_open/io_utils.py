from __future__ import absolute_import

import os

import six


@six.python_2_unicode_compatible
class IOMode(object):
    def __init__(self, mode):
        # type: (str) -> None
        self._mode = self.string_to_flags(mode)
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
        return (self._mode & os.O_RDONLY) or (self._mode & os.O_RDWR) != 0

    @property
    def write(self):
        # type: () -> bool
        return (self._mode & os.O_WRONLY) or (self._mode & os.O_RDWR) != 0

    @property
    def append(self):
        # type: () -> bool
        return self._mode & os.O_APPEND != 0

    @property
    def create(self):
        # type: () -> bool
        return self._mode & os.O_CREAT != 0

    @property
    def excl(self):
        # type: () -> bool
        return self._mode & os.O_EXCL != 0

    @property
    def truncate(self):
        # type: () -> bool
        return self._mode & os.O_TRUNC != 0

    @staticmethod
    def string_to_flags(string):
        # type: (str) -> int
        """Convert an I/O mode string into integer flags.

        This function does minimal validation, so it's possible to pass in some
        invalid mode strings like "r+x" without getting an exception. Behavior
        for invalid mode strings is *undefined*.

        Parameters
        ----------

        string: str
            The mode string to convert to integer flags.

        Returns
        -------

        The mode string, converted to a Unix-style integer bitfield. On non-Windows
        systems there is no way to indicate whether the mode is binary or text;
        you must do this yourself by examining ``string`` and seeing if "b" or
        "t" is in there.
        """
        # O_BINARY and O_TEXT are only supported on Windows. We'll set them if
        # possible on the flags, or fall back to 0 if they're missing. There's
        # no way to indicate binary vs text mode in flags on *NIX systems.
        if "b" in string:
            flags = getattr(os, "O_BINARY", 0)
        else:
            flags = getattr(os, "O_TEXT", 0)

        if "r" in string:
            if "+" in string:
                flags |= os.O_RDWR
            else:
                flags |= os.O_RDONLY
        elif "w" in string:
            if "+" in string:
                flags |= os.O_RDWR | os.O_CREAT | os.O_TRUNC
            else:
                flags |= os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        elif "a" in string:
            if "+" in string:
                flags |= os.O_APPEND | os.O_RDWR | os.O_CREAT
            else:
                flags |= os.O_APPEND | os.O_WRONLY | os.O_CREAT
        else:
            raise ValueError("Invalid I/O mode string: " + repr(string))

        if "x" in string:
            flags |= os.O_EXCL

        return flags

    @staticmethod
    def flags_to_string(flags, binary=False):
        # type: (int, bool) -> str
        """Convert I/O mode flags into a standardized mode string."""
        # TODO (dargueta): There's gotta be a cleaner way of doing this.
        if flags & (os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            mode = "w+"
        elif flags & (os.O_WRONLY | os.O_CREAT | os.O_TRUNC):
            mode = "w"
        elif flags & (os.O_APPEND | os.O_RDWR | os.O_CREAT):
            mode = "a+"
        elif flags & os.O_RDWR:
            mode = "r+"
        elif flags & os.O_RDONLY:
            mode = "r"
        else:
            raise ValueError("Don't know how to convert flags: %#X" % flags)

        if flags & os.O_EXCL:
            mode += "x"

        if (flags & getattr(os, "O_BINARY", 0)) or binary is True:
            mode += "b"

        return mode

    def __int__(self):
        # type: () -> int
        return self.string_to_flags(self._mode_string)

    def __str__(self):
        # type: () -> str
        return self._mode_string
