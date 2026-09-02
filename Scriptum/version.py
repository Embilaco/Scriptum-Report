"""The one place the package version is written.

A leaf on purpose: the back ends stamp ``Scriptum {version}`` into every
document's author property, and they may not import the root package to
read it -- the root's ``__init__`` is what imports *them* (lazily), and
the layering test holds every ``_<backend>`` package to rdf/tag/element
plus this module. ``pyproject.toml`` carries the same number; the release
procedure (Distribution.md) bumps both together.
"""

__version__ = "2.2.0"
version = __version__
