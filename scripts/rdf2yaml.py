#!/usr/bin/env python3
"""Convert Scriptum's retired ``.rdf`` text format to a ``.yaml`` report document.

A starting point, not a bullet-proof translation. The text format carried its
structure in dotted addresses and prefix characters; the YAML document carries
it in nesting. Most of that is mechanical and is done here. What was
*ambiguous* in the text format -- an absolute address that re-enters a path
with several instances, a fragment that jumps to another section, a setting
defined twice, a marker an include silently cleared -- is decided the way the
old parser decided it, or the way the hand-translated corpus decided it, and
marked with a ``# CHECK:`` comment in the output. The places to look at by
hand are the places with a comment. The result is then loaded the way Scriptum
loads it and the diagnostics printed (unless ``--no-check``): fix what it
refuses, and the document is done.

Usage::

    python scripts/rdf2yaml.py report.rdf [more.rdf ...] [--out DIR] [--force]
                               [--no-follow] [--no-check]

Every ``.rdf`` named is a root document and is written as a ``.yaml`` beside
it (or under ``--out``, keeping the name). Files an ``&include`` names are
followed and converted as fragments -- a bare sequence of entries, relative to
where the include sits -- and the include becomes ``- _include_: name.yaml``
(a ``loopfiles:`` glob keeps its wildcard, extension changed). An existing
``.yaml`` is not overwritten without ``--force``.

What is translated
------------------
* ``*key=value`` -> the ``_scriptum_`` mapping. ``version`` becomes 4, the
  YAML format's floor; ``datadir`` backslashes become slashes; an unknown key,
  or a key set a second time, is kept as a comment.
* the ``global`` root -> the ``_global_`` mapping (a repeated address there
  is kept as a comment: a mapping holds each once).
* ``section:a`` / ``section:a.subsection:b`` / ``.subsection:b`` structural
  lines -> nested containers. A structural line creates a **new instance** of
  its last segment -- that is what a repeat meant -- except a re-stated
  top-level Word section, which the text format used to *return* to a section
  and never cloned. Every PowerPoint slide line is a new slide.
* ``.target=value`` and ``path.target=value`` -> fills under the right
  container. Value grammar: ``file:x`` -> ``{file: x}``; ``parfile:f:p`` ->
  ``{parfile: f, parameter: p}``; ``date:now:'fmt'`` -> ``{date: now, format:
  'fmt'}``; ``numbering:k:f:s`` -> ``{numbering: k, format: f, start: s}``;
  ``@row1`` -> ``{from: row1}``; quoted text -> text; a bare number -> a
  number; ``+name=value`` modifiers -> further keys of the mapping.
* ``@marker:name`` then ``+address=value`` lines -> a ``marker:name:`` entry
  holding the adds, interleaved with fills as written.
* ``&include[+]=file:x.rdf`` / ``loopfiles:pat*.rdf`` -> ``- _include_: …``
  where the line sits -- inside the open marker if the fragment is adds, in
  the section if the fragment is structure (the old parser cleared the marker
  on the fragment's first address line; the corpus had three of these dead
  markers) -- and the fragment converted relative to that site. A fragment
  that opens a *different* top-level section is attached there instead. Both
  get a CHECK comment.
* comments and blank lines stay where they were.
"""

from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path


DOCX_LADDER = ['section', 'subsection', 'subsubsection', 'sub3section',
               'sub4section', 'sub5section']

KNOWN_SETTINGS = ('version', 'documenttype', 'datadir', 'dateformat',
                  'datetimeformat', 'nvseparator', 'csvseparator', 'floatformat',
                  'documenttitle')


# ---------------------------------------------------------------- the tree

class Node:
    """One entry of the document being built.

    ``kind``: ``container`` (address + children), ``fill`` (address + rendered
    value), ``marker`` (address + children -- the adds), ``include`` (value is
    the path), ``comment`` (value is the text) or ``blank``.
    """

    def __init__(self, kind, address='', value='', note=''):
        self.kind = kind
        self.address = address
        self.value = value
        self.note = note            # a CHECK comment printed above the entry
        self.children = []
        self.seeded = False         # part of an include site's scaffolding

    def find_latest(self, address):
        """The most recent container with this address among the children --
        what the text parser's renaming bound an absolute address to."""
        for child in reversed(self.children):
            if child.kind == 'container' and child.address == address:
                return child
        return None

    def count(self, address):
        return sum(1 for c in self.children
                   if c.kind == 'container' and c.address == address)

    def last_marker(self, address):
        """The open marker's node if it is the last real entry, else None."""
        for child in reversed(self.children):
            if child.kind in ('comment', 'blank'):
                continue
            if child.kind == 'marker' and child.address == address:
                return child
            return None
        return None


