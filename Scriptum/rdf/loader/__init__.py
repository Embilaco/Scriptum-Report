#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""Reading a YAML report document.

The replacement for the hand-written ``.rdf`` text syntax. The format is
specified in full on the Spatial board *YAML document format - formal rules*;
what follows is only the map of this package.

``dialect``
    PyYAML restricted to the YAML 1.2 core schema, so ``no`` stays a string.
``diagnostics``
    Positions, accumulating errors, and the exception the root document raises.
``nodes``
    The document as a node graph, which is the only place positions and
    duplicate keys are visible.
``document``
    The two document shapes, and the ``_scriptum_`` settings block.
``addresses``
    What an author writes, and the four slots it completes to.
``entries``
    ``_content_`` walked into a tree of containers, markers and fills, with
    includes spliced in place.
``fills``
    A fill's value and its modifiers, built as ``Value`` objects.
``tasks``
    The tree turned into the task list a back end runs.

:func:`load` runs all of it and is the front door.

Like everything else in ``rdf`` this package is a leaf: it imports PyYAML and
its own siblings, and nothing from the rest of Scriptum. See the layering test.
"""

from .addresses import Address
from .diagnostics import Diagnostic, Diagnostics, DocumentError, Position
from .document import (
    CONTENT_KEY,
    GLOBAL_KEY,
    INCLUDE_KEY,
    MIN_REQUIRED_VERSION,
    RESERVED_TOP_LEVEL,
    SETTINGS_KEY,
    DocumentHeader,
    read_fragment,
    read_root,
    read_settings,
)
from .entries import (Container, Entry, Fill, Marker, MAX_INCLUDE_DEPTH,
                      read_content, read_global, walk)
from .nodes import YamlSource
from .tasks import GLOBAL_ROOT, emit


class Document:
    """A loaded report document: its tasks, and the settings they run under."""

    __slots__ = ('tasks', 'settings', 'filename')

    def __init__(self, tasks, settings, filename):
        self.tasks = tasks
        self.settings = settings
        self.filename = filename

    def __repr__(self):
        return (f'Document({self.filename!r}, {len(self.tasks)} tasks, '
                f'documenttype={self.settings.documenttype!r})')


def load(path):
    """Read a root document and return a :class:`Document`.

    Raises :class:`DocumentError` carrying **every** diagnostic, not the first
    -- a document with six mistakes reports six. That is unchanged from the
    text format, and it is why nothing below raises as it goes.

    The four stages are separately usable and the tests drive them that way;
    this is the one call that runs them in order.
    """
    diagnostics = Diagnostics()

    source = YamlSource.from_path(path, diagnostics)
    if source is None:
        diagnostics.raise_if_any()

    header = read_root(source, diagnostics)
    if header is None:
        diagnostics.raise_if_any()

    globals_ = read_global(header.global_node, source, header.settings,
                           diagnostics)
    entries = read_content(header.content_node, source, header.settings,
                           diagnostics)

    diagnostics.raise_if_any()

    return Document(emit(entries, header.settings, globals_),
                    header.settings, source.filename)


__all__ = [
    'Diagnostic', 'Diagnostics', 'DocumentError', 'Position',
    'YamlSource', 'DocumentHeader', 'Document', 'load',
    'read_root', 'read_fragment', 'read_settings',
    'Address', 'Entry', 'Container', 'Marker', 'Fill',
    'MAX_INCLUDE_DEPTH', 'emit', 'GLOBAL_ROOT',
    'read_content', 'read_global', 'walk',
    'MIN_REQUIRED_VERSION', 'RESERVED_TOP_LEVEL',
    'SETTINGS_KEY', 'GLOBAL_KEY', 'CONTENT_KEY', 'INCLUDE_KEY',
]
