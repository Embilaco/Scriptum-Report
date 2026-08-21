#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""Reading a YAML document as a node graph instead of as Python objects.

``yaml.safe_load`` is not usable here, for two reasons that are both about
things going wrong quietly.

**Positions.** The objects it returns carry nothing about where they came
from, so no diagnostic can point at a line. Nodes carry ``start_mark``.

**Duplicate keys.** PyYAML's mapping constructor keeps the *last* of a
repeated key and says nothing. That is precisely the failure mode that ruled
mappings out for elements in the first place -- an author writing the same
address twice would lose the first one silently -- so the loader must be able
to see the repeat. It is only visible before construction, in the node graph.

Everything here is therefore raw: :func:`pairs` hands back the key/value node
pairs in document order, repeats included, and the caller decides.
"""

import yaml

from .dialect import Core12Loader
from .diagnostics import Position

_NULL_TAG = 'tag:yaml.org,2002:null'


class YamlSource:
    """One parsed document: its root node, and the means to type its scalars.

    The loader is kept after composing because scalar values are built lazily
    -- the walk needs the *node* (for its position) far more often than it
    needs the Python value, so constructing everything up front would throw
    away the thing this class exists to preserve.
    """

    def __init__(self, root, loader, filename):
        self.root = root
        self.filename = filename
        self._loader = loader

    # ------------------------------------------------------------ loading

    @classmethod
    def from_text(cls, text, filename, diagnostics):
        """Compose *text*. Returns ``None`` and records a diagnostic on failure.

        *text* may be ``str`` or ``bytes``. Bytes are preferred for real files:
        PyYAML decodes them per the YAML spec, which means UTF-8 by default and
        UTF-16/32 when a BOM says so. Encoding stops being a question the way it
        was for ``.rdf``, which was read in the platform default and produced
        mojibake with no diagnostic when that guess was wrong.
        """
        loader = Core12Loader(text)
        try:
            root = loader.get_single_node()
        except yaml.MarkedYAMLError as exc:
            diagnostics.error(_marked_message(exc),
                              node=_MarkNode(exc.problem_mark or exc.context_mark),
                              filename=filename)
            return None
        except yaml.YAMLError as exc:
            diagnostics.error(f'cannot parse YAML: {exc}', filename=filename)
            return None
        finally:
            # Frees the parser's state machine. Construction of already-composed
            # scalars does not go through the parser, so it keeps working.
            loader.dispose()

        if root is None:
            diagnostics.error('the document is empty', filename=filename)
            return None

        return cls(root, loader, filename)

    @classmethod
    def from_path(cls, path, diagnostics):
        """Read and compose a file. Bytes in, so the BOM rules above apply."""
        try:
            with open(path, 'rb') as handle:
                text = handle.read()
        except OSError as exc:
            diagnostics.error(f'cannot read {path}: {exc.strerror or exc}',
                              filename=str(path))
            return None
        return cls.from_text(text, str(path), diagnostics)

    # ------------------------------------------------------------- values

    def value(self, node):
        """The typed Python value of a scalar node, under the 1.2 core schema."""
        return self._loader.construct_object(node)

    def position(self, node):
        return Position.of(node, self.filename)


class _MarkNode:
    """Adapter letting a bare PyYAML mark be positioned like a node."""

    __slots__ = ('start_mark',)

    def __init__(self, mark):
        self.start_mark = mark if mark is not None else _ORIGIN


class _Origin:
    line = 0
    column = 0


_ORIGIN = _Origin()


def _marked_message(exc):
    problem = (exc.problem or 'malformed YAML').strip()
    context = (exc.context or '').strip()
    return f'{context}, {problem}' if context else problem


# ------------------------------------------------------------- node kinds

def is_mapping(node):
    return isinstance(node, yaml.MappingNode)


def is_sequence(node):
    return isinstance(node, yaml.SequenceNode)


def is_scalar(node):
    return isinstance(node, yaml.ScalarNode)


def is_null(node):
    """A ``null`` scalar -- which the format reads as 'an empty body'.

    Distinct from the empty string: ``- BackCover:`` is a container with
    nothing in it, ``- rf2: ''`` is a fill whose value is ``''``.
    """
    return isinstance(node, yaml.ScalarNode) and node.tag == _NULL_TAG


def describe(node):
    """How to name this node's kind in a diagnostic."""
    if node is None:
        return 'nothing'
    if is_mapping(node):
        return 'a mapping'
    if is_sequence(node):
        return 'a sequence'
    if is_null(node):
        return 'empty'
    return 'a scalar'


# ---------------------------------------------------------------- walking

def pairs(node):
    """Key/value node pairs of a mapping, in document order, repeats kept."""
    return list(node.value)


def items(node, source, diagnostics, path=()):
    """Key/value pairs of a mapping with duplicate keys reported and dropped.

    The **first** occurrence wins, which is the opposite of PyYAML's silent
    last-wins. It matters only in that a document with a duplicate is going to
    be rejected anyway -- keeping the first just makes the rest of the walk
    report on what the author wrote at the top rather than the bottom.
    """
    seen = {}
    result = []
    for key_node, value_node in pairs(node):
        key = source.value(key_node) if is_scalar(key_node) else None
        if key is None or not isinstance(key, str):
            diagnostics.error('a key must be plain text',
                              node=key_node, filename=source.filename, path=path)
            continue
        if key in seen:
            diagnostics.error(
                f'duplicate key {key!r}, first written at line {seen[key]}',
                node=key_node, filename=source.filename, path=path)
            continue
        seen[key] = key_node.start_mark.line + 1
        result.append((key, key_node, value_node))
    return result


def sequence(node):
    """Items of a sequence node, in order."""
    return list(node.value)


__all__ = [
    'YamlSource',
    'is_mapping', 'is_sequence', 'is_scalar', 'is_null', 'describe',
    'pairs', 'items', 'sequence',
]