class Document:
    """One file being converted: settings, globals, the content tree, notes."""

    def __init__(self, source):
        self.source = Path(source)
        self.settings = {}
        self.setting_notes = []
        self.head = []                 # comments before anything else
        self.globals = []              # fills and comments under global
        self.content = Node('container', '_content_')
        self.warnings = []
        self.documenttype = None

    def warn(self, text):
        self.warnings.append(text)


# -------------------------------------------------------------- rendering

_PLAIN_SAFE = re.compile(r'^(?:\./|/)?[A-Za-z_][A-Za-z0-9_ .()/%=+\-]*$')
_NUMBERISH = re.compile(r'^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$'
                        r'|^0[xXoObB][0-9a-fA-F]+$')
_RESERVED_WORDS = {'true', 'false', 'null', '~', 'yes', 'no', 'on', 'off', 'y', 'n'}


def yaml_text(text):
    """A string as a YAML scalar that reads back as exactly this string.

    Plain where it is safe, single-quoted otherwise, double-quoted when the
    text carries a line break or a tab (the text format wrote ``\\n`` inside
    double quotes for a line break; YAML does the same)."""
    if text == '':
        return "''"
    if (_PLAIN_SAFE.match(text) and not _NUMBERISH.match(text)
            and text.lower() not in _RESERVED_WORDS
            and not text.endswith((' ', ':')) and ': ' not in text
            and ' #' not in text):
        return text
    if '\n' in text or '\t' in text:
        return '"' + (text.replace('\\', '\\\\').replace('"', '\\"')
                      .replace('\n', '\\n').replace('\t', '\\t')) + '"'
    return "'" + text.replace("'", "''") + "'"


def yaml_key(text):
    return text if re.match(r'^[A-Za-z_][A-Za-z0-9_:\-]*$', text) else yaml_text(text)


def unquote(text):
    """Strip one pair of matching quotes; a double-quoted ``\\n`` is a newline."""
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
        inner = text[1:-1]
        if text[0] == '"':
            inner = inner.replace('\\n', '\n')
        return inner, True
    return text, False


def split_modifiers(raw):
    """``main+name=value+name=value`` -> (main, [(name, value), ...]).

    The text parser split on every ``+``; splitting only where ``name=``
    follows lets a ``+`` inside a quoted text survive, which is what the
    author meant by it."""
    parts = re.split(r'\+(?=[A-Za-z_][A-Za-z0-9_:.\-]*=)', raw)
    main = parts[0].strip()
    modifiers = []
    for part in parts[1:]:
        name, _, value = part.partition('=')
        modifiers.append((name.strip().lower(), value.strip()))
    return main, modifiers


def split_date(spec):
    """``now:'fmt'`` / ``'12/15/22 14:24:59':'fmt'`` / ``1231231230`` -> (spec, fmt)."""
    spec = spec.strip()
    if spec[:1] in ('"', "'"):
        close = spec.find(spec[0], 1)
        if close > 0:
            head, rest = spec[:close + 1], spec[close + 1:].strip()
            fmt = rest[1:].strip() if rest.startswith(':') else ''
            return unquote(head)[0], (unquote(fmt)[0] if fmt else None)
    head, sep, rest = spec.partition(':')
    rest = rest.strip()
    return head.strip(), (unquote(rest)[0] if sep and rest else None)


