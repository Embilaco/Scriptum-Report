#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""The shape of a YAML report document, and its ``_scriptum_`` settings block.

Two document shapes, told apart by the kind of the top node
-----------------------------------------------------------
A **root document** is a mapping of three reserved keys and nothing else::

    _scriptum_:   settings. A mapping.  Required. Root document only.
    _global_:     fills applied LAST, everywhere. A mapping. Optional.
    _content_:    the report body. A sequence. Optional.

An **included fragment** is a bare sequence of entries. It carries no settings
and no ``_global_`` because both are root-only, and a sequence has nowhere to
put them -- the rule enforces itself rather than needing a check. A fragment
handed in as a root document fails on the missing ``_scriptum_`` instead of
half-working.

``_global_`` is a top-level key rather than an entry because *applied last* is
not a position. Putting it inside an ordered sequence would invite an author to
reason about where it sits, and make "order is significant" true with an
exception.

The container kind states the constraint
----------------------------------------
``_content_`` is a **sequence** because order matters there and repetition is
meaningful: writing the same address twice is how a template block becomes two
addressable instances.

``_global_`` is a **mapping**, and for the mirror-image reason. A global fill
matches on ``puretag`` alone, so it reaches *every* tag of that name in the
document; there is no instance for a second entry to distinguish itself by.
Two entries with the same address would not be an ordering, they would be a
contradiction. Order is meaningless there for the same reason -- each address
is filled once, everywhere.

The obvious objection is that a mapping is what *lost* the elements argument:
duplicate keys are silently collapsed to the last, which is the failure this
format is shaped around. It does not apply here, because this loader never
lets PyYAML construct a mapping. It walks the node graph and reports a
repeated key as an error (``nodes.items``), so the uniqueness a mapping claims
is one the loader actually enforces.

Three changes from ``*key=value``
---------------------------------
**An unknown key is an error.** The text format wrote an unrecognised ``*key``
to the log as ignored and carried on. That tolerance is what hid ``*timeformat``
for years -- a setting nobody implemented, costing nothing but an unchanged
default and no diagnostic to explain it.

**Root document only**, which the shape enforces on its own.

