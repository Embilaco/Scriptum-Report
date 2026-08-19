# tests different data formats

import sys
import types
from datetime import datetime

from _setup_values import  *

def test_tables(monkeypatch: MonkeyPatch, tmp_path: Path):

    workdir = tmp_path / "workspace"
    workdir.mkdir()

    ensure_link(DATA_SOURCE, workdir / "data")

    base = workdir / "testTable.rdf"
    base.write_text("""
    *version=100
    *documenttype=docx
    *datadir=./data
    section:new
    .table:generic=file:table1.csv
    .table:generic=file:table1.csv+description=@row1
    .table:generic=file:table2.csv+description='Hello world'
    @marker:foo
    +table:generic=file:table3.csv+description=@row1
    # not existing
    +table:generic=file:table4.csv+description=@row1
    """)
    
    monkeypatch.chdir(workdir)

    rdf = ReportDataFile(str(base), _root=[])

    assert rdf.errors == []

    for task in rdf.tasks:
        if task.serial == 4: 
            task.value.load()
            csv = task.value.content
            assert csv.caption == 'Speed records of cars'
            assert csv.rows == 4
            assert csv.cols == 5
            assert csv.data[1][1] == 'Thrust SSC'

