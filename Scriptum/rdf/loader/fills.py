#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""A fill's value, and its modifiers.

A value is either a **scalar**, typed by YAML::

    - head: Serving             # the string
    - report:version: 1.0       # the float
    - rf2: ''                   # the empty string

or a **mapping** with exactly one source key, plus modifiers::

    - image:generic:
        file: instruction1.png
        description: instruction one
        width: 4cm

Quoting stops carrying type information, which retires the format's easiest
mistake: ``.head=Serving`` fell through to the literal-number branch and came
out ``invalid``, surfacing in the finished document rather than at parse time,
while ``.head='Serving'`` worked.

What still chooses the value *class* is the **target namespace** -- ``image:``,
``text:``, ``table:``, ``video:`` and the target ``color``. That is semantic
and deliberate, not a leftover of the line syntax: the mapping says where the
bytes come from, the namespace says what they are. For a bare name the name
itself is the selector, which is what ``target.split(':')[0]`` amounted to in
the text format.

Source keys and their companions
--------------------------------
============  ============================  =========================
source key    replaces                      companions
============  ============================  =========================
``file``      ``file:path``                 --
``parfile``   ``parfile:path:name``         ``parameter`` (required)
``date``      ``date:spec[:format]``        ``format``
``numbering`` ``numbering:kind:fmt[:start]``  ``format`` (required), ``start``
``from``      ``@row1``                     --
``text``      an explicit string            --
``rows``      *reserved, not implemented*   --
============  ============================  =========================

More than one source key in an entry is an error. Everything that is not the
source key or one of its companions is a modifier.

``file``, ``parfile``, ``text`` and ``from`` take text. ``date`` and
``numbering`` also take a number -- a timestamp, or the counter kind ``1`` --
because that is how an author naturally writes them and the value classes
take the parts as they are; the parts are never composed back into the text
format's ``date:spec:'fmt'`` / ``numbering:kind:fmt:start`` and re-split.

Lengths are recognised by modifier name
---------------------------------------
The text format decided a value was a length by looking at its last two
characters, anywhere it appeared, which cannot tell the measurement ``4cm``
from the string ``"4cm"``. The modifiers that take a length are a known set,
so **those names parse their value as a length and nothing else does**, and a
unit is mandatory: ``width: 4`` is an error rather than four of something
implied. Naming them is what makes that check possible at all -- the loader
knows a length was meant, so it can say the unit is missing.

