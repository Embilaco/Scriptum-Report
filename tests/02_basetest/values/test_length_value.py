# tests different data formats

import sys
import types
from datetime import datetime

from _setup_values import  *

def test_length_units(tmp_path):
    base = tmp_path / "testLength.rdf"
    base.write_text("\n".join([
        "*version=100",
        "*documenttype=docx",
        "section:mysection.subsection:foo",
        ".inch=1in",
        ".centimeter=12.3cm",
        ".point=15pt",
        ".millimeter=123.56mm",
        ".wrong=123.3.4mm",
        ".kilometer=12km"]))
    
    rdf = ReportDataFile(str(base), _root=[])
    inch = next(t for t in rdf.tasks if t.target == "inch").value.object
    assert repr(inch) == "1.0 - unit: in"
    inch = next(t for t in rdf.tasks if t.target == "centimeter").value.object
    assert repr(inch) == "12.3 - unit: cm"
    inch = next(t for t in rdf.tasks if t.target == "point").value.object
    assert repr(inch) == "15.0 - unit: pt"
    inch = next(t for t in rdf.tasks if t.target == "millimeter").value.object
    assert repr(inch) == "123.56 - unit: mm"
    wrong = next(t for t in rdf.tasks if t.target == "wrong").value.object
    assert "cannot evaluate length:" in repr(wrong)
    invalid = next(t for t in rdf.tasks if t.target == "kilometer").value
    #print(invalid)
    assert invalid.type == "invalid" 
    assert "invalid decimal literal" in str(invalid)

