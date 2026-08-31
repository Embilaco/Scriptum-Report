"""Paragraph-related element implementations for Word rendering."""

from __future__ import annotations

from typing import Any, List, Tuple

from ...element import ParagraphElement
from ...tag import Tag, getTag
from ..base import DocElement
from .. import wordtags
from copy import deepcopy
from ..template import copy_paragraph_before
from ..structure import StructuredElement

class DocParagraphElement(DocElement,ParagraphElement):
    """paragraphs only, the base element beside tables
    """
    def __init__(self, elem, path=[]):
        # init 
        ParagraphElement.__init__(self)
        DocElement.__init__(self,elem)
        self.type = 'paragraph'
        self.thing = elem
        self.path = path # for almost all paragraphs is this empty FIX?
        self.anchor = False

        # tags
        tags = getTag(elem.text)
        # first tag may contain a hint if that is a template
        #<subsection:preparation template breakbefore>....
        #? self.isTemplate = False
        if tags:
            t = tags[0] # do not allow this in mixed tags, template is always the first!
            if t.args and 'template' in t.args:
                self.isTemplate = True
            # clean comments
            for tag in tags:
                if tag.ns == 'comment':
                    self.replaceTag(tag,'')
                    tag.burn()
                elif tag.ns == 'marker':
                    self.tags += [tag] # we still keep those active
                else:
                    self.tags += [tag]

        self.content = elem.text
             
    def delete(self):
        """delete it from document"""
        p = self.thing._element
        if p.getparent() is not None:
            p.getparent().remove(p)
            p._p = p._element = None

    def deleteIfEmpty(self):
        #print('deleteIfEmpty',self.thing.text)
        if not self.thing.text:
            for r in self.thing.iter_inner_content():
                for d in r.iter_inner_content():
                    return # something is in, usually a drawing?
            else:
                self.delete()

    def createTemplate(self):
        """usually only required for the paragraphs in the template section"""
        self.deepcopy = [deepcopy(self.thing._p)]
        return self.deepcopy

    def copy(self, anchor, parent, newpath=[], newname='', section=None):
        """copy all elements just before the anchor,
        in case of self.type == 'struct', rename the first and last element if newname is set
        
        in this case we ignore section since we don't deliver a structure"""
        #print('newpath', newpath)
        newElement = DocParagraphElement(
                copy_paragraph_before(anchor.thing,  
                                        deepcopy(self.deepcopy[0])) # copy once again to keep template clean
                                )
        
        newElement.path = parent.path + [newname]
        if newname:
            from ..template import numberTag
            numberTag(newElement, newElement.tags[0], newname,
                      selfclosing=True)
            tag = newElement.tags[0]

        #print('\n tag rewritten\n',tag.puretag, tag.burned)
            
        # add this one into the parents structure
        parent.structure.append((tag,newElement))
        return newElement

def delete_paragraph(paragraph):
    """tested for docx only"""
    p = paragraph._element
    if p.getparent() is not None:
        p.getparent().remove(p)
        p._p = p._element = None

def delete_paragraph_if_empty(paragraph):
    """delete it if there is
    no text
    no drawing
    no oMath
    
    tested for docx only
    """
    if paragraph.text:
        return
    for c in paragraph._element.iterchildren():
        if c.find(wordtags['w:drawing']) is not None:
            return
    if paragraph._element.find(wordtags['m:oMath']) is not None:
        return
    delete_paragraph(paragraph)


def renderedText(tag, value):
    """The text *value* belongs to write, beyond its plain string form.

    ``None`` means ``str(value)`` already said it, which is the common case.
    A **file-backed** value is the exception that makes this worth naming: it
    stringifies to nothing until it is loaded, and then it is the file's
    *content* that belongs on the page -- or the message saying the file is
    not there. Get that wrong and the fill goes silently blank, which is what
    a placeholder carrying ``{file: ...}`` did before this was shared.

    Both callers are here on purpose: ``ManagedDocx.fillGeneric`` for a fill
    addressed on its own, and ``DocTextBlockElement.fill`` for a placeholder
    inside a text block. They replace the tag differently -- one by name
    across the element, one by the Tag object it already holds -- but what
    the value *says* must not depend on which of them asked.
    """
    if value.tostring:
        return None

    if value.type == 'file' and tag.tagtype in ('open', 'simple'):
        if not value.object.exists:
            return f'file {value.object.filename!r} not found'
        if value.subtype == 'text':
            return value.object.content
        if value.subtype == 'video':
            return (f'{value.object.filename!r}: videos cannot be added to a '
                    f'word document')
        if value.subtype == 'unclear':
            return f'{value.object.filename!r}: unclear what to do'
        # an image or a table places itself; nothing to write here
        return None

    if value.type == 'parfile':
        if not value.object.exists:
            return f'file {value.object.filename!r} not found'
        # load() fills value.content; reading it as the return value put the
        # word 'None' on the page once
        value.load()
        return str(value.content)

    return None


