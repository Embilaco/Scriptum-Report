# tests different data formats

from pathlib import Path
import sys

from _setup_values import  *

def test_counter_formats(tmp_path: Path):
    base = tmp_path / "testCounters.rdf"
    base.write_text("\n".join([
        "*version=100",
        "*documenttype=docx",
        "section:mysection.subsection:foo",
        ".number=numbering:1:%s):2",
        ".roman=numbering:I:%s):4",
        ".freestyle=numbering:F:%s -:A;b;C;4;Jojo;K",
        ".lowroman=numbering:i:%s ):3",
        ".char=numbering:A:%s ):3",
        ".lowchar=numbering:a:%s ):6",
        ".strange=numbering:U:%s ):6",
        ]))
    
    rdf = ReportDataFile(str(base), _root=[])

    #print(next(t for t in rdf.tasks if t.target == "number").value)
    #print(next(t for t in rdf.tasks if t.target == "roman").value)
    #print(next(t for t in rdf.tasks if t.target == "lowroman").value)
    #print(next(t for t in rdf.tasks if t.target == "freestyle").value)
    #print(next(t for t in rdf.tasks if t.target == "char").value)
    #print(next(t for t in rdf.tasks if t.target == "lowchar").value)
    #print([t.value for t in rdf.tasks if t.value.type == 'numbering'])
    assert rdf.errors == [], f'Asserion failed: {rdf.errors}'
    assert not any(["failed to" in t.value.object.str for t in rdf.tasks if t.value.type == 'numbering'])
    assert any(["unknown number format" in t.value.object.str for t in rdf.tasks if t.value.type == 'numbering'])


def test_number_formats(monkeypatch: MonkeyPatch, tmp_path: Path):

    workdir = tmp_path / "workspace"
    workdir.mkdir()

    ensure_link(DATA_SOURCE, workdir / "data")

    base = workdir / "testCounters.rdf"
    base.write_text("""
    # test report input
    *version=100
    *documenttype=docx
    *datadir=./data

    # test floats and ints
    section:intro
    .value:count=42
    .mypi:pi=3.141
    """)
    
    monkeypatch.chdir(workdir)

    rdf = ReportDataFile(str(base), _root=[])

    assert rdf.errors == [], f'Asserion failed: {rdf.errors}'

    for task in rdf.tasks:
        task.value.load()
        #print(task.serial, task.value.content)
        if task.serial == 1: assert task.value.content == '42'
        if task.serial == 2: assert task.value.content == ' 3.1410' # 7.4
