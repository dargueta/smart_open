"""Support for implementing plugins.

Implementing a Plugin
=====================

.. todo:: Finish
"""

from __future__ import absolute_import

import abc
import threading
import typing
import warnings
from typing import MutableMapping

import attr
import pkg_resources
import pluggy
import six


if typing.TYPE_CHECKING:
    from typing import Iterator
    from typing import List
    from typing import Tuple
    from smart_open.smart_open_lib import Uri
    from smart_open.io_utils import IOMode


ENTRY_POINT = "smart_open"
"""The name of the first half of the entry point we're using for plugins."""

_protocol_hookspec = pluggy.HookspecMarker("smart_open.protocol")
_compression_hookspec = pluggy.HookspecMarker("smart_open.compression")

protocol_hook = pluggy.HookimplMarker("smart_open.protocol")
compression_hook = pluggy.HookimplMarker("smart_open.compression")


class SmartOpenIOPluginBase(abc.ABC):
    """The base class for all plugins."""

    @abc.abstractmethod
    def recognizes(self, uri):
        # type: (Uri) -> bool
        """Can this plugin handle the resource specified by the URI?"""

    @abc.abstractmethod
    def supports_read(self, protocol):
        # type: (str) -> bool
        """Does this plugin support reading operations for the given protocol?

        Most plugins will hard-code this method to return either True or False.

        Parameters
        ----------
        protocol: str
            A protocol string. Guaranteed to be one of the strings returned by
            :meth:`recognized_protocols`.

        Returns
        -------
        A boolean indicating if this plugin supports read operations using the given
        protocol.
        """

    @abc.abstractmethod
    def supports_write(self, protocol):
        # type: (str) -> bool
        """Does this plugin support writing operations for the given protocol?

        Most plugins will hard-code this method to return either True or False.

        Parameters
        ----------
        protocol: str
            A protocol string. Guaranteed to be one of the strings returned by
            :meth:`recognized_protocols`.

        Returns
        -------
        A boolean indicating if this plugin supports write operations using the given
        protocol.
        """

    @abc.abstractmethod
    def supports_readwrite(self, protocol):
        """Does this protocol support reading and writing on the same stream?"""