def render_value(raw, selector=''):
    """The YAML for one text-format value (a main value or a modifier's)."""
    raw = raw.strip()
    lowered = raw.lower()
    if lowered.startswith('file:'):
        return '{file: ' + yaml_text(unquote(raw[5:])[0].replace('\\', '/')) + '}'
    if lowered.startswith('parfile:'):
        filename, _, parameter = raw[8:].rpartition(':')
        return ('{parfile: ' + yaml_text(unquote(filename)[0].replace('\\', '/')) +
                ', parameter: ' + yaml_text(unquote(parameter)[0]) + '}')
    if lowered.startswith('date:'):
        spec, fmt = split_date(raw[5:])
        spec_yaml = spec if _NUMBERISH.match(spec) else yaml_text(spec)
        return '{date: ' + spec_yaml + (', format: ' + yaml_text(fmt) if fmt else '') + '}'
    if lowered.startswith('numbering:'):
        parts = raw[10:].split(':')
        kind = parts[0] if parts else ''
        fmt = parts[1] if len(parts) > 1 else ''
        out = '{numbering: ' + yaml_text(kind) + ', format: ' + yaml_text(fmt)
        if len(parts) > 2:
            start = parts[2]
            out += ', start: ' + (start if _NUMBERISH.match(start) else yaml_text(start))
        return out + '}'
    if lowered.startswith('@'):
        return '{from: ' + yaml_text(raw[1:]) + '}'
    text, quoted = unquote(raw)
    if quoted:
        return yaml_text(text)
    if _NUMBERISH.match(raw):
        return raw                          # a literal number stays a number
    return yaml_text(raw)                   # unquoted text is text in YAML


def render_fill_value(rawvalue, target):
    """Main value plus its modifiers as one YAML value."""
    main, modifiers = split_modifiers(rawvalue)
    main_yaml = render_value(main, target.split(':')[0])
    if not modifiers:
        return main_yaml
    items = []
    if main_yaml.startswith('{') and main_yaml.endswith('}'):
        items.append(main_yaml[1:-1])
    else:
        items.append('text: ' + main_yaml)
    for name, value in modifiers:
        items.append(yaml_key(name) + ': ' + render_value(value, name.split(':')[0]))
    return '{' + ', '.join(items) + '}'


# ----------------------------------------------------------------- reading

class State:
    """Where the reader is in a file: the container new entries go into, its
    address path from the tree's top, and the open marker."""

    def __init__(self, top, node, path, marker=None, marker_node=None):
        self.top = top
        self.node = node
        self.path = list(path)
        self.marker = marker
        self.marker_node = marker_node
        self.in_global = False
        self.pending = []            # comments waiting for the next entry


