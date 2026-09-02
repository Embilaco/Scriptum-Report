#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M 

#
from copy import deepcopy
from docx.text.paragraph import Paragraph
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.shared import Emu, Twips
from docx.table import Table

from ..tag.tag import getReTag, getTag

class Template:
    """a template is one of
    - Paragraph - quite simple from simple tagged entries and only from section:template
    - StructuredElement - consist of paragraphs and tables enclosed in open/close tags

    templates can be added to marker:content or to the end of a previous template (close-tag)
    """

    def __init__(self, ttype, element):

        if ttype == 'struct':
            self.type = 'struct'
            self.path = element.path
            _elements = []
            for p,t,e in element: # we need only the elements from now on, tags are derived again below
                if e not in _elements: _elements.append(e)
            # and we need them only once
            #self.elements = [ determineElement(e) for e in _elements ]   
            self.elements = _elements  

        else:
            self.type = 'simple'
            # simple tags are always in the template section, even if not ?
            # Canonical, like every other path in the tree.
            self.path = ['section:template::1', ttype.canonical]
            self.elements = [element]
            
    def inspect(self):
        """visualize the content of that element"""
        print(f'TEMPLATE (start): {self.type} path={self.path}')
        for elem in self.elements:
            print(f'  element: {elem}')
        print(f'TEMPLATE (end): {self.path}')

def numberTag(element, tag, canonical, selfclosing=False):
    """Number a cloned element's tag instead of renaming it.

    ``canonical`` is the new instance's four-slot address and its last slot is
    the number. The tag keeps the name the template wrote and gains ``id=N``,
    which is what keeps ``global`` -- matching on ``puretag`` -- reaching every
    clone: renaming made each one invisible to it.

    Only an opening (or self-closing) tag is numbered. Open and close are
    matched on ``puretag``, which is now untouched, so a closing tag needs
    nothing -- as in XML, where attributes belong to the opening tag.

    The replacement text is computed before the tag changes, because
    ``replaceTag`` has to match what is still written in the document.
    """
    instance = canonical.rsplit(':', 1)[-1] or '1'
    numbered = tag.withInstance(instance)
    element.replaceTag(tag, f'<{numbered}/>' if selfclosing else f'<{numbered}>')
    tag.setInstance(instance)


def copy_table_before(anchor_paragraph, source_table):
    """Return copy of `source_table`, inserted directly before `anchor_paragraph`."""
    #new_tbl = deepcopy(source_table._tbl)
    new_tbl = deepcopy(source_table)
    anchor_paragraph._p.addprevious(new_tbl)
    return Table(new_tbl, anchor_paragraph._parent)

def copy_paragraph_before(anchor_paragraph, source_paragraph):
    """Return copy of `source_paragraph`, inserted directly before `anchor_paragraph`."""
    #new_p = deepcopy(source_paragraph._p)
    new_p = deepcopy(source_paragraph)
    anchor_paragraph._p.addprevious(new_p)
    return Paragraph(new_p, anchor_paragraph._parent)

def add_page_break_before(anchor_paragraph):
    """Return newly |Paragraph| object containing only a page break."""
    paragraph = anchor_paragraph.insert_paragraph_before()
    paragraph.add_run().add_break(WD_BREAK.PAGE)
    return paragraph


# --------------------------------------------------------------- takeindent
#
# `<marker:content takeindent/>` -- the template saying *what is added here
# takes my indentation*. A blueprint carries the indent of wherever it was
# written, which for `section:template` is nowhere in particular, so content
# added at a nested marker used to land at the margin between two paragraphs
# well inside the subsection. The flag sits on the marker rather than on the
# block because the marker is the donor: one blueprint is added at many
# markers of many depths and only the marker knows which of them it is.
#
# Word only. A PowerPoint paragraph indents by `level`, an integer outline
# depth rather than a measurement, so the same word would mean something
# else there -- see the decision on the DOCX board.

def _asEmu(length):
    """A ``Length`` or ``None`` as a plain EMU count."""
    return 0 if length is None else int(length)


def _documentDefaultLeftIndent(paragraph):
    """The left indent from ``w:docDefaults``, the last place Word looks.

    python-docx exposes styles but not the document defaults, so this is the
    one step that has to read the XML itself.
    """
    try:
        styles = paragraph.part.styles.element
    except (AttributeError, KeyError, ValueError):
        return None
    path = '/'.join(qn(tag) for tag in
                    ('w:docDefaults', 'w:pPrDefault', 'w:pPr', 'w:ind'))
    ind = styles.find(path)
    if ind is None:
        return None
    left = ind.get(qn('w:left'))
    return None if left is None else Twips(int(left))


