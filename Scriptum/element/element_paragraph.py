#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

from typing import Any, Optional

from ..tag.tag import Tag, getReTag
from .base import Element, replaceTextInRuns

VISIBLE_CHARS = 20

class ParagraphElement(Element):
    """ParagraphElement class"""
    def __init__(self):
        """feed it with one element"""
        super().__init__()

    def __repr__(self) -> str:
        extra = f"--> {self.thing.text.encode('utf8')[:VISIBLE_CHARS]}..."
        return f'element of type paragraph : {self.id!r} {extra}'
                
    #def burntag(self,tag):
    #    """burn all tags named tag in that element"""
    #    for t in self.tags:
    #        if tag == t.puretag:
    #            t.burned = True

    #
    # replace tags
    #
    def replaceTag(self, tag: Tag, replace: str) -> Optional[Any]:# Optional[thing], but what is thing?
        """replace <tag>, </tag>, <tag/> 
        in a paragraph object with multiple runs, every run stays as it is.
        only the tag is replaced 
        replace will be added to first run, where tag start, only!
        
        do the replacement inline, 
        return "run" where the replace started
        used in docx but in pptx as well (tables, group shapes)
        """

        if tag.burned: # already done!
            return None
        
        # in a placeholder it is quite simple - it is always "empty"
        if hasattr(self.thing, 'is_placeholder') and self.thing.is_placeholder:
            self.thing.text = replace
            tag.burned = True
            return None
        
        # full text
        text = self.thing.text
        #ltext = len(text)
        tagre = getReTag(tag)

        return replaceTextInRuns(self.thing.runs, text, tagre, replace)

