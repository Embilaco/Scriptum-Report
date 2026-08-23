from _setup_parameter import *

from Scriptum.rdf.values.namevalues_value import NameValueReader, strToTime # pyright: ignore[reportMissingImports]

def test_parameter_case1(tmp_path) -> None:
    """Timestamp-like entries in *.nv files are converted using ``strToTime``."""

    document = write(
        tmp_path, "namevalue.yaml",
        """_scriptum_:
  version: 4
  documenttype: docx
_content_:
  - section:parameters:
      - position: {parfile: basic.nv, parameter: Modified}
""",
    )

    nv_path = write(
        tmp_path, 'basic.nv',
        """Title:WhatEver-F1
CreatedFrom:Variant B
Revision: 0815
FileIsOpen:0
Modified:1566996265000
this is a long text:'abc
def
geh
ijk'
"""
    )

    os.chdir(tmp_path)

    rdf = ReportDataFile('namevalue.yaml')

    task = next(t for t in rdf.tasks if t.target == 'position')
    task.value.load()

    assert task.value.content == 'Wed Aug 28 14:44:25 2019', f'AssertionError: value not correct: {task.value.content}'