class Converter:

    def __init__(self, follow=True, out_dir=None, force=False):
        self.follow = follow
        self.out_dir = Path(out_dir) if out_dir else None
        self.force = force
        self.written = []
        self.skipped = []
        self.visiting = []
        self._pending_note = ''

    # -- files

    def target_path(self, rdf_path):
        rdf_path = Path(rdf_path)
        name = rdf_path.with_suffix('.yaml').name
        return (self.out_dir / name) if self.out_dir else rdf_path.with_suffix('.yaml')

    def _write(self, rdf_path, text):
        target = self.target_path(rdf_path)
        if target.exists() and not self.force:
            self.skipped.append(target)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        self.written.append(target)

    # -- entry points

    def convert_root(self, rdf_path):
        rdf_path = Path(rdf_path).resolve()
        document = Document(rdf_path)
        state = State(top=document.content, node=document.content, path=[])
        self.visiting.append(rdf_path)
        try:
            self._read(rdf_path, document, state)
        finally:
            self.visiting.pop()
        self._write(rdf_path, self.render_root(document))
        return document

    def convert_fragment(self, rdf_path, document, site_path, marker):
        """Convert an included file relative to its include site.

        Writes the fragment's own ``.yaml`` and returns the path (a list of
        container addresses from the top) of the node the fragment's entries
        belong under -- ``site_path`` in the clean case; a shallower path, or
        another top-level section, when the fragment addressed a level above
        its include or jumped elsewhere; the caller re-homes the include
        accordingly -- paired with whether the fragment holds structure
        (containers), which decides whether an include may sit inside a marker.
        ``(None, False)`` for an empty fragment. ``marker`` is the caller's open
        marker, if any: the text format passed it on, so a fragment of ``+``
        lines is adds at that marker -- which, relative to an ``_include_``
        placed inside the marker, are plain entries.
        """
        rdf_path = Path(rdf_path).resolve()
        if rdf_path in self.visiting:
            document.warn(f'{rdf_path.name}: include cycle, not followed')
            return None, False
        fragment = Document(rdf_path)
        node = fragment.content
        node.seeded = True
        for address in site_path:
            child = Node('container', address)
            child.seeded = True
            node.children.append(child)
            node = child
        site_node = node
        state = State(top=fragment.content, node=site_node, path=site_path,
                      marker=marker, marker_node=site_node if marker else None)
        self.visiting.append(rdf_path)
        try:
            self._read(rdf_path, fragment, state)
        finally:
            self.visiting.pop()

        for key in fragment.settings:
            fragment.warn(f'{rdf_path.name}: setting *{key} in an included file is '
                          'dropped -- settings live in the root document only')
        if any(n.kind == 'fill' for n in fragment.globals):
            fragment.warn(f'{rdf_path.name}: global fills in an included file are '
                          'dropped -- put them in the root document')

        # What the fragment put under each node of the seeded chain, by the
        # path of that node. Entries at the site itself are the normal case;
        # entries on a shallower node mean the fragment addressed a level
        # above its include, and entries under a top-level section other than
        # the site's mean it jumped elsewhere -- the caller re-homes the
        # include for those, the way the hand-translated corpus did.
        placements = []
        chain = [fragment.content]
        for address in site_path:
            chain.append(chain[-1].find_latest(address))
        for depth, seeded in enumerate(chain):
            own = [c for c in seeded.children if not c.seeded]
            if depth == 0:
                # top level: a container here is a jump to another section
                jumps = [c for c in own if c.kind == 'container']
                own = [c for c in own if c.kind != 'container']
                for jump in jumps:
                    placements.append(([jump.address], jump.children))
            if own:
                placements.append((list(site_path[:depth]), own))
        document.warnings.extend(fragment.warnings)

        if not placements:
            self._write(rdf_path, self.render_fragment([], rdf_path.name))
            return None, False
        # One placement is the clean case. Several cannot all be relative to
        # one include: the fragment is written with everything, each odd group
        # marked, and the include goes where most of it belongs.
        primary = max(placements, key=lambda p: len(p[1]))
        everything = []
        for parent_path, entries in placements:
            if parent_path != primary[0]:
                for entry in entries:
                    entry.note = entry.note or (
                        f'CHECK: this belongs under {".".join(parent_path) or "the document"}, '
                        f'not under {".".join(primary[0]) or "the document"} where the rest '
                        'of this fragment is included')
                fragment_warning = (f'{rdf_path.name}: entries at two different levels '
                                    f'({".".join(parent_path) or "top"} and '
                                    f'{".".join(primary[0]) or "top"}); see the CHECK comments')
                document.warn(fragment_warning)
            everything.extend(entries)
        self._write(rdf_path, self.render_fragment(everything, rdf_path.name))
        structural = any(e.kind == 'container' for e in everything)
        return primary[0], structural

    # -- the line reader

    def _read(self, rdf_path, document, state):
        try:
            lines = rdf_path.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError:
            lines = rdf_path.read_text(encoding='latin-1').splitlines()
            document.warn(f'{rdf_path.name}: not UTF-8, read as latin-1; check umlauts')
        except OSError as error:
            document.warn(f'{rdf_path.name}: cannot read ({error.strerror or error})')
            return

        pending_blank = False
        for number, raw in enumerate(lines, 1):
            line = raw.strip()
            where = f'{rdf_path.name}:{number}'
            if not line:
                pending_blank = True
                continue
            if pending_blank:
                self._note(state, document, Node('blank'))
                pending_blank = False
            if line.startswith('#'):
                self._note(state, document, Node('comment', value=line[1:].strip()))
                continue

            first = line[0].lower()
            if first == '*':
                self._setting(line[1:], document, where)
            elif first == '&':
                self._include(line, document, state, rdf_path, where)
            elif first == '@':
                state.marker = line[1:].strip().lower()
                state.marker_node = None
            elif first == '+':
                self._add(line[1:], document, state, where)
            elif first == '.':
                self._relative(line[1:], document, state, where)
            elif first.isalpha():
                if line.lower() == 'global':
                    state.in_global = True
                    state.marker = None
                    state.marker_node = None
                    continue
                self._absolute(line, document, state, where)
            else:
                self._note(state, document, Node(
                    'comment', value=f'CHECK: line not understood: {line}'))
                document.warn(f'{where}: first character {line[0]!r} not understood')
        self._flush(state, document)

    def _ladder(self, document):
        return None if document.documenttype == 'pptx' else DOCX_LADDER

    # -- pieces

    def _setting(self, body, document, where):
        key, _, value = body.partition('=')
        key, value = key.strip().lower(), value.strip()
        if key == 'documenttype':
            document.documenttype = value.lower()
        if key not in KNOWN_SETTINGS:
            document.setting_notes.append(f'CHECK: unknown setting dropped ({where}): *{key}={value}')
            document.warn(f'{where}: unknown setting *{key} kept as a comment')
            return
        if key in document.settings:
            document.setting_notes.append(
                f'CHECK: *{key} was set again at {where} ({value}); only the first is kept')
            document.warn(f'{where}: *{key} set twice; the first value is kept')
            return
        if key == 'version':
            document.settings[key] = '4'
        elif key == 'documenttype':
            document.settings[key] = value.lower()
        elif key == 'datadir':
            document.settings[key] = yaml_text(unquote(value)[0].replace('\\', '/'))
        else:
            document.settings[key] = yaml_text(unquote(value)[0])

    def _note(self, state, document, node):
        """Comments and blanks describe what follows: they wait until the next
        entry is placed and go where it goes."""
        if node.kind == 'comment' and not node.value:
            return                                   # a bare '#' separator
        state.pending.append(node)

    def _place(self, state, document, container, node):
        """Append *node* to *container*, with the comments that preceded it.
        Comments before anything at all go to the head of the file."""
        if state.pending:
            if (container is document.content and not document.content.children
                    and not document.globals and state.top is document.content):
                document.head.extend(state.pending)
            else:
                container.children.extend(state.pending)
            state.pending.clear()
        container.children.append(node)

    def _flush(self, state, document):
        """End of file: trailing comments stay in the current container."""
        if state.pending:
            if state.in_global:
                document.globals.extend(state.pending)
            else:
                state.node.children.extend(state.pending)
            state.pending.clear()

    def _marker_node(self, state, document):
        if state.marker_node is not None:
            return state.marker_node
        address = state.marker if state.marker.startswith('marker:') \
            else 'marker:' + state.marker
        node = state.node.last_marker(address)
        if node is None:
            node = Node('marker', address)
            self._place(state, document, state.node, node)
        state.marker_node = node
        return node

    def _fill(self, address, rawvalue, document, state, where, into=None):
        address = address.strip().lower()
        if not address:
            document.warn(f'{where}: a value without a target; dropped')
            return
        node = Node('fill', address, render_fill_value(rawvalue, address))
        if state.in_global:
            document.globals.extend(state.pending)
            state.pending.clear()
            document.globals.append(node)
        else:
            self._place(state, document, into if into is not None else state.node, node)

    def _add(self, body, document, state, where):
        if state.in_global:
            document.warn(f'{where}: + is not allowed under global; dropped')
            return
        path, _, rawvalue = body.partition('=')
        if state.marker is None:
            document.warn(f'{where}: + without a marker; written as a plain fill')
            self._fill(path, rawvalue, document, state, where)
            return
        self._fill(path, rawvalue, document, state, where, into=self._marker_node(state, document))

    def _relative(self, body, document, state, where):
        state.marker = None
        state.marker_node = None
        if state.in_global:
            path, sep, rawvalue = body.partition('=')
            if not sep:
                document.warn(f'{where}: structure under global; dropped')
                return
            self._fill(path, rawvalue, document, state, where)
            return
        if '=' in body:
            path, _, rawvalue = body.partition('=')
            segments = [s for s in path.strip().lower().split('.') if s]
            if not segments:
                document.warn(f'{where}: a value without a target; dropped')
                return
            *intermediate, target = segments
            node = state.node
            ladder = self._ladder(document)
            for offset, address in enumerate(intermediate):
                address = self._ladder_name(address, len(state.path) + offset, ladder,
                                            document, where)
                node = self._enter(node, address, document, where, create_new=False, state=state)
            self._fill(target, rawvalue, document, state, where, into=node)
            return
        segments = [s for s in body.strip().lower().split('.') if s]
        if not segments:
            return
        ladder = self._ladder(document)
        namespace = segments[0].split(':', 1)[0]
        if ladder is not None:
            if namespace in ladder:
                depth = ladder.index(namespace)
                if depth > len(state.path):
                    document.warn(f'{where}: {segments[0]} skips a level of the ladder; '
                                  'nested where it sits')
                    depth = len(state.path)
                self._cut_back(state, depth)
            else:
                document.warn(f'{where}: {segments[0]!r} is not a ladder namespace; '
                              'nested where it sits')
        for index, address in enumerate(segments):
            address = self._ladder_name(address, len(state.path), ladder, document, where)
            child = self._enter(state.node, address, document, where,
                                create_new=(index == len(segments) - 1), state=state)
            state.node = child
            state.path.append(address)

    def _absolute(self, line, document, state, where):
        state.marker = None
        state.marker_node = None
        if state.in_global:
            state.in_global = False
        ladder = self._ladder(document)
        if '=' in line:
            path, _, rawvalue = line.partition('=')
            segments = [s for s in path.strip().lower().split('.') if s]
            *intermediate, target = segments
            node = self._navigate(intermediate, document, state, ladder, where, structural=False)
            self._fill(target, rawvalue, document, state, where, into=node)
            return
        segments = [s for s in line.strip().lower().split('.') if s]
        node = self._navigate(segments, document, state, ladder, where, structural=True)
        state.node = node
        state.path = self._path_to(state.top, node)

    def _navigate(self, segments, document, state, ladder, where, structural):
        """An absolute path from the tree's top: the most recent instance of
        each prefix segment; a structural line's last segment is a new
        instance, except a top-level Word section (and any PowerPoint slide
        line, which is always new)."""
        node = state.top
        for index, address in enumerate(segments):
            last = index == len(segments) - 1
            if ladder is None:
                create_new = structural and index == 0
            else:
                create_new = structural and last and index > 0
                address = self._ladder_name(address, index, ladder, document, where)
            node = self._enter(node, address, document, where, create_new=create_new, state=state)
        return node

    def _ladder_name(self, address, depth, ladder, document, where):
        """A segment whose namespace is not on the Word ladder at all -- the
        corpus had a ``subsubsubsection`` -- gets the ladder's name at its
        depth, with a note: the template's tag must be renamed to match."""
        if ladder is None or ':' not in address:
            return address
        namespace, name = address.split(':', 1)
        if namespace in ladder or depth >= len(ladder):
            return address
        fixed = f'{ladder[depth]}:{name}'
        document.warn(f'{where}: {namespace!r} is not on the ladder; written as {fixed} '
                      '-- the template tag must be renamed to match (CHECK)')
        self._pending_note = (f'CHECK: was {address}; {namespace!r} is not on the ladder, '
                              f'{ladder[depth]!r} is its depth -- rename the template tag too')
        return fixed

    def _enter(self, parent, address, document, where, create_new, state=None):
        existing = parent.find_latest(address)
        if existing is not None and not create_new:
            count = parent.count(address)
            if count > 1 and not existing.note:
                existing.note = (f'CHECK: {where} re-enters {address}, which has {count} '
                                 'instances here; the old parser bound it to the most '
                                 'recent one, as done here')
                document.warn(f'{where}: {address} has {count} instances; the absolute '
                              'address was bound to the most recent one (CHECK)')
            return existing
        child = Node('container', address)
        note = self._pending_note
        if note:
            child.note = note
            self._pending_note = ''
        if state is not None:
            self._place(state, document, parent, child)
        else:
            parent.children.append(child)
        return child

    def _path_to(self, top, node):
        """The addresses from *top* down to *node* (containers only)."""
        def walk(current, trail):
            if current is node:
                return trail
            for child in current.children:
                if child.kind == 'container':
                    found = walk(child, trail + [child.address])
                    if found is not None:
                        return found
            return None
        return walk(top, []) or []

    def _cut_back(self, state, depth):
        if depth >= len(state.path):
            return
        node = state.top
        for address in state.path[:depth]:
            node = node.find_latest(address)
        state.path = state.path[:depth]
        state.node = node

    def _include(self, line, document, state, rdf_path, where):
        if not line.lower().startswith('&include'):
            document.warn(f'{where}: {line[:30]!r} is not an include; kept as a comment')
            self._note(state, document, Node('comment', value=f'CHECK: {line}'))
            return
        if state.in_global:
            document.warn(f'{where}: include under global; dropped')
            return
        _, _, source = line.partition('=')
        source = source.strip()
        lowered = source.lower()
        if lowered.startswith('file:'):
            pattern, is_glob = source[5:].strip(), False
        elif lowered.startswith('loopfiles:'):
            pattern, is_glob = source[10:].strip(), True
        else:
            document.warn(f'{where}: include source {source!r} not understood')
            self._note(state, document, Node('comment', value=f'CHECK: {line}'))
            return
        pattern = unquote(pattern)[0].replace('\\', '/')
        yaml_pattern = re.sub(r'\.rdf$', '.yaml', pattern, flags=re.I)

        include = Node('include', value=yaml_pattern)
        in_marker = state.marker is not None
        if not self.follow:
            self._place(state, document, self._marker_node(state, document) if in_marker else state.node,
                        include)
            return

        files = self._resolve(rdf_path.parent, pattern, is_glob, document, where)
        if files is None:
            include.note = f'CHECK: {pattern} was not found next to {rdf_path.name}; not converted'
            self._place(state, document, self._marker_node(state, document) if in_marker else state.node,
                        include)
            return

        site_path = list(state.path)
        homes = []
        structural = False
        for candidate in files:
            home, holds_structure = self.convert_fragment(candidate, document, site_path,
                                                          state.marker)
            structural = structural or holds_structure
            if home is not None and home not in homes:
                homes.append(home)
        if not homes:
            homes = [site_path]
        if len(homes) > 1:
            document.warn(f'{where}: the files of {pattern} belong at different levels; one '
                          '_include_ per level is written (CHECK)')

        for index, home in enumerate(homes):
            node = include if index == 0 else Node('include', value=yaml_pattern)
            if home == site_path:
                # The clean case: the fragment is relative to where it sits.
                # Inside an open marker only if it is adds -- a fragment that
                # is structure was read by the old parser after its first
                # address line had cleared the marker, so its content never
                # landed there; it goes in the section, where the loader can
                # read it.
                if in_marker and not structural:
                    self._place(state, document, self._marker_node(state, document), node)
                else:
                    if in_marker:
                        node.note = (f'CHECK: the marker {state.marker!r} was open when this '
                                     'was included, but the fragment is structure, which the '
                                     'old parser read after clearing the marker; placed in '
                                     'the section')
                        document.warn(f'{where}: include moved out of marker {state.marker!r} '
                                      '(the fragment is structure; CHECK)')
                    self._place(state, document, state.node, node)
                continue
            # The fragment addressed a level above its include, or another
            # top-level section: re-home the include there, as the
            # hand-translated corpus did.
            parent = state.top
            for address in home:
                parent = self._enter(parent, address, document, where, create_new=False)
            node.note = (f'CHECK: {pattern} addresses {".".join(home) or "the document"} '
                         f'rather than the including {".".join(site_path) or "document"}; '
                         'the include was moved here')
            self._place(state, document, parent, node)
            document.warn(f'{where}: {pattern} addresses {".".join(home) or "the top level"}; '
                          'include moved there (CHECK)')

    def _resolve(self, base, pattern, is_glob, document, where):
        """The files an include names: beside the including document, else
        under its datadir (the old parser tried both)."""
        def found(at):
            paths = sorted(glob.glob(str(at / pattern))) if is_glob else [str(at / pattern)]
            return paths if paths and all(Path(p).exists() for p in paths) else None
        paths = found(base)
        if paths is None:
            datadir = document.settings.get('datadir', "'.'").strip("'\"")
            paths = found(base / datadir)
            if paths is not None:
                document.warn(f'{where}: {pattern} found under datadir rather than beside '
                              'the document; an _include_ path is relative to the document')
        if paths is None:
            document.warn(f'{where}: {pattern} not found; the _include_ is written, '
                          'nothing is converted for it')
        return paths

    # -- output

    def render_root(self, document):
        out = []
        for node in document.head:
            if node.kind == 'comment':
                out.append(f'# {node.value}')
        if out:
            out.append('')
        out.append('_scriptum_:')
        document.settings.setdefault('version', '4')
        for key in KNOWN_SETTINGS:
            if key in document.settings:
                out.append(f'  {key}: {document.settings[key]}')
        for note in document.setting_notes:
            out.append(f'  # {note}')
        out.append('')
        if document.globals:
            out.append('_global_:')
            seen = set()
            for node in document.globals:
                if node.kind == 'fill':
                    if node.address in seen:
                        out.append(f'  # CHECK: {node.address} repeated under global; '
                                   f'a mapping holds it once -- dropped: {node.value}')
                        continue
                    seen.add(node.address)
                    out.append(f'  {yaml_key(node.address)}: {node.value}')
                elif node.kind == 'comment':
                    out.append(f'  # {node.value}')
                elif node.kind == 'blank' and out[-1] != '':
                    out.append('')
            if out[-1] != '':
                out.append('')
        out.append('_content_:')
        self._render(document.content.children, 2, out)
        return '\n'.join(out).rstrip('\n') + '\n'

    def render_fragment(self, entries, name):
        out = [f'# converted from {name}: a fragment, a bare sequence relative to '
               'where it is included']
        self._render(entries, 0, out)
        return '\n'.join(out).rstrip('\n') + '\n'

    def _render(self, children, indent, out):
        pad = ' ' * indent
        for node in children:
            if node.note:
                out.append(f'{pad}# {node.note}')
            if node.kind == 'blank':
                if out and out[-1] != '':
                    out.append('')
            elif node.kind == 'comment':
                out.append(f'{pad}# {node.value}')
            elif node.kind == 'fill':
                out.append(f'{pad}- {yaml_key(node.address)}: {node.value}')
            elif node.kind == 'include':
                out.append(f'{pad}- _include_: {yaml_text(node.value)}')
            elif node.kind in ('container', 'marker'):
                out.append(f'{pad}- {yaml_key(node.address)}:')
                self._render(node.children, indent + 4, out)


