# part of:
#   S C R I P T U M 

from pptx.presentation import Presentation

from pptx.oxml.slide import CT_SlideLayout
from pptx.enum.shapes import PP_PLACEHOLDER_TYPE, MSO_SHAPE_TYPE

# The slide namespace table now lives in `rdf`, which must not depend on
# this package -- see rdf/namespaces.py. Re-exported here so existing
# imports keep working.
from ..rdf.namespaces import pptx_sections

class PPTXTypes:
    CT_SlideLayout = CT_SlideLayout
    Presentation = Presentation       

known_placeholder_types = {
    PP_PLACEHOLDER_TYPE.PICTURE: 'image',
    PP_PLACEHOLDER_TYPE.SLIDE_IMAGE: 'image',
    PP_PLACEHOLDER_TYPE.CENTER_TITLE: 'text',
    PP_PLACEHOLDER_TYPE.TITLE: 'text',
    PP_PLACEHOLDER_TYPE.SUBTITLE: 'text',
    PP_PLACEHOLDER_TYPE.BODY: 'text',
    PP_PLACEHOLDER_TYPE.TABLE: 'table',
    PP_PLACEHOLDER_TYPE.CHART: 'unsupported', #'chart',
    PP_PLACEHOLDER_TYPE.ORG_CHART: 'unsupported', #'smartart',
    PP_PLACEHOLDER_TYPE.MEDIA_CLIP: 'unsupported', #'media',
    PP_PLACEHOLDER_TYPE.BITMAP: 'unsupported', #'clipart',
    PP_PLACEHOLDER_TYPE.DATE: 'unsupported', #'date',
    PP_PLACEHOLDER_TYPE.FOOTER: 'unsupported', #'footer',
    PP_PLACEHOLDER_TYPE.HEADER: 'unsupported', #'header',
    PP_PLACEHOLDER_TYPE.SLIDE_NUMBER: 'unsupported', #'slidenumber',
    PP_PLACEHOLDER_TYPE.OBJECT: 'multiple', # it covers the case of many above
}

known_shape_types = {
    MSO_SHAPE_TYPE.AUTO_SHAPE: 'frame', #"AutoShape" - use it for images used in templates for now
    MSO_SHAPE_TYPE.CALLOUT: 'unsupported', # "Callout shape"
    MSO_SHAPE_TYPE.CANVAS: 'unsupported', # "Drawing canvas"
    MSO_SHAPE_TYPE.CHART: 'unsupported', #  "bar chart"
    MSO_SHAPE_TYPE.COMMENT: 'unsupported', #  "Comment"
    MSO_SHAPE_TYPE.DIAGRAM: 'unsupported', #  "Diagram"
    MSO_SHAPE_TYPE.EMBEDDED_OLE_OBJECT: 'unsupported', #  "Embedded OLE object"
    MSO_SHAPE_TYPE.FORM_CONTROL: 'unsupported', #  "Form control"
    MSO_SHAPE_TYPE.FREEFORM: 'unsupported', #  "Freeform"
    MSO_SHAPE_TYPE.GROUP: 'group', #  "Group shape"
    MSO_SHAPE_TYPE.IGX_GRAPHIC: 'unsupported', #  "SmartArt graphic"
    MSO_SHAPE_TYPE.INK: 'unsupported', #  "Ink"
    MSO_SHAPE_TYPE.INK_COMMENT: 'unsupported', #  "Ink Comment"
    MSO_SHAPE_TYPE.LINE: 'unsupported', #  "Line"
    MSO_SHAPE_TYPE.LINKED_OLE_OBJECT: 'unsupported', #  "Linked OLE object"
    MSO_SHAPE_TYPE.LINKED_PICTURE: 'unsupported', #  "Linked picture"
    MSO_SHAPE_TYPE.MEDIA: 'unsupported', #  "Media"
    MSO_SHAPE_TYPE.OLE_CONTROL_OBJECT: 'unsupported', #  "OLE control object"
    MSO_SHAPE_TYPE.PICTURE: 'image', #  "Picture"
    MSO_SHAPE_TYPE.PLACEHOLDER: 'placeholder', #  "Placeholder"
    MSO_SHAPE_TYPE.SCRIPT_ANCHOR: 'unsupported', #  "Script anchor"
    MSO_SHAPE_TYPE.TABLE: 'table', #  "Table"
    MSO_SHAPE_TYPE.TEXT_BOX: 'text', #  "Text box"
    MSO_SHAPE_TYPE.TEXT_EFFECT: 'unsupported', #  "Text effect"
    MSO_SHAPE_TYPE.WEB_VIDEO: 'unsupported', #  "Web video"
    MSO_SHAPE_TYPE.MIXED: 'unsupported', #  "Multiple shape types (read-only)"
}

__all__ = ['PPTXTypes', 
           'known_placeholder_types',
           'known_shape_types', 'pptx_sections']