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
            mark = exc.problem_mark or exc.context_mark
            diagnostics.error(_marked_message(exc, _line_of(text, mark)),
                              node=_MarkNode(mark), filename=filename)
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

        # What composes fine and would go wrong later, or has gone wrong
        # already without a word: a tag the loader cannot construct (it would
        # raise out of construction, far from here), and an anchor nothing
        # refers to (the word is simply gone from the value).
        problems = _unreadable_markup(root, loader)
        if problems:
            for node, message in problems:
                diagnostics.error(message, node=node, filename=filename)
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


def _marked_message(exc, line=''):
    problem = (exc.problem or 'malformed YAML').strip()
    context = (exc.context or '').strip()
    message = f'{context}, {problem}' if context else problem
    hint = _quoting_hint(message, line)
    return f'{message}. {hint}' if hint else message


def _line_of(text, mark):
    """The source line a mark points at, for a hint to quote back."""
    if mark is None:
        return ''
    if isinstance(text, bytes):
        text = text.decode('utf-8', errors='replace').lstrip(chr(0xFEFF))
    lines = text.splitlines()
    return lines[mark.line] if 0 <= mark.line < len(lines) else ''


#: PyYAML's scanner and parser name the token they choked on; an author
#: wrote a value. Each entry maps the problem PyYAML reports to what the
#: author most likely did. The value part of the line is quoted back when it
#: can be found, so the fix is in the message.
_QUOTING_HINTS = (
    ('mapping values are not allowed here',
     "An unquoted value that contains ': ' or ends with ':' reads as a nested "
     "key"),
    ('sequence entries are not allowed here',
     "An unquoted value that starts with '- ' reads as a list item"),
    ('mapping keys are not allowed here',
     "An unquoted value that starts with '? ' reads as a complex key"),
    ('found undefined alias',
     "An unquoted value that starts with '*' reads as a YAML alias"),
    ("found character '\\t'",
     'YAML indents with spaces; a tab cannot start a token'),
    ('cannot start any token',
     "An unquoted value cannot start with '%', '@' or '`'"),
    ('while scanning a block scalar',
     "'|' and '>' start a block scalar, whose text goes on the following "
     "lines, indented; a value that starts with '|' or '>' must be quoted"),
    ('while scanning a quoted scalar',
     'A quoted value was opened and never closed'),
)


def _quoting_hint(message, line):
    """What the author most likely did, from PyYAML's message and the line."""
    for fingerprint, explanation in _QUOTING_HINTS:
        if fingerprint in message:
            break
    else:
        explanation = _quote_inside_quotes(line)
        if not explanation:
            return ''
    value = _value_part(line)
    if value and not value.startswith(("'", '"')):
        quoted = "'" + value.replace("'", "''") + "'"
        return f'{explanation}. Quote the value: {quoted}'
    return explanation


def _quote_inside_quotes(line):
    """A single-quoted value with a lone quote inside: ``'it's``.

    YAML closes the value at the apostrophe and chokes on what follows, with
    a message about block mappings that says nothing about quotes.
    """
    value = _value_part(line)
    if not value.startswith("'"):
        return ''
    body = value[1:]
    index = 0
    while index < len(body):
        if body[index] == "'":
            if body[index + 1:index + 2] == "'":       # an escaped quote
                index += 2
                continue
            rest = body[index + 1:].strip()
            if rest and not rest.startswith('#'):
                return ("A single quote inside a single-quoted value is "
                        "written twice: 'it''s'")
            return ''
        index += 1
    return ''


def _value_part(line):
    """What follows the first ``: `` on a line -- the value of a block entry.

    Addresses carry colons without a following space (``date:creation``), so
    the separator is the colon-space, never a bare colon.
    """
    stripped = line.strip()
    if stripped.startswith('- '):
        stripped = stripped[2:].lstrip()
    _, separator, value = stripped.partition(': ')
    return value.strip() if separator else ''


def _unreadable_markup(root, loader):
    """Tags the loader cannot construct, and anchors nothing refers to.

    Both compose without complaint. A ``!tag`` then raises ``ConstructorError``
    out of the first ``value()`` call, far from any diagnostic; an anchor is
    never heard of again -- ``- title: &me a value`` has silently lost
    ``&me`` from its text. Returns ``(node, message)`` pairs.
    """
    problems = []
    seen = set()
    constructible = loader.yaml_constructors

    def walk(node):
        if id(node) in seen:
            return
        seen.add(id(node))
        if node.tag not in constructible:
            shown = _shown(node)
            written = node.tag if node.tag.startswith('!') else ''
            quoted = ' '.join(part for part in (written, shown) if part)
            problems.append((node, (
                f'{node.tag!r} is a YAML tag, which this format does not '
                f"read. A value that starts with '!' must be quoted"
                + (f": '{quoted}'" if quoted else ''))))
        if is_sequence(node):
            for child in node.value:
                walk(child)
        elif is_mapping(node):
            for key, value in node.value:
                walk(key)
                walk(value)

    walk(root)

    for anchor, node in loader.anchored.items():
        if anchor in loader.aliased:
            continue
        shown = _shown(node)
        problems.append((node, (
            f"'&{anchor}' reads as a YAML anchor, and nothing refers to it, so "
            'the word is dropped from the value. If it is part of the text, '
            'quote the value'
            + (f": '&{anchor} {shown}'" if shown else ''))))

    problems.sort(key=lambda pair: (pair[0].start_mark.line,
                                    pair[0].start_mark.column))
    return problems


def _shown(node):
    """A scalar's text for a hint, or '' for anything else."""
    return node.value.strip() if is_scalar(node) and isinstance(node.value, str) else ''


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
            # An all-digit key is the common case and the confusing one: YAML
            # types it as a number, so it never reaches the rule that would
            # have explained itself. Say what to do about it here.
            written = key_node.value if is_scalar(key_node) else None
            hint = f' Quote it if you meant the text {written!r}.' if written \
                else ''
            diagnostics.error(f'a key must be plain text.{hint}',
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
