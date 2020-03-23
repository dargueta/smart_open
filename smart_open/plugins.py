from __future__ import absolute_import

import pluggy


_protocol_hookspec = pluggy.HookspecMarker("smart_open_protocol")
smart_open_protocol_hook = pluggy.HookimplMarker("smart_open_protocol")

_compression_hookspec = pluggy.HookspecMarker("smart_open_compression")
smart_open_compression_hook = pluggy.HookimplMarker("smart_open_compression")


class SmartOpenFileSystemPlugin(object):
    """Base class for all plugins implementing a file system protocol."""

    @_protocol_hookspec
    def smart_open_implemented_protocols(self):
        """Declare what protocols this plugin implements.

        Returns
        -------

        A string or iterable of strings naming the URI protocols that this plugin
        implements.
        """

    @_protocol_hookspec
    def smart_open_supports_read(self, protocol):
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
        """Open the given resource and return a binary file stream.

        Parameters
        ----------

        uri: smart_open.smart_open_lib.Uri
            The parsed URL to open.
        mode: smart_open.io_utils.IOMode
            The I/O mode to open the stream in.
        buffering: int, optional
            Mimicks built-in open parameter of the same name.

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
    def smart_open_implemented_compression(self):
        """Declare what compression algorithms this plugin supports."""
