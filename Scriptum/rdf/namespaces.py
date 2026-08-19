#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""Section namespaces for the rdf address grammar.

An address in a report data file is a dotted path of ``namespace:name``
segments, and which namespaces are legal depends on the document type:
Word nests sections, PowerPoint has only slides.

These tables used to live in the ``_docx`` and ``_pptx`` packages, which
forced ``rdf`` to import both back ends -- and therefore both python-docx
and python-pptx -- merely to parse a text file.  They describe the *rdf
address grammar*, not the Office APIs, so they belong here.  ``rdf`` now
depends on nothing outside itself; the back ends depend on ``rdf``.

Supporting another document type (LibreOffice, HTML, ...) means registering
a namespace here or through :func:`register_documenttype`. The parser reads
this registry and needs no change.

A namespace table has three keys:

``order``
    Namespace names, outermost first. A relative address may descend
    exactly one level at a time; naming a shallower level truncates the
    current root back to it.
``names``
    Depth -> namespace name, used to validate an absolute address segment
    by segment.
``mandatory``
    When true, the segment at depth *n* must use ``names[n]`` (Word). When
    false, bare names are accepted too (PowerPoint, where a slide is
    addressed by its layout name).
"""

# --------------------------------------------------------------- docx

DOCX_SECTION_NAMES = {
    0: 'section',
    1: 'subsection',
    2: 'subsubsection',
    3: 'sub3section',
    4: 'sub4section',
    5: 'sub5section',
}

# NOTE -- reproduced verbatim from the previous definition, including its
# off-by-one: ``range(max(...))`` stops one short, so 'sub5section' appears
# in ``names`` but NOT in ``order``. That difference is observable:
# ``<sub5section:x>`` validates as an absolute address yet is rejected as a
# relative one, because relative resolution checks ``order``. Kept as-is so
# that moving these tables changes no behaviour; correcting the depth limit
# is a separate decision.
DOCX_SECTION_ORDER = [DOCX_SECTION_NAMES[i] for i in range(max(DOCX_SECTION_NAMES))]

docx_sections = {
    'order': DOCX_SECTION_ORDER,
    'names': DOCX_SECTION_NAMES,
    'mandatory': True,
}

# --------------------------------------------------------------- pptx

PPTX_SECTION_NAMES = {
    0: 'slide',
}

PPTX_SECTION_ORDER = ['slide']

pptx_sections = {
    'order': PPTX_SECTION_ORDER,
    'names': PPTX_SECTION_NAMES,
    'mandatory': False,
}

# ----------------------------------------------------------- registry

#: Value of ``*documenttype`` -> namespace table. Membership of this mapping
#: is what makes a ``*documenttype`` valid, so the parser holds no list of
#: known formats of its own.
SECTION_NAMESPACES = {
    'docx': docx_sections,
    'pptx': pptx_sections,
}


def register_documenttype(documenttype, order, names, mandatory=True):
    """Make a new ``*documenttype`` known to the rdf parser.

    Intended for a back end that adds a format -- it registers its address
    grammar and the parser accepts ``*documenttype=<name>`` from then on.
    The tables are copied, so a caller cannot mutate the registry by holding
    on to what it passed in.

    Returns the stored namespace table.
    """

    documenttype = documenttype.lower()
    SECTION_NAMESPACES[documenttype] = {
        'order': list(order),
        'names': dict(names),
        'mandatory': bool(mandatory),
    }
    return SECTION_NAMESPACES[documenttype]


__all__ = [
    'docx_sections',
    'pptx_sections',
    'SECTION_NAMESPACES',
    'register_documenttype',
    'DOCX_SECTION_NAMES',
    'DOCX_SECTION_ORDER',
    'PPTX_SECTION_NAMES',
    'PPTX_SECTION_ORDER',
]
