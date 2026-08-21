#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""Walking ``_content_`` into a tree of entries.

Every item of a content sequence is a **mapping with exactly one key**, and
that key is an address. What the entry *is* comes from the kind of its value,
not from a keyword::

    - section:title:            # sequence -> a container, with a body
        - head: A pudding       # scalar   -> a fill
        - image:main:           # mapping  -> a fill with an explicit source
            file: pudding.jpg
    - BackCover:                # null     -> a container with an empty body

The two cases cannot collide, because a container never carries a value and a
fill never carries children. Marking the difference with a ``type:`` key would
be ceremony on every line of a format whose commonest entry is a two-word fill.

Nesting is the ladder
---------------------
Depth in ``_content_`` **is** depth in the document type's namespace ladder,
counted in containers -- a fill is a target inside its parent, not a level of
its own. Three rules of the text format retire rather than being reimplemented:

* **Gaps become impossible.** Nesting at depth 2 requires writing the depth-1
  parent, so "skipping a level" has no spelling.
* **Mixing roots has no spelling either**, there being no absolute form to
  disagree with the relative one.
* **Re-opening a root is not expressible, and is not needed.** Restating
  ``section:a`` was how the text format *returned* to a section it had left.
  Under nesting you never leave it, so a second ``- section:a:`` entry means
  what it says: a second instance. That is the sharpest edge when converting
  existing documents -- ``rdf_repeatSection.rdf`` opens ``section:a`` three
  times to add children in three passes, and translating it line by line would
  produce three sections.

Markers are transparent
-----------------------
A marker names a position in the template, not a level and not an instance. So
it takes no id -- two ``marker:content`` entries in one section refer to the
same tag -- and it does not scope numbering: adds inside it count against the
enclosing container, which is what ``checkPath`` does today, markers never
having been part of a path.

