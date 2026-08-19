#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

from ..tag.tag import Tag
from .base import Element
from .element_paragraph import ParagraphElement

# generic class that can work on tables 

class ImageElement(Element):
    """ImageElement class"""
    def __init__(self):
        """feed it with one element"""
        super().__init__()

    def __repr__(self) -> str:
        return f'element of type image: {self.id!r}'
        
    #
    # replace tags
    #
    @staticmethod
    def replaceTag(object: "ImageElement", tag: Tag, replace: str) -> None:
        image = object.thing
        print('to be implemented')
        return None        

