# part of:
#   S C R I P T U M 

from docx.oxml.ns import qn

# The section namespace table now lives in `rdf`, which must not depend on
# this package -- importing a back end just to parse a text file is what
# made `import Scriptum` require both python-docx and python-pptx. See
# rdf/namespaces.py. Re-exported here so existing imports keep working.
from ..rdf.namespaces import docx_sections

wordtags = { 'w:instrText': qn('w:instrText'),
             'w:drawing': qn('w:drawing'),
             'm:oMath': qn('m:oMath'),
             'w:sdtContent': qn('w:sdtContent') }

__all__ = ["wordtags", 'docx_sections']
