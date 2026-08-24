#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""Section namespaces -- the ladder a report document nests along.

A container in a report document is addressed ``namespace:name``, and which
namespace is legal at which depth depends on the document type: Word nests
sections, PowerPoint has only slides. Depth in ``_content_`` *is* depth in
this ladder, so the loader checks every container against the table for the
depth it sits at (``Scriptum/rdf/loader/entries.py``).

These tables used to live in the ``_docx`` and ``_pptx`` packages, which
forced ``rdf`` to import both back ends -- and therefore both python-docx
and python-pptx -- merely to read a document.  They describe the *address
grammar*, not the Office APIs, so they belong here.  ``rdf`` depends on
nothing outside itself; the back ends depend on ``rdf``.

Supporting another document type (LibreOffice, HTML, ...) means registering
a namespace here or through :func:`register_documenttype`. The loader reads
this registry and needs no change.

A namespace table has four keys:

``order``
    Namespace names, outermost first -- the ladder as a diagnostic spells it
    (``section > subsection > ...``).
``names``
    Depth -> namespace name: what a container at that depth must be called.
``mandatory``
    When true, a container at depth *n* must use ``names[n]`` (Word). When
    false, bare names are accepted too (PowerPoint, where a slide is
    addressed by its layout name).
``always_copy``
    Whether the template holds blueprints only. PowerPoint's holds layouts, so
    every mention of one means a new slide and the reuse question never
    arises. Word's holds real sections, so the first instance of an address
    fills the block already there and only later ones are clones.

    This is a property of the *format*, not of the ladder, which is why it is
    its own key rather than being inferred from ``mandatory`` -- the two happen
    to agree today and there is no reason they must.
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

# ``order`` must list EVERY level in ``names``. It previously read
# ``range(max(DOCX_SECTION_NAMES))``, which stops one short and silently
# dropped the deepest level: 'sub5section' validated as an absolute address
# (checked against ``names``) but was rejected as a relative one (checked
# against ``order``), and a sub5section structure never registered a
# sub-anchor on its parent in the docx tree. Derive it from the keys so the
# two tables cannot disagree again.
DOCX_SECTION_ORDER = [DOCX_SECTION_NAMES[i] for i in sorted(DOCX_SECTION_NAMES)]

docx_sections = {
    'order': DOCX_SECTION_ORDER,
    'names': DOCX_SECTION_NAMES,
    'mandatory': True,
    'always_copy': False,
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
    'always_copy': True,
}

# ----------------------------------------------------------- registry

#: Value of ``documenttype`` -> namespace table. Membership of this mapping
#: is what makes a ``documenttype`` valid, so the loader holds no list of
#: known formats of its own.
SECTION_NAMESPACES = {
    'docx': docx_sections,
    'pptx': pptx_sections,
}


def register_documenttype(documenttype, order, names, mandatory=True,
                          always_copy=False):
    """Make a new ``documenttype`` known to the loader.

    Intended for a back end that adds a format -- it registers its address
    grammar and the ``_scriptum_`` block accepts ``documenttype: <name>``
    from then on. The tables are copied, so a caller cannot mutate the
    registry by holding on to what it passed in.

    Returns the stored namespace table.
    """

    documenttype = documenttype.lower()
    SECTION_NAMESPACES[documenttype] = {
        'order': list(order),
        'names': dict(names),
        'mandatory': bool(mandatory),
        'always_copy': bool(always_copy),
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