``inch`` is accepted alongside ``cm``/``mm``/``in``/``pt``, closing a split
where the same spelling worked in one place and not the other: ``LengthValue``
has always understood it and ``Tag.getLength`` tests for it, so ``width=4inch``
worked in a template tag, while a value line tested only the last *two*
characters, so ``4inch`` ended in ``ch``, missed the length branch and fell
through to ``invalid``.
"""

import re

from ..values import (AnimationValue, ColorValue, DateValue, FileValue,
                      FloatValue, ImageValue, IntegerValue, LengthValue,
                      NameValue, NumberValue, StringValue, TableValue,
                      TextValue, Value)
from ..common import getCorrectFile
from .nodes import describe, is_mapping, is_null, is_scalar, is_sequence, items

#: In the order they are listed to an author who used none of them.
SOURCE_KEYS = ('file', 'parfile', 'text', 'date', 'numbering', 'from', 'rows')

#: source key -> keys that belong to it rather than being modifiers.
COMPANIONS = {
    'parfile': ('parameter',),
    'date': ('format',),
    'numbering': ('format', 'start'),
}

#: Modifier names whose value is a length. A closed set, which is the whole
#: reason a missing unit can be diagnosed instead of silently becoming a number.
LENGTH_MODIFIERS = frozenset({'width', 'height', 'top', 'left', 'bottom', 'right'})

UNITS = ('cm', 'mm', 'in', 'pt', 'inch')

LENGTH = re.compile(r'^[-+]?(?:\d+\.?\d*|\.\d+)\s*(?:cm|mm|in|pt|inch)$', re.I)

#: Target namespace -> the class that carries a file of that kind.
_FILE_CLASSES = {
    'image': ImageValue,
    'text': TextValue,
    'video': AnimationValue,
}


def selector_for(address):
    """The namespace that chooses the value class.

    A bare name has no namespace, so the name itself selects -- ``color`` is
    a colour, and that is what the text format's ``target.split(':')[0]``
    came to for a single-segment target.
    """
    return address.namespace or address.name


def read(node, selector, source, settings, diagnostics, path, modifiers=True):
    """Read one value. Returns ``(Value, actions)``, or ``(None, {})``.

    ``actions`` are the modifier values, already applied to the value object
    for the types that take them (tables read their caption from one).
    """
    if is_sequence(node):
        diagnostics.error(
            'a value cannot be a sequence: a sequence is a body, and a fill '
            'has none. Inline tabular data would take the mapping form.',
            node=node, filename=source.filename, path=path)
        return None, {}

    if is_mapping(node):
        return _from_mapping(node, selector, source, settings, diagnostics,
                             path, modifiers)

    value = _from_scalar(node, selector, source, settings, diagnostics, path)
    return value, {}


# ---------------------------------------------------------------- scalars

def _from_scalar(node, selector, source, settings, diagnostics, path):

    def report(message):
        diagnostics.error(message, node=node, filename=source.filename,
                          path=path)

    if selector == 'color':
        return _colour(node, report)

    raw = source.value(node)

    if raw is None:
        report('this needs a value. Note that a value starting with "#" is a '
               'YAML comment unless it is quoted.')
        return None

    if isinstance(raw, bool):
        report('true and false are not values this format uses. Quote it if '
               'you meant the word.')
        return None

    if isinstance(raw, str):
        return Value('str', StringValue(raw), tostring=True)
    if isinstance(raw, int):
        return Value('int', IntegerValue(raw), tostring=True)
    if isinstance(raw, float):
        return Value('float', FloatValue(raw, settings), tostring=True)

    report(f'{raw!r} is not a value this format knows')
    return None


def _colour(node, report):
    """A colour is read from the node's **raw text**, not its typed value.

    Under the 1.2 core schema an all-digit hex is an integer: ``123456``
    arrives as ``123456`` and -- worse -- ``012345`` as ``12345``, the leading
    zero gone and the colour silently wrong. The node still holds exactly what
    was written, so reading that makes YAML's typing irrelevant here.

    Which is what lets the ``#`` be dropped. ``ColorValue`` has always treated
    it as optional, but without this a bare hex would sometimes be a string and
    sometimes a mangled number, so ``ff0000`` is now simply the way to write
    one -- and it needs no quoting, where ``#ff0000`` does: unquoted, the
    ``#`` makes the rest of the line a YAML comment.

    An unrecognised colour is **reported**. ColorValue still degrades to black,
    because a colour has nowhere to put an explanatory sentence, but the
    fallback was previously the whole story: a typo produced a black element
    and nothing anywhere said why. The loader has a diagnostic channel, so it
    uses it.
    """
    written = node.value.strip() if isinstance(node.value, str) else ''

    if not written:
        report('a colour needs a value. Note that "#ff0000" unquoted is a '
               'YAML comment -- write ff0000, which needs no quoting.')
        return None

    colour = ColorValue(written)
    if not colour.valid:
        hint = ''
        if written.lower().startswith('rgb(') and not written.endswith(')'):
            hint = (' Inside a flow mapping {...} the commas in rgb(...) split '
                    'it into separate entries, so it must be quoted there.')
        report(f'{written!r} is not a colour. Write a name (red, steelblue), '
               'six hex digits with or without "#" (ff0000), or rgb(255,0,0).'
               f'{hint}')
        return None

    return Value('color', colour, tostring=False)


# ---------------------------------------------------------------- mappings

def _from_mapping(node, selector, source, settings, diagnostics, path,
                  modifiers):

    def report(message, at=node):
        diagnostics.error(message, node=at, filename=source.filename, path=path)

    pairs = items(node, source, diagnostics, path)
    if not pairs:
        if not node.value:
            report('this needs a value')
        return None, {}

    entries = {key.lower(): (key, key_node, value_node)
               for key, key_node, value_node in pairs}

    found = [key for key in entries if key in SOURCE_KEYS]
    if not found:
        report('a value needs one source key: '
               f'{", ".join(SOURCE_KEYS)}. Found {", ".join(sorted(entries))}.')
        return None, {}
    if len(found) > 1:
        written = ', '.join(sorted(found))
        report(f'a value has one source key, not {len(found)}: {written}. '
               'Which of them the bytes come from is not decidable.',
               at=entries[sorted(found)[1]][1])
        return None, {}

    key = found[0]
    companions = COMPANIONS.get(key, ())

    # A companion of a source that is not the one used says so plainly,
    # rather than being silently treated as a modifier and ignored.
    for other, names in COMPANIONS.items():
        if other == key:
            continue
        for name in names:
            if name in entries and name not in companions:
                report(f'{name!r} belongs to {other!r}, which this value does '
                       f'not use', at=entries[name][1])

    value = _build(key, entries, selector, source, settings, diagnostics, path,
                   report)
    if value is None:
        return None, {}

    consumed = {key, *companions}

    if not modifiers:
        # A modifier's own value takes a source and nothing else. Saying so is
        # the point: silently ignoring the extra keys would drop what the
        # author wrote, which is the failure mode this format exists to end.
        for name in entries:
            if name in consumed:
                continue
            report(f'{name!r} is a modifier of a modifier. A modifier takes a '
                   'source and no modifiers of its own -- one attached here '
                   'would hang where nothing reads it.', at=entries[name][1])
        return value, {}

    actions = _read_modifiers(entries, consumed, source, settings, diagnostics,
                              path, report)
    if actions:
        value.applyActions(actions)
    return value, actions


def _build(key, entries, selector, source, settings, diagnostics, path, report):
    _, _, value_node = entries[key]

    def scalar(name, required=True):
        """A companion's text, or None."""
        if name not in entries:
            if required:
                report(f'{key!r} needs {name!r}')
            return None
        node = entries[name][2]
        if not is_scalar(node) or is_null(node):
            report(f'{name!r} must be a single value, not {describe(node)}',
                   at=node)
            return None
        return source.value(node)

    if key == 'rows':
        # Checked before the shape, so inline table data -- which is naturally
        # written as a sequence -- gets told it is reserved rather than told
        # its sequence is the wrong shape.
        report('inline table data is reserved but not implemented; load the '
               'table from a file with "file:" for now', at=value_node)
        return None

    if not is_scalar(value_node) or is_null(value_node):
        report(f'{key!r} takes a single value, not {describe(value_node)}',
               at=value_node)
        return None

    written = source.value(value_node)
    if isinstance(written, str):
        written = written.strip()
    # A timestamp or the counter kind 1 is a number to an author and to the
    # value class alike; everything else takes text.
    takes_numbers = key in ('date', 'numbering') and not isinstance(written, bool)
    if not (isinstance(written, str) and written) \
            and not (takes_numbers and isinstance(written, (int, float))):
        report(f'{key!r} needs text', at=value_node)
        return None

    if key == 'file':
        return _file(written, selector, settings)

    if key == 'parfile':
        parameter = scalar('parameter')
        if parameter is None:
            return None
        filename, exists = getCorrectFile(written, False, settings.datadir)
        object = NameValue(filename, exists, settings, str(parameter))
        return Value('parfile', object, tostring=False,
                     subtype=object.subtype)

    if key == 'text':
        return Value('str', StringValue(written), tostring=True)

    if key == 'from':
        # Meaningful as a table modifier: the caption is read out of the table
        # itself. The name is lowercased, as it was when written '@row1'.
        return Value('readfrom', written.lower(), tostring=False)

    if key == 'date':
        return _date(written, entries, scalar, settings, report, value_node)

    return _numbering(written, entries, scalar)


