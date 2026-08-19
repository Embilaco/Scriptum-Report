import sys
#import pytest
#from pathlib import Path
#from tempfile import TemporaryDirectory

from _setup_rdf import *

def test_include_cycle(tmp_path):
    p = tmp_path
    a = p / "A.rdf"
    b = p / "B.rdf"
    a.write_text(f"""*version=3
*documenttype=pptx
&include=file:{b}
""")
    b.write_text(f"""*version=3
*documenttype=pptx
&include=file:{a}
""")
    with pytest.raises(Exception) as excinfo:
        ReportDataFile(str(a))
    assert str(excinfo.value) in f"&include cycle detected: {a.resolve()}"

