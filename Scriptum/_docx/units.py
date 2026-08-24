from docx.shared import Inches, Pt, Cm, Mm
from typing import Any, Optional, Union

units = { 'cm': Cm,
          'mm': Mm,
          'pt': Pt,
          'in': Inches,
          'inch': Inches}

def InCm(value: Union[int, float]) -> float:
    return float(value)/Cm(1)

def convertFromLength(
    length, # length value
    ) -> Optional[Any]:
    """convert into pptx/docx units"""
    if length == None:
        return None
    myunit = length.object.unit
    myval  = length.object.value
    return units[myunit](myval)
