#!/usr/bin/env python3
#
# part of:
#   S C R I P T U M
#

from typing import Any, Dict

from .attrs import ShapeAttrs
from ..element import Element
from ..tag.tag import OPENING, CLOSING, Tag
from ..rdf.tasks import ReportTask
from typing import Any, Sequence, Union, Optional

class PptElement(Element):
    """all types of elements with some metadata for POWERPOINT documents
    unique ID - shape_id+layout/slidename
    highlevel element - python-pptx
    lowlever xml element - python-pptx, lxml
    objecttype:
        shape,
        ?table, 
        groupshape
    """
    def __init__(self, shape: Any):
        super(PptElement,self).__init__()
        #Element.__init__(self)
        self.id = shape.shape_id
        self.thing = shape
        self.isplaceholder = shape.is_placeholder
        self.tags = None
      
    def storeAttributes(self) -> None:
        """store attributes for future copy"""
        self.attrs = ShapeAttrs(self.thing)

def replaceById(text: str) -> str:
    """generate a unique ID from text
    
    @TODO: is that still required? cross check with function getSimpleTag! 
    """
    
    all = text.lower().replace(OPENING,'').replace(CLOSING,'').split()
    # this is from above
    #tagId = [all[0]]
    #for arg in all[1:]:
    #    tagId += [arg]            
    # thus
    tagId = ':'.join(all)
    return tagId



def extractFontAndDecorators(paragraph: Any) -> Dict[str, Any]:
    """extract everything required...
    tested for pptx only
    
    @todo: retest if really required!
    """
    rPr = paragraph._p.r_lst[0].get_or_add_rPr()
    
    fad = dict([ (name, val) for name, val in rPr.items() if name in ['sz','b','i','cap','u','strike']])
    fad['typeface'] = rPr.latin.typeface
    #fad['_par'] = paragraph
    fad['sz'] = int(fad['sz'])/100
    fad['b'] = bool(int(fad.get('b',0)))
    fad['i'] = bool(int(fad.get('i',0)))
    fad['alignment'] = paragraph.alignment
    return fad

def genericFill(
    elements: Union[Element, Sequence[Element]],
    task: ReportTask,
    onlyOne: bool = False,
) -> None:
    """decide the fill target on a single task
    the elements to fill in are identified
    maybe a structure or a single element

    ``elements`` is always normalized to an iterable so downstream
    processing can treat the input uniformly regardless of whether a
    single element or a sequence was passed.
    """
    if isinstance(elements, Element):
        iterable: list[Element] = [elements]
    else:
        iterable = list(elements)
    # the main action is given by task 
    target = task.target
    value = task.value
    #print(value, str(value), 'x%sx'%value, target)

    # find the correct element for images
    if value.type == 'file' and value.subtype == 'image':
        # image handling is somewhat different in pptx and docx
        # so match is either a pptx or a docx element object
        if match := findTargetAndTagInElements(target, iterable):
            # returned an element and a tag
            match[0].fillImage(match[1], task)
    
    elif value.type == 'file' and value.subtype == 'video':
        # video handling is somewhat different in pptx and docx
        # so match is either a pptx or a docx element object
        if match := findTargetAndTagInElements(target, iterable):
            # returned an element and a tag
            match[0].fillAnimation(match[1], task)

    elif value.type == 'file' and value.subtype == 'text':
        value.load()
        text = value.content
        for element in iterable:
            found = element.replaceTagInAll(target,text)
            if found and onlyOne:
                break

    elif value.type == 'parfile':
        value.load()
        for element in iterable:
            found = element.replaceTagInAll(target,value.content)
            if found and onlyOne:
                break

    elif value.type == 'float':
        val = str(value.object)
        for element in iterable:
            found = element.replaceTagInAll(target,val)
            if found and onlyOne:
                break

    else:
        val = str(value)
        #print('TEXT?', val)
        for element in iterable:
            found = element.replaceTagInAll(target,val)
            if found and onlyOne:
                break
    
    # finally look in the task modifier if there is any
    if task.modified:
        actions = task.actions 
        for ktag, action in actions.items():
            what = action.type
            val = action.object
            if what in ['str','datetime','int','float']:
                val = str(val)
                if match := findTargetAndTagInElements(ktag, iterable):
                    # returned an element and a tag
                    match[0].replaceAndBurnTag(match[1],val)

def findTargetAndTagInElements(
    target: str,
    elements: Sequence[Element],
) -> Union[tuple[Element, Tag], bool]:
    """find exactly one element and its tag that macthes the target
    This prevents us at this point to find possible multiple occurences of tag in the elements
    Which restricts for instance the tags to be unique in the given context!
    """
    match: Optional[Element] = None
    tag: Optional[Tag] = None
    for el in elements:
        for tag in el.tags:
            if tag.puretag == target:
                match = el
                break
        if match is not None:
            break
    else:
        print(f'WARNING: Target not identified: {target}')
        return False
    return (match, tag)

