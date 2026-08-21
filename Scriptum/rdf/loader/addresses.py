#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""Addresses: what an author writes, and the four slots it completes to.

An address has **four positional slots**, always in this order::

    namespace : name : child : id

Empty slots are kept, so the separator count is fixed and position -- not
content -- decides meaning. ``subsection:instruction::1`` carries no child;
``table:default:description:1`` does. Recovering the template address is
dropping the last field, which works only because the id is always last and
always an integer.

The four-slot form is **internal**. Authors and document templates keep the
short form and the loader completes it:

==============================  ==========================
authored                        canonical
==============================  ==========================
``head``                        ``:head::1``
``subsection:instruction``      ``subsection:instruction::1``
``table:default:description``   ``table:default:description:1``
``TitleSlide`` (pptx layout)    ``:titleslide::1``
==============================  ==========================

**A bare name leaves the namespace slot empty.** Not ``head:head::1``: keeping
the name in its own slot means the slots always mean the same thing. A tag
written ``<head/>`` sets namespace and name to the same word, which duplicates
the value and makes "is there a namespace?" unanswerable -- :attr:`puretag`
is where that shape is reproduced, and only there, because that is what has to
match the document.

Why the instance separator is ``:`` and not ``_``
-------------------------------------------------
``:`` is reserved as the segment separator, so it cannot occur inside a
segment and the template address is always recoverable by stripping the last
field. ``_`` is an ordinary name character: a template legitimately called
``figure_1`` would be indistinguishable from instance 1 of ``figure``, and
``global`` -- which has to split an instance address back to its template name
-- would be guessing.
"""

import re

#: A segment after lowercasing: letters, digits, ``_`` and ``-``, and never
#: opening with ``_`` or ``-``.
SEGMENT = re.compile(r'^[a-z0-9][a-z0-9_-]*$')

#: The **first** segment carries one more rule: it must begin with a letter.
#:
#: This is not a style preference, it is what the document template can hold.
#: The tag scanner's pattern begins ``[a-z]+``, so the first character of a tag
#: must be a letter -- ``<figure:2024/>`` is found and ``<2024/>`` is not
#: (measured, not read). An address that cannot be written as a tag is an
#: address nothing can ever match.
#:
#: It also reconciles two rules that look contradictory. *Address grammar* says
#: an address cannot start with a number; *Elements are sequences* says all-digit
#: names stay legal, because positional slots remove the need for any rule about
#: what a segment may contain. Both are true, of different segments: a **name**
#: may be all digits, an **address** may not begin with one.
FIRST_SEGMENT = re.compile(r'^[a-z][a-z0-9_-]*$')

#: Namespace of a marker entry. Spelled plainly rather than ``_marker_``
#: because it names a ``<marker:name/>`` tag the document template contains --
#: the author is naming something real, as with ``image:generic``.
MARKER_NAMESPACE = 'marker'

MAX_SEGMENTS = 3


class Address:
    """One address, in its four positional slots.

    ``id`` is ``None`` until the walk assigns one, and stays ``None`` for a
    marker: a marker names a position in the template rather than an instance
    in the output, so there is nothing to number. Two ``marker:content``
    entries in one section refer to the same tag.
    """

    __slots__ = ('namespace', 'name', 'child', 'id')

    def __init__(self, namespace, name, child='', id=None):
        self.namespace = namespace
        self.name = name
        self.child = child
        self.id = id

    # ------------------------------------------------------------- forms

    @property
    def template(self):
        """The blueprint address: the first three slots, empties kept."""
        return f'{self.namespace}:{self.name}:{self.child}'

    @property
    def canonical(self):
        """All four slots. ``subsection:instruction::1``."""
        return f'{self.template}:{"" if self.id is None else self.id}'

    @property
    def puretag(self):
        """As the matching tag is spelled in the document template.

        This is the one place the tag's own shape is reproduced: a bare name
        is just the name, because ``<head/>`` is what a template contains, and
        trailing empty slots are dropped rather than written.
        """
        if not self.namespace:
            return self.name
        if self.child:
            return f'{self.namespace}:{self.name}:{self.child}'
        return f'{self.namespace}:{self.name}'

    @property
    def is_marker(self):
        return self.namespace == MARKER_NAMESPACE

    def numbered(self, number):
        """A copy carrying an instance id."""
        return Address(self.namespace, self.name, self.child, number)

    def __eq__(self, other):
        if not isinstance(other, Address):
            return NotImplemented
        return self.canonical == other.canonical

    def __hash__(self):
        return hash(self.canonical)

    def __repr__(self):
        return f'Address({self.canonical})'

    def __str__(self):
        return self.canonical


def parse(text, node, source, diagnostics, path=()):
    """Parse an authored address. Returns ``None`` after reporting.

    The whole address is lowercased; values are not. That is unchanged from
    the text format, and it is what retires a real bug: modifier names were
    *not* lowercased there while addresses were, so a modifier written
    ``Description`` never bound to its ``description`` child and nothing said
    so. One rule for every key removes the class.
    """

    def report(message):
        diagnostics.error(message, node=node, filename=source.filename, path=path)

    if not isinstance(text, str) or not text.strip():
        report('an address must be text')
        return None

    lowered = text.strip().lower()

    if lowered.startswith('_'):
        report(f'{text!r} starts with "_", which is reserved for keys such as '
               '_scriptum_ and _include_. An address cannot begin with one.')
        return None

    segments = lowered.split(':')

    if len(segments) > MAX_SEGMENTS:
        report(f'{text!r} has {len(segments)} segments; an address has at most '
               f'{MAX_SEGMENTS} (namespace:name:child). The instance number is '
               'assigned by the loader and is never written.')
        return None

    for position, segment in enumerate(segments):
        if not segment:
            report(f'{text!r} has an empty segment. Empty slots are internal; '
                   'an authored address writes only the segments it has.')
            return None
        if not SEGMENT.match(segment):
            report(f'{segment!r} in {text!r} is not a valid segment: letters, '
                   'digits, "_" and "-", and not opening with "_" or "-".')
            return None
        if position == 0 and not FIRST_SEGMENT.match(segment):
            report(f'an address must begin with a letter, and {text!r} begins '
                   'with a digit. A document template could not hold it: the '
                   'tag scanner requires a tag to start with a letter, so '
                   '<figure:2024/> is found and <2024/> is not. A later '
                   'segment may be all digits.')
            return None

    if len(segments) == 1:
        # A bare name keeps the name slot and leaves the namespace empty.
        return Address('', segments[0])
    if len(segments) == 2:
        return Address(segments[0], segments[1])
    return Address(segments[0], segments[1], segments[2])


__all__ = ['Address', 'parse', 'SEGMENT', 'MARKER_NAMESPACE', 'MAX_SEGMENTS']
