from __future__ import absolute_import

import typing
import warnings

import pkg_resources
import pluggy
import six


if typing.TYPE_CHECKING:
    from typing import Any
    from typing import BinaryIO
    from typing import Dict
    from smart_open.smart_open_lib import Uri
    from smart_open.io_utils import IOMode


_hookspec = pluggy.HookspecMarker("smart_open")
hook = pluggy.HookimplMarker("smart_open")


class SmartOpenFileSystemPlugin(object):
    """Base class for all plugins implementing a file system protocol."""

    @_hookspec
    def supports_read(self, protocol):
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

    @_hookspec
    def supports_write(self, protocol):
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

    @_hookspec
    def supports_create(self, protocol):
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

    @_hookspec
    def supports_exclusive_create(self, protocol):
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

    @_hookspec
    def open_binary_stream(self, uri, mode, buffering=-1, **kwargs):
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

    @_hookspec
    def supports_codec(self, uri, stream):
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


def class_name(klass):
    # type: (type) -> str
    """Get the full import path of a class as defined in the entry point providing it.

    Parameters
    ----------

    klass: type
        Any class object. Not an instance of the class!

    Returns
    -------

    The full import path to the module where possible, followed by a colon, and
    the name of the class. On Python 3 this will be the fully-qualified name of
    the class in case it's nested.
    """
    return klass.__module__ + ":" + getattr(klass, "__qualname__", klass.__name__)


class PluginConflictWarning(UserWarning):
    """This plugin implements a protocol or compression algorithm that another plugin
    already implements."""

    def __init__(self, protocol, plugin_kind, existing_class, conflicting_class):
        # type: (str, str, type, type) -> None
        super(PluginConflictWarning, self).__init__(
            "%s %r already implemented by plugin %s; ignoring plugin %s"
            % (
                plugin_kind.capitalize(),
                protocol,
                class_name(existing_class),
                class_name(conflicting_class),
            )
        )


def discover_plugins(entry_point, plugin_kind):
    # type: (str, str) -> Dict[str, Any]
    """

    Parameters
    ----------

    entry_point: str
        The second half of the entry point namespace. It should be a valid Python
        identifier.

    plugin_kind: str
        A human-readable string indicating the kind of plugin this function is loading,
        e.g. "protocol" or "compression codec". Only used in error messages.

    Returns
    -------

    """
    unloaded_plugins = {}

    for entry_point in pkg_resources.iter_entry_points("smart_open." + entry_point):
        name = entry_point.name
        plugin_class = entry_point.load()

        if entry_point.name in unloaded_plugins:
            warnings.warn(
                PluginConflictWarning(
                    entry_point.name, plugin_kind, unloaded_plugins[name], plugin_class
                )
            )
            continue
        unloaded_plugins[name] = plugin_class

    return {
        name: plugin_class() for name, plugin_class in six.iteritems(unloaded_plugins)
    }