What this module does not do yet
--------------------------------
``_include_`` is recognised and recorded unresolved, so a document containing
one parses and nothing silently drops it, but splicing belongs with the include
rules.
"""

from ..namespaces import SECTION_NAMESPACES
from . import addresses
from .addresses import Address
from . import fills
from .document import CONTENT_KEY, GLOBAL_KEY, INCLUDE_KEY
from .nodes import describe, is_mapping, is_null, is_sequence, items, sequence


class Entry:
    """Base: where it is, and which marker it sits in."""

    __slots__ = ('address', 'node', 'path', 'marker')

    def __init__(self, address, node, path, marker=None):
        self.address = address
        self.node = node
        #: Canonical addresses of the enclosing ladder containers, outermost
        #: first. Markers are not in it, matching the path a task carries.
        self.path = tuple(path)
        #: puretag of the enclosing marker, or None. An entry with one is an
        #: *add*: it materialises a new element at that marker rather than
        #: filling one the template already contains.
        self.marker = marker

    @property
    def canonical_path(self):
        return tuple(a.canonical for a in self.path)

    def __repr__(self):
        return f'{type(self).__name__}({self.address})'


class Container(Entry):
    """A section, subsection or slide: a level of the ladder, with a body."""

    __slots__ = ('children',)

    def __init__(self, address, node, path, children, marker=None):
        super().__init__(address, node, path, marker)
        self.children = children


class Marker(Entry):
    """A position in the template, and the things to add there."""

    __slots__ = ('children',)

    def __init__(self, address, node, path, children, marker=None):
        super().__init__(address, node, path, marker)
        self.children = children


class Fill(Entry):
    """A target and its value. An *add* when :attr:`marker` is set."""

    __slots__ = ('value_node', 'value', 'actions')

    def __init__(self, address, node, path, value_node, value, actions,
                 marker=None):
        super().__init__(address, node, path, marker)
        self.value_node = value_node
        #: The built :class:`~Scriptum.rdf.values.Value`.
        self.value = value
        #: Modifier name -> Value, already applied to :attr:`value` for the
        #: types that read them.
        self.actions = actions


class Include(Entry):
    """A path or glob, recorded unresolved. Carries no address."""

    __slots__ = ('pattern',)

    def __init__(self, pattern, node, path, marker=None):
        super().__init__(None, node, path, marker)
        self.pattern = pattern

    def __repr__(self):
        return f'Include({self.pattern!r})'


# --------------------------------------------------------------- the walk

def read_content(content_node, source, settings, diagnostics):
    """Walk a ``_content_`` sequence into a list of entries.

    Returns ``[]`` when the document type is unknown -- that is already
    reported by the settings schema, and guessing a ladder would bury it under
    a page of consequences.
    """
    if content_node is None:
        return []

    ladder = SECTION_NAMESPACES.get(settings.documenttype)
    if ladder is None:
        return []

    return _read_sequence(content_node, source, ladder, settings, diagnostics,
                          depth=0, path=(), display=(CONTENT_KEY,),
                          counters={}, marker=None)


def _read_sequence(node, source, ladder, settings, diagnostics, depth, path,
                   display, counters, marker):
    entries = []
    for item in sequence(node):
        entry = _read_entry(item, source, ladder, settings, diagnostics, depth,
                            path, display, counters, marker)
        if entry is not None:
            entries.append(entry)
    return entries


def _read_entry(node, source, ladder, settings, diagnostics, depth, path,
                display, counters, marker):

    def report(message, at=node, where=display):
        diagnostics.error(message, node=at, filename=source.filename, path=where)

    if not is_mapping(node):
        report(f'an entry is a mapping of one address to its value, not '
               f'{describe(node)}')
        return None

    pairs = items(node, source, diagnostics, display)
    if not pairs:
        # items() has already said why (duplicate key, or a key that is not
        # text). An empty mapping reaches here with nothing said.
        if not node.value:
            report('an entry needs an address')
        return None
    if len(pairs) > 1:
        written = ', '.join(repr(key) for key, _, _ in pairs)
        report(f'an entry has exactly one key, the address. Found {written}. '
               'Each one needs its own "-".', at=pairs[1][1])
        return None

    key, key_node, value_node = pairs[0]
    here = display + (key,)

    if key.lower() == INCLUDE_KEY:
        return _read_include(value_node, key_node, source, diagnostics,
                             path, here, marker)

    address = addresses.parse(key, key_node, source, diagnostics, display)
    if address is None:
        return None

    is_container = is_sequence(value_node) or is_null(value_node)

    if address.is_marker:
        return _read_marker(address, node, value_node, key_node, source, ladder,
                            settings, diagnostics, depth, path, here, counters,
                            marker, is_container)

    if is_container:
        return _read_container(address, node, value_node, key_node, source,
                               ladder, settings, diagnostics, depth, path,
                               here, counters, marker)

    return _read_fill(address, node, value_node, key_node, source, settings,
                      diagnostics, path, display, here, counters, marker)


def _read_include(value_node, key_node, source, diagnostics, path, display,
                  marker):
    if is_sequence(value_node) or is_mapping(value_node):
        diagnostics.error(
            f'{INCLUDE_KEY} takes one path or glob, not {describe(value_node)}',
            node=value_node, filename=source.filename, path=display)
        return None
    pattern = source.value(value_node)
    if not isinstance(pattern, str) or not pattern.strip():
        diagnostics.error(f'{INCLUDE_KEY} needs a path or glob to include',
                          node=value_node, filename=source.filename, path=display)
        return None
    return Include(pattern.strip(), key_node, path, marker)


def _read_marker(address, node, value_node, key_node, source, ladder,
                 settings, diagnostics, depth, path, display, counters, marker,
                 is_container):

    def report(message, at=key_node):
        diagnostics.error(message, node=at, filename=source.filename,
                          path=display)

    if not is_container:
        report(f'{address.puretag} is a marker: its value is the sequence of '
               'things to add there, not a value of its own')
        return None
    if not path:
        report(f'{address.puretag} needs a container around it. A marker is a '
               'position inside an element of the template, so there has to be '
               'an element for it to be inside.')
        return None
    if marker is not None:
        report(f'{address.puretag} is inside {marker}. A marker names one '
               'position; nesting a second inside it names no place at all.')
        return None

    children = [] if is_null(value_node) else _read_sequence(
        value_node, source, ladder, settings, diagnostics, depth, path, display,
        counters, marker=address.puretag)

    # No id: a marker is a reference to a position in the template, not an
    # instance in the output, and two entries naming it mean the same place.
    return Marker(address, key_node, path, children, marker)


def _read_container(address, node, value_node, key_node, source, ladder,
                    settings, diagnostics, depth, path, display, counters,
                    marker):

    def report(message, at=key_node):
        diagnostics.error(message, node=at, filename=source.filename,
                          path=display)

    if marker is not None:
        report(f'{address.puretag} is a container, and a marker adds elements '
               f'rather than levels. Move it out of {marker}.')
        return None

    if not _check_ladder(address, depth, ladder, value_node, report):
        return None

    numbered = _next_id(address, counters)
    children = [] if is_null(value_node) else _read_sequence(
        value_node, source, ladder, settings, diagnostics, depth + 1,
        path + (numbered,), display,
        # A fresh counter map: numbering is scoped to the parent path, so
        # section:a and section:c each count their own subsection:b.
        counters={}, marker=None)

    return Container(numbered, key_node, path, children, marker)


def _read_fill(address, node, value_node, key_node, source, settings,
               diagnostics, path, parent_display, display, counters, marker):
    if not path:
        diagnostics.error(
            f'{address.puretag} is a fill and needs a container around it. '
            f'{CONTENT_KEY} holds the elements of the document; a value goes '
            'inside one of them.',
            node=key_node, filename=source.filename, path=parent_display)
        return None

    value, actions = fills.read(value_node, fills.selector_for(address), source,
                                settings, diagnostics, display)
    if value is None:
        # Whatever was wrong is already reported. Dropping the entry keeps the
        # rest of the walk reporting on the document rather than on the hole.
        return None

    return Fill(_next_id(address, counters), key_node, path, value_node, value,
                actions, marker)


# -------------------------------------------------------------- the rules

def _check_ladder(address, depth, ladder, value_node, report):
    order = ladder['order']
    expected = ladder['names'].get(depth)

    if expected is None:
        report(f'nothing nests this deep. The ladder is: {" > ".join(order)}')
        return False

    if address.namespace == expected:
        return True

    # PowerPoint addresses a slide by its layout name, so a bare name is a
    # legal container there. Word's ladder is mandatory at every level.
    if not ladder['mandatory'] and not address.namespace:
        return True

    written = f'{address.namespace!r}' if address.namespace else 'no namespace'
    hint = ''
    if is_null(value_node):
        # Overwhelmingly this is a fill whose value went missing rather than a
        # container someone meant to leave empty -- and a value opening with
        # '#' is the commonest way for it to go missing, YAML reading the rest
        # of the line as a comment.
        hint = (' An entry with no value is an empty container. To fill '
                "something with an empty string, write '' instead -- and note "
                'that a value starting with "#" is a YAML comment unless it '
                'is quoted.')
    elif is_sequence(value_node):
        hint = (' A sequence value is a body, so this reads as a container. '
                "A fill's value is a scalar or a mapping.")
    report(f'{address.puretag} is at depth {depth}, where the namespace must '
           f'be {expected!r}, but it has {written}. '
           f'The ladder is: {" > ".join(order)}.{hint}')
    return False


def _next_id(address, counters):
    """Number this instance within its parent path.

    Keyed on the *template* address, so instances of one blueprint are what
    get counted: two ``subsection:instruction`` under one section become
    ``::1`` and ``::2`` while a ``subsection:bc`` beside them starts at 1.
    """
    key = address.template
    counters[key] = counters.get(key, 0) + 1
    return address.numbered(counters[key])


def read_global(global_node, source, settings, diagnostics):
    """Read the ``_global_`` mapping into fills applied last, everywhere.

    **No ids.** A global fill is not an instance, it is a rule applied to every
    instance: ``global`` matches on ``puretag`` alone -- deliberately, since
    that is what lets it reach clones -- so numbering one would name something
    the match ignores. Markers are refused here for the mirror-image reason: a
    marker names a position inside one element, and there is no one element.
    """
    if global_node is None:
        return []

    result = []
    for key, key_node, value_node in items(global_node, source, diagnostics,
                                           (GLOBAL_KEY,)):
        address = addresses.parse(key, key_node, source, diagnostics,
                                  (GLOBAL_KEY,))
        if address is None:
            continue

        if address.is_marker:
            diagnostics.error(
                f'{address.puretag} names a position inside one element, and '
                f'{GLOBAL_KEY} applies to every element. Put the marker in '
                f'{CONTENT_KEY}, where there is an element for it to be in.',
                node=key_node, filename=source.filename, path=(GLOBAL_KEY,))
            continue

        value, actions = fills.read(value_node, fills.selector_for(address),
                                    source, settings, diagnostics,
                                    (GLOBAL_KEY, key))
        if value is None:
            continue

        result.append(Fill(address, key_node, (), value_node, value, actions))

    return result


# ------------------------------------------------------------- traversal

def walk(entries):
    """Yield every entry in document order, depth first.

    Order is significant: both back ends iterate the task list in order, and
    PPTX carries a current-slide position through it.
    """
    for entry in entries:
        yield entry
        if isinstance(entry, (Container, Marker)):
            yield from walk(entry.children)


__all__ = [
    'Entry', 'Container', 'Marker', 'Fill', 'Include',
    'read_content', 'read_global', 'walk', 'Address',
]
