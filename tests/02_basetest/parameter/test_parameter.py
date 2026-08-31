from datetime import datetime

from _setup_parameter import *

from Scriptum.rdf.values.namevalues_value import NameValueReader, strToTime # pyright: ignore[reportMissingImports]

#: The ``Modified`` stamp written into the .nv fixture below, and the instant
#: it stands for: 2019-08-28 12:44:25 UTC, which is 14:44:25 in CEST.
MODIFIED = 1566996265


def test_parameter_case1(tmp_path) -> None:
    """Timestamp-like entries in *.nv files are converted using ``strToTime``.

    In two halves, because only one of them reads the same on every machine.
    """

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

    # The *instant* is absolute, and is pinned as one: thirteen digits are
    # milliseconds, and the datetime that comes back stands for exactly that
    # second, wherever the clock is set.
    assert strToTime(f'{MODIFIED}000').timestamp() == MODIFIED

    # The *rendering* is naive local time by decision -- `now` is the local
    # clock, a timestamp is converted to it, and no time zone is ever
    # attached (DateValue, docs/rdf.md). So the text depends on where the
    # report is built: 14:44:25 in CEST, 12:44:25 on a UTC runner. Asserting
    # either one pins the author's machine, which is what this line did until
    # the first CI run said so. What holds everywhere is that the fill
    # rendered *that* instant with datetimeformat, whose default is ISO 8601
    # (it was '%c': 'Wed Aug 28 14:44:25 2019').
    expected = datetime.fromtimestamp(MODIFIED).strftime('%Y-%m-%d %H:%M:%S')
    assert task.value.content == expected, f'value not correct: {task.value.content}'