def effectiveLeftIndent(paragraph):
    """The left indent Word actually shows for *paragraph*, or ``None``.

    ``paragraph_format.left_indent`` reports **direct formatting only** and
    answers ``None`` both for *no indent at all* and for *inherited from the
    style* -- so a marker sitting in an indented style reads as flush left,
    and taking that at face value makes ``takeindent`` a silent no-op on
    every template that indents through its styles. The style chain and then
    the document defaults are therefore walked before giving up.
    """
    direct = paragraph.paragraph_format.left_indent
    if direct is not None:
        return direct

    style = paragraph.style
    seen = set()
    while style is not None and id(style) not in seen:
        seen.add(id(style))                    # a self-based style cannot loop
        fmt = getattr(style, 'paragraph_format', None)
        if fmt is not None and fmt.left_indent is not None:
            return fmt.left_indent
        style = getattr(style, 'base_style', None)

    return _documentDefaultLeftIndent(paragraph)


def _shiftTable(tbl, delta):
    """Move a cloned table by *delta* EMU, as ``w:tblInd``.

    python-docx has no table indent property, so the element is placed by
    hand -- ``w:tblInd`` belongs after ``w:tblCellSpacing`` and before
    ``w:tblBorders`` in ``w:tblPr``, and Word rejects a document whose
    properties are out of schema order.
    """
    tblPr = tbl.tblPr
    ind = tblPr.find(qn('w:tblInd'))
    if ind is None:
        current = 0
        ind = OxmlElement('w:tblInd')
        tblPr.insert_element_before(ind, 'w:tblBorders', 'w:shd', 'w:tblLayout',
                                    'w:tblCellMar', 'w:tblLook', 'w:tblCaption',
                                    'w:tblDescription', 'w:tblPrChange')
    else:
        # Anything but `dxa` is a width this cannot add to -- start from zero
        # rather than treat a percentage as twentieths of a point.
        current = int(ind.get(qn('w:w')) or 0) \
            if (ind.get(qn('w:type')) or 'dxa') == 'dxa' else 0

    ind.set(qn('w:type'), 'dxa')
    ind.set(qn('w:w'), str(max(0, current + Emu(delta).twips)))


def _saysSomething(paragraph):
    """True when the paragraph holds prose and not merely mark-up.

    Read through the tag grammar rather than a regex of its own, so a tag
    spelled in a way this module has never heard of still counts as mark-up.
    """
    text = paragraph.text
    for tag in getTag(text):
        text = getReTag(tag).sub('', text)
    return bool(text.strip())


def takeIndentFrom(marker, nodes):
    """Shift freshly cloned *nodes* to sit where the *marker* paragraph sits.

    The shift is **relative**: every element moves by the same delta -- the
    marker's indent less the block's own first line -- so a block that
    indents internally keeps its shape instead of being flattened onto one
    measurement. Setting them all to the marker's indent was the other
    reading, and it destroys the one thing a multi-paragraph block is for.

    The delta is measured from the first cloned paragraph that says something
    **of its own**, which is neither of the two that come first:
    ``breakbefore`` rides in front of a clone as an empty paragraph, and a
    block opens with the paragraph carrying ``<text:block>``, which holds
    nothing else and is deleted before the document ships. Measuring from
    either moves the block by the wrong amount -- and by an amount that looks
    right for as long as every blueprint sits at the margin.

    An indent is never driven negative. A block whose later lines sit further
    left than its first would otherwise be pushed into the margin, and no
    template asking to *take the marker's indentation* means that.
    """
    parent = marker._parent
    paragraphs = [(node, Paragraph(node, parent))
                  for node in nodes if isinstance(node, CT_P)]

    base = None
    for _node, paragraph in paragraphs:
        if _saysSomething(paragraph):
            base = effectiveLeftIndent(paragraph)
            break
    else:
        if paragraphs:
            base = effectiveLeftIndent(paragraphs[0][1])

    delta = _asEmu(effectiveLeftIndent(marker)) - _asEmu(base)
    if not delta:
        return

    for _node, paragraph in paragraphs:
        own = _asEmu(effectiveLeftIndent(paragraph))
        paragraph.paragraph_format.left_indent = Emu(max(0, own + delta))

    for node in nodes:
        if isinstance(node, CT_Tbl):
            _shiftTable(node, delta)


def nodesAddedBefore(anchor, previous):
    """The elements a clone just inserted in front of *anchor*.

    Every ``copy()`` in the back end inserts with ``addprevious`` and returns
    an element of its own shape -- a paragraph, a block, a structure -- so
    walking back from the anchor to whatever stood there before the copy is
    the one reading that works for all of them, tables and page breaks
    included. *previous* is ``anchor.getprevious()`` taken before the copy,
    and ``None`` when the anchor was the first child.
    """
    added = []
    node = anchor.getprevious()
    while node is not None and node is not previous:
        added.append(node)
        node = node.getprevious()
    added.reverse()
    return added