class DocTextBlockElement(StructuredElement):
    """A block of prose the template carries, with slots the document fills.

    The paragraphs are the template's -- that is the point of a text block --
    so the fill's own value has nothing to write. What a document supplies is
    the **placeholders** standing inside the block, and they arrive as the
    fill's modifiers, matched to the tags by the name the template spells:
    the mechanism an image block already uses for its ``description``.

    A placeholder may be namespaced (``<placeholder:one/>``) or bare
    (``<subtitle/>``); both are matched the same way. Namespaced is the safer
    habit, a bare name sharing its space with the source keys and the length
    modifiers -- see ``docs/tags.md``.
    """

    HEADER = "TEXTBLOCK"

    def __init__(
        self,
        tag: Tag,
        path: List,
        parent: Any,
        content: List[Tuple[Tag, Any]],
        anchor: None,
    ) -> None:
        super().__init__(tag, path, parent, content, None)
        self.type = "textblock"
        self.subtype = "text"

    def fill(self, task) -> None:
        """Write the document's placeholders into the block.

        The block's own tag goes first, then every modifier that names a tag
        standing inside it. A placeholder the document did not mention is
        left to :meth:`clean`, which blanks it -- a half-filled block ships
        without its markup showing rather than with an empty slot announced.
        """
        self.structure[0][1].replaceTag(self.tag, '')
        self.tag.burn()

        for name, value in (task.actions or {}).items():
            for tag, element in self.structure:
                if not tag or tag.burned or name != tag.puretag:
                    continue
                value.load()
                text = renderedText(tag, value)
                element.replaceTag(tag, str(value) if text is None else text)
                tag.burn()

    def copy(self, anchor, parent, newpath=None, newname="", section=None):
        """Copy all elements just before the anchor."""

        if newpath is None:
            newpath = []

        newElements = []
        for dc in self.deepcopy:
            newElements += [
                DocParagraphElement(
                    copy_paragraph_before(
                        anchor.thing, deepcopy(dc)
                    )
                )
            ]

        if newname:
            from ..template import numberTag
            numberTag(newElements[0], newElements[0].tags[0], newname)

        # The inner tags come along. They used to be dropped here -- every
        # element unfolded as (None, element) -- which made a placeholder
        # unaddressable and left the closing tag with nothing to pair it, so
        # it shipped as literal text at the end of the block.
        newUnfoldedElements = []
        for element in newElements:
            if element.tags:
                for subtag in element.tags:
                    newUnfoldedElements += [(subtag, element)]
            else:
                newUnfoldedElements += [(None, element)]

        etag = newElements[0].tags[0]
        
        mycopy = DocTextBlockElement(
            etag, newpath, parent, newUnfoldedElements, None
        )
        mycopy.explore()
    
        section.addressbook[".".join(mycopy.path)] = mycopy
        
        parent.structure.append(('text',mycopy))

        return mycopy

    def clean(self) -> None:
        """Blank whatever the document left unsaid.

        A placeholder no modifier named, and the block's closing tag, which
        pairs with nothing once the block is in place. Both are replaced with
        nothing and their paragraph dropped if that empties it -- so an
        unmentioned slot leaves no gap and no markup. Decided 2026-08-31: a
        text block is prose, and prose with a visible ``<placeholder:two/>``
        in it is worse than prose without the slot.
        """
        for t, element in self.structure:
            if not t or t.burned:
                continue
            element.replaceTag(t, "")
            t.burn()
            element.deleteIfEmpty()

