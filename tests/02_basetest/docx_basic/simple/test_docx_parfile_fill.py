"""A parameter-file value in a Word paragraph renders the parameter.

``ManagedDocx.fillGeneric`` wrote ``str(value.load())`` into the run -- and
``Value.load()`` returned None, so the word *None* went into the document
where the parameter belonged. The case tests never saw it: they assert that a
file was written, not what it says. This one reads the paragraph back.
"""

from pathlib import Path
import shutil
import sys

import pytest

docx = pytest.importorskip('docx')

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = THIS_DIR.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT))

from _setup_docx_basic import *          # noqa: F401,F403

DOCUMENT = """_scriptum_:
  version: 4
  documenttype: docx
  datadir: ./data
_content_:
  - section:title:
      - report:product_name: {parfile: product.nv, parameter: Title}
      - date:creation: {parfile: product.nv, parameter: Modified}
"""


def test_a_parfile_value_renders_the_parameter_not_none(tmp_path, monkeypatch):
    import Scriptum

    shutil.copy(THIS_DIR / 'template.docx', tmp_path)
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'product.nv').write_text(
        'Title:WhatEver-F1\nModified:1566996265000\n', encoding='utf-8')
    (tmp_path / 'case.yaml').write_text(DOCUMENT, encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    rdf = Scriptum.ReportDataFile('case.yaml')
    document = Scriptum.ManagedDocx('template.docx', rdf)
    document.typesetting(rdf)
    document.save('out.docx')

    # The title page of template.docx keeps <report:product_name/> in a table
    # cell, so read the cells as well as the paragraphs.
    finished = docx.Document('out.docx')
    said = [p.text for p in finished.paragraphs]
    for table in finished.tables:
        said.extend(cell.text for row in table.rows for cell in row.cells)
    assert any('Product: WhatEver-F1' in text for text in said), said
    assert not any('None' in text for text in said), said