def _file(written, selector, settings):
    filename, exists = getCorrectFile(written, False, settings.datadir)
    if selector == 'table':
        object = TableValue(filename, exists, settings)
    else:
        object = _FILE_CLASSES.get(selector, FileValue)(filename, exists)
    return Value('file', object, tostring=False, subtype=object.subtype)


def _date(written, entries, scalar, settings, report, value_node):
    """A :class:`DateValue` from its parts: the spec, and the pattern beside it.

    Nothing is composed. The text format packed the two into ``date:spec:'fmt'``
    and DateValue split it again on ``:`` -- which, once YAML had consumed the
    quotes around a date string, split the time inside it too
    (``'12/15/22 14:24:59'`` read as 14:00 with the pattern ``24:59``). The
    parts go to the class as parts.

    **What does not read as a date is refused here, not degraded.** DateValue
    keeps the house rule of never raising -- an unreadable spec becomes the
    epoch, a pattern strftime rejects falls back to ``dateformat`` -- but it
    flags both (``valid``, ``problem``), and a document is the one place where
    silently printing ``01. Jan 1970`` is worse than stopping: three translated
    fixtures did exactly that for a pattern written in the ``date`` slot before
    anyone noticed. So the common fingerprints are named, with the form that
    was meant, and the rest is reported as DateValue words it.
    """
    pattern = None
    if 'format' in entries:
        pattern = scalar('format', required=False)
        if pattern is None:
            return None
        if not isinstance(pattern, str) or not pattern.strip():
            report("'format' needs text: a strftime pattern such as "
                   "'%d. %b %Y -- %H:%M:%S'", at=entries['format'][2])
            return None

    if isinstance(written, str) and '%' in written:
        report(f"{written!r} looks like a strftime pattern written in the "
               "'date' slot. 'date' takes what to evaluate -- now, today, a "
               "timestamp or a date -- and the pattern goes beside it: "
               f"{{date: today, format: {written!r}}}", at=value_node)
        return None

    date = DateValue(written, settings, format=pattern)
    if not date.valid:
        report(date.problem, at=value_node)
        return None
    return Value('datetime', date, tostring=True)


