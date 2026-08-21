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
    ``_content_`` walked into a tree: containers, markers, fills and includes.

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
from .entries import Container, Entry, Fill, Include, Marker, read_content, walk
from .nodes import YamlSource

__all__ = [
    'Diagnostic', 'Diagnostics', 'DocumentError', 'Position',
    'YamlSource', 'DocumentHeader',
    'read_root', 'read_fragment', 'read_settings',
    'Address', 'Entry', 'Container', 'Marker', 'Fill', 'Include',
    'read_content', 'walk',
    'MIN_REQUIRED_VERSION', 'RESERVED_TOP_LEVEL',
    'SETTINGS_KEY', 'GLOBAL_KEY', 'CONTENT_KEY', 'INCLUDE_KEY',
]
