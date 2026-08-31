"""Paragraph template helpers."""

from copy import deepcopy
import re

from .element import PptTextElement
from ..base import paintRun
from ..template_utils import (
    compute_template_bounds,
    resolve_template_box,
)
from ...tag.tag import RECOMPILEFLAGS
from ...element.base import replaceTextInRuns
from ...tag.tag import getReTag

debug = True

jumpingfox = 'The quick brown fox jumps over the lazy dog'
foxre = re.compile(jumpingfox, flags=RECOMPILEFLAGS)


class TextTemplate:
    """A template describing how to duplicate text elements.
    where the shapes could be either a list with 
    - a single shape
    - multiple shapes
    groupshapes do not exist anymore on this level, so we have to compute overall
    top, left, width, height from all shapes
    """

    def __init__(self, shapes):
        
        self.elements = shapes

        bounds = compute_template_bounds(shapes)
        self.top = bounds.top
        self.left = bounds.left
        self.width = bounds.width
        self.height = bounds.height

        for element in self.elements:
            element.storeAttributes()
            element.attrs.top -= self.top
            element.attrs.left -= self.left

    def copyAndFill(self, slide, baseshape, value, actions) -> None:
        """do the full copy and fill operation
        this will return nothing as it fills all content

        slide - the slide to place content on
        baseshape - the shape that defines the size 
        actions - defined actions from rdf that may modify positions or contain more
        value - the main value object, here a table-value
        """

        box = resolve_template_box(
            baseshape,
            self.width,
            self.height,
            actions,
            default_width="available",
            default_height="available",
        )

        value.load()

        if value.type == 'file' and not value.object.exists:
            # need to define the fail action
            warning = f"non existing text file {value.object.filename!r}"
        else:
            warning = False

        for element in self.elements:
            attrs = element.attrs

            element_top = int(box.top) + attrs.top
            element_left = int(box.left) + attrs.left

            # we do not scale it, but we may reduce the width if not enough space
            element_width = min(attrs.width, box.width-attrs.left)
            element_height = attrs.height

            shape = slide.shapes.add_textbox(
                element_left, element_top, element_width, element_height
                )
            
            #print('1', shape.text)

            copiedtags = deepcopy(element.tags)
            text_frame = shape.text_frame
            text_frame.paragraphs[0].text = element.thing.text_frame.text

            #print('2', shape.text)

            oldre = getReTag(copiedtags[0])
                
            # the main element is the one without a "child"

            if not element.tags[0].child:
                # in this case we take the content from value
                content = str(value.object.content)
                if jumpingfox in element.thing.text_frame.text:
                    # this happens only in the first paragraph
                    replaceTextInRuns(text_frame.paragraphs[0].runs, shape.text, foxre,'')
                #print('3', shape.text)
                

            else:
                content = str(actions.get(element.tags[0].child,'undefined'))

            #print('4', shape.text, content)
            written = replaceTextInRuns(
                text_frame.paragraphs[0].runs, shape.text, oldre, content
                )
            #print('5', shape.text)
            attrs.setFontAttrs(text_frame)
            if not element.tags[0].child:
                # a color modifier paints the main text; child elements
                # (descriptions and friends) keep the template's own style
                paintRun(written, actions)