def _numbering(written, entries, scalar):
    """A :class:`NumberValue` from its parts: kind, format and start.

    Nothing is composed, so a ``:`` in the format is just a character --
    the text format's ``numbering:kind:format[:start]`` could not say that.
    """
    pattern = scalar('format')
    if pattern is None:
        return None

    start = None
    if 'start' in entries:
        start = scalar('start', required=False)
        if start is None:
            return None

    return Value('numbering', NumberValue(written, str(pattern), start),
                 tostring=True)


# --------------------------------------------------------------- modifiers

def _read_modifiers(entries, consumed, source, settings, diagnostics, path,
                    report):
    actions = {}
    for name, (written, key_node, value_node) in entries.items():
        if name in consumed:
            continue

        if name in LENGTH_MODIFIERS:
            value = _length(name, value_node, source, settings, diagnostics,
                            path)
        else:
            # A modifier's own selector is its namespace, so 'image:poster'
            # carries an image. Nested modifiers are refused: a modifier of a
            # modifier would be attached where nothing reads it.
            value, _ = read(value_node, name.split(':')[0], source, settings,
                            diagnostics, path + (written,), modifiers=False)

        if value is not None:
            actions[name] = value
    return actions


def _length(name, node, source, settings, diagnostics, path):

    def report(message):
        diagnostics.error(message, node=node, filename=source.filename,
                          path=path)

    if not is_scalar(node) or is_null(node):
        report(f'{name} is a length, not {describe(node)}')
        return None

    written = source.value(node)
    if not isinstance(written, str) or not LENGTH.match(written.strip()):
        report(f'{name} needs a length with a unit: {", ".join(UNITS)}. '
               f'Got {written!r}.')
        return None

    object = LengthValue(written.strip())
    object.floatformat = settings.floatformat
    return Value('length', object, tostring=True)


__all__ = ['read', 'selector_for', 'SOURCE_KEYS', 'COMPANIONS',
           'LENGTH_MODIFIERS', 'UNITS']
