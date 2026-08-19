from typing import Union

from pptx.util import Pt, Cm, Mm, Inches

units = {
    'cm': Cm,
    'mm': Mm,
    'pt': Pt,
    'in': Inches,
    'inch': Inches,
}

def InCm(value: Union[int, float]) -> float:
    return float(value)/Cm(1)