class SmartOpenProtocolPlugin(SmartOpenIOPluginBase):
    """Base class for all plugins implementing a file system protocol."""

    @abc.abstractmethod
    def supports_create(self, protocol):
        # type: (str) -> bool
        """Does this plugin support creating files using the given protocol?

        Most plugins will hard-code this method to return either True or False.

        Parameters
        ----------
        protocol: str
            A protocol string. Guaranteed to be one of the strings returned by
            :meth:`recognized_protocols`.

        Returns
        -------
        A boolean indicating if this plugin supports creating files using the
        given protocol.
        """

    @abc.abstractmethod
    def supports_exclusive_create(self, protocol):
        # type: (str) -> bool
        """Does this plugin support exclusive creation of files for the given
        protocol?

        This is used to query the plugin's support for the "x" flag in I/O mode strings.
        Most plugins will hard-code this to return either True or False.

        Parameters
        ----------
        protocol: str
            A protocol string. Guaranteed to be one of the strings returned by
            :meth:`recognized_protocols`.

        Returns
        -------
        A boolean indicating if this plugin supports exclusive creation of files using
        the given protocol.
        """

    @abc.abstractmethod
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
        Additional implementation-specific arguments can be passed to subclasses
        implementing a protocol. ``smart_open`` ignores anything it doesn't recognize
        and passes it through unmodified to the plugin.

        Returns
        -------
        A file-like object opened in binary mode.
        """


class SmartOpenCompressionPlugin(abc.ABC):
    """Base class for all plugins implementing a compression codec."""

    def supports_text_mode(self, uri):
        # type: (Uri) -> bool
        """Does this plugin support text mode natively for the given resource?

        Most plugins will hard-code this to return True or False.
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
    The full import path to the module where possible, followed by a colon, and the name
    of the class. On Python 3 this will be the fully-qualified name of the class in case
    it's nested. (Python 2 doesn't support that unfortunately.)
    """
    return klass.__module__ + ":" + getattr(klass, "__qualname__", klass.__name__)


class PluginConflictWarning(UserWarning):
    """This plugin implements a protocol or compression algorithm that another plugin
    already implements.

    Parameters
    ----------
    protocol: str
        The name of the plugin that has the conflicting implementations.
    plugin_kind: str
        The kind of plugin, like "compression codec". Used only in making a pretty error
        message.
    existing_class: type
        The class (not instance!) implementing the plugin.
    conflicting_class: type
        The class (not instance!) that conflicts with the existing implementation.
    """

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


class NoSuchPluginError(Exception):
    """The requested plugin doesn't exist.

    Parameters
    ----------
    name: str
        The name of the plugin.
    entry_point: str
        The full entry point name.
    """

    def __init__(self, name, entry_point):
        super(NoSuchPluginError, self).__init__(
            "No plugin named %r was found for entry point %r." % (name, entry_point)
        )
        self.name = name
        self.entry_point = entry_point


def discover_plugins(namespace, plugin_kind):
    # type: (str, str) -> MutableMapping[str, SmartOpenIOPluginBase]
    """Load all plugins under the given namespace in the smart_open entry point.

    Parameters
    ----------
    namespace: str
        The namespace under the smart_open entry point to search for plugins. It should
        be a valid Python identifier.

    plugin_kind: str
        A human-readable string indicating the kind of plugin this function is loading,
        e.g. "protocol" or "compression codec". Only used in error messages.

    Returns
    -------
    A dictionary mapping the plugin names to the initialized implementation objects.
    """
    unloaded_plugins = {}

    for entry_point in pkg_resources.iter_entry_points(ENTRY_POINT + "." + namespace):
        name = entry_point.name
        plugin_class = entry_point.load()

        if entry_point.name not in unloaded_plugins:
            unloaded_plugins[name] = plugin_class
        else:
            # Found a plugin for a protocol or compression algorithm another plugin
            # already implements. Issue a warning and ignore the plugin we just found.
            warnings.warn(
                PluginConflictWarning(
                    entry_point.name, plugin_kind, unloaded_plugins[name], plugin_class
                )
            )

    return {
        name: plugin_class() for name, plugin_class in six.iteritems(unloaded_plugins)
    }


@attr.s
class PluginRegistry(object):
    """A thread-safe registry for dynamically accessing plugins.

    Parameters
    ----------

    namespace: str
        The namespace under the smart_open entry point to search for plugins.
    plugin_type: str
        A human-readable string indicating the type of plugin this is storing, e.g.
        "compression codec" or "file access protocol". Only used in error messages;
        nouns should be singular to grammatically match the messages they're used in.

    Attributes
    ----------

    _registry: dict
        A mapping of plugin names to their initialized implementations. You are *highly*
        recommended to use :meth:`get_plugin` instead of accessing this directly, as
        that acquires a lock first to make this thread-safe.
    _lock: threading.RLock
        The thread lock used to protect access to this registry.
    """

    namespace = attr.ib(type=str)
    plugin_type = attr.ib(type=str)
    _registry = attr.ib(type=MutableMapping[str, SmartOpenIOPluginBase], default=None)
    _lock = attr.ib(type=threading.Lock, factory=threading.RLock)

    def load_registered_plugins(self, force=False):
        # type: (bool) -> None
        """Load all plugins registered for this registry's entry point.

        Does nothing if plugins are already loaded unless ``force`` is True.

        Parameters
        ----------
        force: bool
            Reload all plugins even if they've already been loaded. Useful only if more
            plugins have been added manually and the registry needs to know about it.
        """
        with self._lock:
            if self._registry is None or force:
                self._registry = discover_plugins(self.namespace, self.plugin_type)

    def get_plugin(self, plugin_name):
        # type: (str) -> SmartOpenIOPluginBase
        """Retrieve a plugin with the given name.

        Parameters
        ----------
        plugin_name: str
            The name of the plugin to retrieve.

        Raises
        ------
        smart_open.plugins.NoSuchPluginError: The named plugin was not found.
        """
        with self._lock:
            self.load_registered_plugins()
            if plugin_name not in self._registry:
                raise NoSuchPluginError(plugin_name, self.namespace)
            return self._registry[plugin_name]

    def has_plugin(self, plugin_name):
        # type: (str) -> bool
        """Does this registry have a plugin with the given name?

        Parameters
        ----------
        plugin_name: str
            The name of the plugin to query for.

        Returns
        -------
        A boolean indicating if the plugin is present.

        .. note::

            In a multithreading environment, to avoid `TOCTOU bugs`_ consider using
            :meth:`.get_plugin` directly and catching :class:`NoSuchPluginError` than
            using this.

        .. _TOCTOU bugs: https://en.wikipedia.org/wiki/Time-of-check_to_time-of-use
        """
        with self._lock:
            self.load_registered_plugins()
            return plugin_name in self._registry

    def list_plugin_names(self):
        # type: () -> List[str]
        """Get a list of the plugins in the registry."""
        with self._lock:
            self.load_registered_plugins()
            return list(self._registry)

    def iter_plugins(self):
        # type: () -> Iterator[Tuple[str, SmartOpenIOPluginBase]]
        """Return an iterator over tuples of the plugin name and object.

        Consider this an equivalent to dict.iteritems() on Python 2 or dict.items() on
        Python 3.
        """
        with self._lock:
            self.load_registered_plugins()
            for pair in six.iteritems(self._registry):
                yield pair


COMPRESSION_PLUGINS = PluginRegistry("compression", "compression codec")
"""The registry containing all implementations of compression plugins."""

PROTOCOL_PLUGINS = PluginRegistry("protocol", "file system protocol")
"""The registry containing all implementations of file protocol plugins."""
