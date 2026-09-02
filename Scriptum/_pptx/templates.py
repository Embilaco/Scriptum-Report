#!/usr/bin/env python3
#
# part of:
#   S C R I P T U M 
#

from .images import ImageTemplate, AnimationTemplate
from .tables import TableTemplate
from .paragraphs import TextTemplate

def makeTemplate(shapes: list, ttype='__undefined__') -> dict:
    """create a template to be used further based on that shapes (non empty)
    return a dict such that we can enhance this further
    
    supported cases:
    
    ttype == group - this is a groupshape, -> (hasattr(shape,'shapes)) which can be 
        - a set of text boxes
        - text boxes mixed with auto_shapes (graphic objects, used as "dummy frames" for images)
        - text boxes mixed with images - need to implement to copy that (fixed) image
        - combinations of the above but not groupshapes of groupshapes - at least never tested
        - there are only images (usually one) or videos (usually one), but no mix of both in the same groupshape

    ttype == table - which is either -> tag.ns == table (same for all)
        tables cannot be grouped in a groupshape, which is a PPT limitation
        - a single table with a <table:foo/> tag in the first cell
        - multiple objects, where one is a table as above, the rest are text boxes with a <table:foo:bar/> tag
        - more complex was never tested

    ttype == image | ttype == video -> tag.ns == image|video (same for all)
        - single image/video shape
            or
        - handled in the same way as tables before in case there is no way to group that shape

    type == p|text -> tag.ns = p|text (same for all)
        - single paragraph
            or
        - handled in the same way as tables before in case there is no way to group that shape

    empty shapes-list or no tags in shapes are already excluded before!
    """

    template = {}

    if ttype == 'group':
        # groupshape
        # follow the rules above
        
        _tagnames = { tag.ns: tag.puretag for subshape in shapes for tag in subshape.tags }
        #print('tag names', _tagnames)
        if 'image' in _tagnames:
            # is an image template
            template[_tagnames['image']] = ImageTemplate(shapes)
        elif 'video' in _tagnames:
            # is an image template
            template[_tagnames['video']] = AnimationTemplate(shapes)
        elif 'p' in _tagnames:
            # seems only paragraphs?
            template[_tagnames['p']] = TextTemplate(shapes)  
        elif 'text' in _tagnames:
            # seems only texts?
            template[_tagnames['text']] = TextTemplate(shapes) 
        else:
            print(f'this looks like an unsupported template: {_tagnames!r}')
                
    elif ttype == 'table':
        # get the table in that ...
        for shape in shapes:
            if shape.thing.has_table:
                #table = shape.thing.table
                break
        # but we transfer all shapes
        template[shape.tags[0].puretag] = TableTemplate(shapes) # need to deepcopy table
    
    elif ttype in ('image', 'video'):
        # get the image or video in that ...
        for shape in shapes:
            if shape.type in ('image', 'video'):
                break
        # but we transfer all shapes
        template[shape.tags[0].puretag] = ImageTemplate(shapes) # need to deepcopy image
    
    elif ttype in ('p', 'text'):

        for shape in shapes:
            if shape.tags[0].child == None: 
                #is the master tag
                break
        # but we transfer all shapes
        template[shape.tags[0].puretag] = TextTemplate(shapes)  # need to deepcopy text

    
    elif ttype in ('size',):
        # yet not implemented but we stay quiet
        pass

    else: 
        print(f'WARNING: Template type is unknown is yet not implemented: {ttype!r}')
                
    return template

