from __future__ import absolute_import

import pluggy
import typing


if typing.TYPE_CHECKING:
    from typing import BinaryIO
    from typing import Iterable
    from typing import Iterator
    from typing import Union
    from smart_open.smart_open_lib import Uri
    from smart_open.io_utils import IOMode


_protocol_hookspec = pluggy.HookspecMarker("smart_open_protocol")
protocol_hook = pluggy.HookimplMarker("smart_open_protocol")

_compression_hookspec = pluggy.HookspecMarker("smart_open_compression")
compression_hook = pluggy.HookimplMarker("smart_open_compression")


class SmartOpenFileSystemPlugin(object):
    """Base class for all plugins implementing a file system protocol."""

    @_protocol_hookspec
    def smart_open_implemented_protocols(self):
        # type: () -> Union[str, Iterable[str]]
        """Declare what protocols this plugin implements.

        Returns
        -------

        A string or iterable of strings naming the URI protocols that this plugin
        implements.
        """

    @_protocol_hookspec
    def smart_open_supports_read(self, protocol):
        # type: (str) -> bool
        """Does this plugin support reading operations for the given protocol?

        Most plugins will hard-code this method to return either True or False.

        Parameters
        ----------

        protocol: str
            A protocol string. Guaranteed to be one of the strings returned by
            :meth:`smart_open_implements_protocols`.

        Returns
        -------

        A boolean indicating if this plugin supports read operations using the
        given protocol.
        """

    @_protocol_hookspec
    def smart_open_supports_write(self, protocol):
        # type: (str) -> bool
        """Does this plugin support writing operations for the given protocol?

        Most plugins will hard-code this method to return either True or False.

        Parameters
        ----------

        protocol: str
            A protocol string. Guaranteed to be one of the strings returned by
            :meth:`smart_open_implements_protocols`.

        Returns
        -------

        A boolean indicating if this plugin supports write operations using the
        given protocol.
        """

    @_protocol_hookspec
    def smart_open_supports_create(self, protocol):
        # type: (str) -> bool
        """Does this plugin support creating files using the given protocol?

        Most plugins will hard-code this method to return either True or False.

        Parameters
        ----------

        protocol: str
            A protocol string. Guaranteed to be one of the strings returned by
            :meth:`smart_open_implements_protocols`.

        Returns
        -------

        A boolean indicating if this plugin supports creating files using the
        given protocol.
        """

    @_protocol_hookspec
    def smart_open_supports_exclusive_create(self, protocol):
        # type: (str) -> bool
        """Does this plugin support exclusive creation of files for the given
        protocol?

        This is used to query the plugin's support for the "x" flag in I/O mode
        strings. Most plugins will hard-code this to return either True or False.

        Parameters
        ----------

        protocol: str
            A protocol string. Guaranteed to be one of the strings returned by
            :meth:`smart_open_implements_protocols`.

        Returns
        -------

        A boolean indicating if this plugin supports exclusive creation of files
        using the given protocol.
        """

    @_protocol_hookspec
    def smart_open_open_binary_stream(self, uri, mode, buffering=-1, **kwargs):
        # type: (Uri, IOMode, int, ...) -> bool
        """Open the given resource and return a binary file stream.

        Parameters
        ----------

        uri: smart_open.smart_open_lib.Uri
            The parsed URL to open.
        mode: smart_open.io_utils.IOMode
            The I/O mode to open the stream in.
        buffering: int, optional
            Mimics built-in open parameter of the same name.

        Other Parameters
        ----------------

        Additional implementation-specific arguments can be passed directly to
        subclasses implementing a protocol. ``smart_open`` ignores anything it
        doesn't recognize.

        Returns
        -------

        A file-like object opened in binary mode.
        """


class SmartOpenCompressionPlugin(object):
    """Base class for all plugins implementing a compression codec."""

    @_compression_hookspec
    def smart_open_implemented_compression_algorithms(self):
        # type: () -> Union[str, Iterable[str]]
        """Declare what compression algorithms this plugin supports.

        Returns
        -------

        A string or iterable of strings of the file extensions that this plugin
        recognizes.
        """

    @_compression_hookspec
    def smart_open_supports_codec(self, uri, stream):
        # type: (Uri, BinaryIO) -> bool
        """Determine if this plugin supports the compression codec for the given
        URI and/or file stream.

        Parameters
        ----------

        uri: smart_open.smart_open_lib.Uri
            The URI that smart_open will open.
        stream: BinaryIO
            The opened binary stream for the file that may need decompression.
            This is solely provided for checking magic numbers in case the
            extension doesn't provide enough information.

        Returns
        -------

        A boolean indicating if this plugin supports the compression codec the
        file is compressed with.
        """

    @compression_hook(hookwrapper=True)
    def smart_open_supports_codec(self, uri, stream):
        # type: (Uri, BinaryIO) -> Iterator[None]
        """A wrapper for the :meth:`smart_open_supports_codec` hook to ensure the
        stream pointer isn't moved after an implementation returns.
        """
        try:
            initial_position = stream.tell()
        except AttributeError:
            # Stream doesn't support tell() so we have no way of resetting the
            # stream pointer to where it was once the plugins return.
            yield
            return

        try:
            yield
        finally:
            stream.seek(initial_position)