# ---------------------------------------------------------------- checking

def check(document_path):
    """Load the result the way Scriptum will; return the diagnostics text."""
    repo = Path(__file__).resolve().parents[1]
    for candidate in (repo.parent, repo):
        if str(candidate) not in sys.path:
            sys.path.append(str(candidate))
    try:
        from Scriptum.rdf.loader import DocumentError, load
    except ImportError:
        return 'Scriptum is not importable here; run scripts/check_rdf.py on the result'
    try:
        load(document_path)
    except DocumentError as error:
        return str(error)
    return ''


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Convert .rdf report data files to .yaml report documents -- '
                    'a starting point, to be finished by hand.')
    parser.add_argument('paths', nargs='+', type=Path, help='root .rdf file(s)')
    parser.add_argument('--out', type=Path, help='write the .yaml files into this directory')
    parser.add_argument('--force', action='store_true', help='overwrite existing .yaml files')
    parser.add_argument('--no-follow', action='store_true',
                        help='do not convert the files an &include names')
    parser.add_argument('--no-check', action='store_true',
                        help='do not load the result through Scriptum afterwards')
    args = parser.parse_args(argv)

    converter = Converter(follow=not args.no_follow, out_dir=args.out, force=args.force)
    exit_code = 0
    for path in args.paths:
        if not path.exists():
            print(f'{path}: not found')
            exit_code = 2
            continue
        document = converter.convert_root(path)
        print(f'{path}:')
        for target in converter.written:
            print(f'    wrote {target}')
        for target in converter.skipped:
            print(f'    kept  {target} (exists; --force to overwrite)')
        for warning in document.warnings:
            print(f'    CHECK {warning}')
        converter.written.clear()
        converter.skipped.clear()
        if not args.no_check:
            target = converter.target_path(path)
            if target.exists():
                report = check(target)
                if report:
                    print('    the result does not load yet:')
                    for line in report.splitlines():
                        print(f'        {line}')
                    exit_code = max(exit_code, 1)
                else:
                    print(f'    {target.name} loads without diagnostics')
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
