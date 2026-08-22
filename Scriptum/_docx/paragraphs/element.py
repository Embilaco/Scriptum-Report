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


class DocTextBlockElement(StructuredElement):
    """Paragraph-only structure used for predefined text blocks.
    
    There is no internal tagging allowed for now!
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
        """Fill the element with a nothing
        
        a text block already contains everything"""

        #value = task.value
        #actions = task.actions

        self.structure[0][1].replaceTag(self.tag, '')
        self.tag.burn()

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

        newUnfoldedElements = []
        for element in newElements:
            newUnfoldedElements += [(None, element)] # ignore any inner tags

        etag = newElements[0].tags[0]
        
        mycopy = DocTextBlockElement(
            etag, newpath, parent, newUnfoldedElements, None
        )
        mycopy.explore()
    
        section.addressbook[".".join(mycopy.path)] = mycopy
        
        parent.structure.append(('text',mycopy))

        return mycopy

    def clean(self) -> None:
        """Clean the unused tags and paragraphs."""

        pass
        # for t, element in self.structure:
        #     if not t or t.burned:
        #         continue
        #     element.replaceTag(t, "")
        #     t.burn()
        #     element.deleteIfEmpty()