**Order stops mattering.** A mapping is read whole before the body, so
``documenttype`` selects the namespace ladder before any entry is interpreted
no matter where the author wrote it. The old "settings must come first" rule
retires with nothing to replace it.
"""

from pathlib import Path

from ..namespaces import SECTION_NAMESPACES
from ..settings import SETTINGS
from .nodes import describe, is_mapping, is_sequence, items

#: The YAML format is version 4. The text format required 3, and giving the
#: replacement its own floor means a document can be identified as one or the
#: other without guessing from its extension.
MIN_REQUIRED_VERSION = 4

SETTINGS_KEY = '_scriptum_'
GLOBAL_KEY = '_global_'
CONTENT_KEY = '_content_'

#: Legal wherever an entry is legal, so it is not a top-level key. Its position
#: places the content it pulls in.
INCLUDE_KEY = '_include_'

#: Everything legal at the top level of a root document.
RESERVED_TOP_LEVEL = (SETTINGS_KEY, GLOBAL_KEY, CONTENT_KEY)

#: Settings that must be present. ``documenttype`` selects the address ladder,
#: so nothing below it can be validated without one.
REQUIRED_SETTINGS = ('version', 'documenttype')


class DocumentHeader:
    """What a root document declares, before any content is interpreted."""

    __slots__ = ('settings', 'global_node', 'content_node', 'source')

    def __init__(self, settings, global_node, content_node, source):
        self.settings = settings
        self.global_node = global_node
        self.content_node = content_node
        self.source = source

    def __repr__(self):
        return (f'DocumentHeader({self.source.filename!r}, '
                f'documenttype={self.settings.documenttype!r})')


# --------------------------------------------------------------- validators
#
# Each takes the constructed value and returns what to store, or ``None`` after
# recording why not. They never raise: diagnostics accumulate.

def _kind_of(value):
    if isinstance(value, bool):
        return 'a true/false value'
    if isinstance(value, int):
        return 'a whole number'
    if isinstance(value, float):
        return 'a number'
    if value is None:
        return 'nothing'
    return f'{value!r}'


def _integer(key, value, report):
    # bool is a subclass of int, and `version: true` is not a version.
    if isinstance(value, bool) or not isinstance(value, int):
        report(f'{key} must be a whole number, not {_kind_of(value)}')
        return None
    return value


def _text(key, value, report):
    if not isinstance(value, str):
        report(f'{key} must be text, not {_kind_of(value)}. '
               f'Quote it if that is what you meant.')
        return None
    return value


def _single_character(key, value, report):
    if not isinstance(value, str):
        report(f'{key} must be a single character, not {_kind_of(value)}')
        return None
    if len(value) != 1:
        report(f'{key} must be exactly one character, not {value!r}')
        return None
    return value


def _version(key, value, report):
    number = _integer(key, value, report)
    if number is None:
        return None
    if number < MIN_REQUIRED_VERSION:
        report(f'{key} is {number}; this format needs at least '
               f'{MIN_REQUIRED_VERSION}')
        return None
    return number


def _documenttype(key, value, report):
    text = _text(key, value, report)
    if text is None:
        return None
    lowered = text.lower()
    if lowered not in SECTION_NAMESPACES:
        known = ', '.join(sorted(SECTION_NAMESPACES))
        report(f'{key} {text!r} is not a known document type. Known: {known}')
        return None
    return lowered


def _directory(key, value, report):
    text = _text(key, value, report)
    if text is None:
        return None
    # Backslashes are accepted so a Windows-shaped path in a document still
    # resolves; Path normalises the rest.
    path = Path(text.replace('\\', '/'))
    if not path.exists():
        report(f'{key} {text!r} does not exist')
        return None
    return path


#: setting name -> validator. Membership here is what makes a key legal, so
#: adding a setting is one line and an unknown key cannot slip through.
SCHEMA = {
    'version': _version,
    'documenttype': _documenttype,
    'datadir': _directory,
    'dateformat': _text,
    'datetimeformat': _text,
    'nvseparator': _single_character,
    'csvseparator': _single_character,
    'floatformat': _text,
    'documenttitle': _text,
}


# ------------------------------------------------------------------ reading

def read_settings(node, source, diagnostics, path=(SETTINGS_KEY,)):
    """Validate a ``_scriptum_`` mapping into a :class:`SETTINGS`.

    Always returns a SETTINGS -- an invalid one still carries its defaults, so
    the walk can continue and report everything else that is wrong rather than
    stopping at the header.
    """
    settings = SETTINGS()

    if not is_mapping(node):
        diagnostics.error(
            f'{SETTINGS_KEY} must be a mapping of settings, not {describe(node)}',
            node=node, filename=source.filename, path=path)
        return settings

    provided = set()
    for key, key_node, value_node in items(node, source, diagnostics, path):
        # Keys are lowercased like every other key in the format. The text
        # format lowercased addresses but not setting names, so a capitalised
        # one fell through to "unknown" and was ignored without a word.
        name = key.lower()

        def report(message, _node=value_node, _path=path):
            diagnostics.error(message, node=_node,
                              filename=source.filename, path=_path)

        if name not in SCHEMA:
            diagnostics.error(
                f'unknown setting {key!r}. Known: {", ".join(sorted(SCHEMA))}',
                node=key_node, filename=source.filename, path=path)
            continue

        if not hasattr(value_node, 'value') or is_mapping(value_node) \
                or is_sequence(value_node):
            report(f'{name} must be a single value, not {describe(value_node)}')
            continue

        accepted = SCHEMA[name](name, source.value(value_node), report)
        provided.add(name)
        if accepted is not None:
            setattr(settings, name, accepted)

    for name in REQUIRED_SETTINGS:
        if name not in provided:
            diagnostics.error(f'{name} is required and was not set',
                              node=node, filename=source.filename, path=path)

    return settings


def read_root(source, diagnostics):
    """Read a root document's header. Returns ``None`` if it is not one."""
    root = source.root

    if not is_mapping(root):
        hint = ''
        if is_sequence(root):
            hint = (' A bare sequence is an included fragment, not a root '
                    'document; a root document needs its own '
                    f'{SETTINGS_KEY} block.')
        diagnostics.error(
            f'a root document is a mapping of '
            f'{", ".join(RESERVED_TOP_LEVEL)}, not {describe(root)}.{hint}',
            node=root, filename=source.filename)
        return None

    sections = {}
    for key, key_node, value_node in items(root, source, diagnostics):
        name = key.lower()
        if name not in RESERVED_TOP_LEVEL:
            diagnostics.error(
                f'{key!r} is not allowed at the top level of a root document. '
                f'Content belongs under {CONTENT_KEY}. '
                f'Allowed here: {", ".join(RESERVED_TOP_LEVEL)}',
                node=key_node, filename=source.filename)
            continue
        sections[name] = value_node

    settings_node = sections.get(SETTINGS_KEY)
    if settings_node is None:
        diagnostics.error(f'{SETTINGS_KEY} is required in a root document',
                          node=root, filename=source.filename)
        settings = SETTINGS()
    else:
        settings = read_settings(settings_node, source, diagnostics)

    global_node = _expect_mapping(sections.get(GLOBAL_KEY), GLOBAL_KEY,
                                  source, diagnostics)
    # The uniqueness the mapping shape claims is enforced when the block is
    # walked, in entries.read_global: nodes.items reports a repeated key rather
    # than letting it collapse to the last, which is the whole reason a mapping
    # is safe here at all. Checking it twice would report it twice.
    content_node = _expect_sequence(sections.get(CONTENT_KEY), CONTENT_KEY,
                                    source, diagnostics)

    return DocumentHeader(settings, global_node, content_node, source)


