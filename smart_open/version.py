import pkg_resources as _pkgr

# Parsed version object extracted from the package's metadata
__parsed_version = _pkgr.get_distribution("smart_open").parsed_version

__version__ = str(__parsed_version)
"""A string representing the full version of this distribution of smart_open."""

__version_info__ = tuple(int(p) for p in __parsed_version.base_version.split("."))
"""A three-element tuple with the major, minor, and patch of smart_open, as integers."""
