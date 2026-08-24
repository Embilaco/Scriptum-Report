"""Image-related element implementations for Word rendering."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, List, Mapping, Tuple

from ...rdf.values import ImageValue
from ...tag import Tag
from ..paragraphs import DocParagraphElement
from ..structure import StructuredElement
from ..template import copy_paragraph_before
from ..units import units, convertFromLength
from docx.image.exceptions import UnrecognizedImageError

class DocImageBlockElement(StructuredElement):
    """Image block representation wrapping one or more paragraphs."""

    HEADER = "IMAGE"

    def __init__(
        self,
        tag: Tag,
        path: List,
        parent: Any,
        content: List[Tuple[Tag, Any]],
        anchor: None,
    ) -> None:
        super().__init__(tag, path, parent, content, None)
        self.subtype = "paragraph" if len(content) == 1 else "structure"

    def fill(self, task) -> None:
        """Fill the element with a value."""

        value = task.value
        actions = task.actions
        value.load()

        #if self.subtype == 'structure':
        _structure = self.structure
        image_par = _structure[0][1]
        # else:
        #     _structure = self.structure[0][1].structure
        #     image_par = _structure[0][1]
        #print(type(self),type(image_par), self.subtype, self.tag.puretag)
        #print(self.tag.printable)
        #print(task._inspect())

        if value.object.exists:
            imagename = value.object.filename
            #print('IMF',value.object.filename)
            width, height = getSizeFrom(self.tag, value.object, actions, units=units)

            #print(imagename,width,height)
            found = image_par.replaceTag(self.tag, "")
            if found is None:
                # The tag is no longer in the paragraph: a header or footer
                # shared by linked sections is unfolded into each of them, so
                # a global fill meets the same paragraph once per section and
                # the first visit has already placed the picture.
                self.tag.burn()
                return
            try:
                found.add_picture(imagename, width=width, height=height)
            except UnrecognizedImageError:
                found.text = f'WARNING: python-docx cannot handle image "{imagename}"'

            for key, val in actions.items():
                for t, element in _structure:
                    if not t or t.burned:
                        continue
                    if key == t.puretag:
                        element.replaceTag(t, str(val))
                        t.burn()
        else:
            image_par.replaceTag(self.tag, str(value.object))

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
            numberTag(newElements[0], newElements[0].tags[0], newname,
                      selfclosing=self.subtype != "structure")

        newUnfoldedElements = []
        for element in newElements:
            if element.tags:
                for subt in element.tags:
                    newUnfoldedElements += [(subt, element)]
            else:
                newUnfoldedElements += [(None, element)]

        etag = newElements[0].tags[0]
        
        if self.subtype == 'structure':
            mycopy = DocImageBlockElement(
                etag, newpath, parent, newUnfoldedElements, None
            )
            mycopy.explore()
        
            if mycopy.subtype == 'structure':
                section.addressbook[".".join(mycopy.path)] = mycopy
        else:
            
            mycopy = DocImageBlockElement(
                etag, newpath, parent, [(etag,newElements[0])], None
            )
            mycopy.path = parent.path + [newname]
            mycopy.structure = [(etag,newElements[0])]
            # add this one into the parents structure
        
        parent.structure.append(('image',mycopy))

        return mycopy

    def clean(self) -> None:
        """Clean the unused tags and paragraphs."""

        for t, element in self.structure:
            if not t or t.burned:
                continue
            element.replaceTag(t, "")
            t.burn()
            try:
                element.deleteIfEmpty()
            except Exception as e:
                print(f'FAILED to delete element {e}')


def getSizeFrom(
    tag: Tag,
    image: ImageValue,
    actions: dict,
    units: Mapping[str, Any],
    ) -> Tuple[float, float]:
    """Extract the size from tag, actions, and image if possible."""

    width = tag.getLength("width", units) or convertFromLength(actions.get('width',None))
    height = tag.getLength("height", units) or convertFromLength(actions.get('height',None))
    scale = actions.get('scale')
    if scale:
        scale = scale.value
    scale = tag.getFloat("scale") or scale

    if scale and (width or height):
        print(f"Image: {image!r} - ignore scale={scale:5.2f} since width or height is set")
        scale = None

    image.content
    imagew, imageh = image.width, image.height
    imagew = units["pt"](imagew)
    imageh = units["pt"](imageh)
    ratio = imagew / imageh

    if scale:
        imagew = scale * imagew
        imageh = scale * imageh

    if not width and not height:
        width = imagew
        height = imageh
    elif width and not height:
        height = width / ratio
    elif height and not width:
        width = height * ratio

    return width, height