def read_fragment(source, diagnostics):
    """Read an included fragment: a bare sequence of entries.

    Returns the sequence node, or ``None`` after reporting.
    """
    root = source.root
    if is_sequence(root):
        return root

    hint = ''
    if is_mapping(root):
        hint = (f' A mapping is a root document; {SETTINGS_KEY} and '
                f'{GLOBAL_KEY} belong to the root only, and an included '
                'fragment carries neither.')
    diagnostics.error(
        f'an included fragment is a sequence of entries, not {describe(root)}.'
        f'{hint}',
        node=root, filename=source.filename)
    return None


def _expect_sequence(node, key, source, diagnostics):
    if node is None:
        return None
    if is_sequence(node):
        return node
    diagnostics.error(
        f'{key} must be a sequence of entries, not {describe(node)}. '
        'Every entry starts with "-", because order and repetition matter here.',
        node=node, filename=source.filename, path=(key,))
    return None


def _expect_mapping(node, key, source, diagnostics):
    if node is None:
        return None
    if is_mapping(node):
        return node
    hint = ''
    if is_sequence(node):
        hint = (' Entries here take no "-": a global fill reaches every tag of '
                'its name, so each address appears once and their order does '
                'not matter.')
    diagnostics.error(
        f'{key} must be a mapping of address to value, not {describe(node)}.'
        f'{hint}',
        node=node, filename=source.filename, path=(key,))
    return None


__all__ = [
    'DocumentHeader', 'MIN_REQUIRED_VERSION', 'SCHEMA',
    'SETTINGS_KEY', 'GLOBAL_KEY', 'CONTENT_KEY', 'INCLUDE_KEY',
    'RESERVED_TOP_LEVEL',
    'read_root', 'read_fragment', 'read_settings',
]
