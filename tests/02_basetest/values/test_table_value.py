# tests table values, read from a report document

from pathlib import Path

from _setup_values import *


def test_tables(monkeypatch: MonkeyPatch, tmp_path: Path):
    """A table's caption comes from a modifier -- a string, or ``{from: row1}``
    to read it out of the CSV itself -- and the modifiers are applied before
    the content is first read (see *Tables: applyActions before content*).
    Inside a marker the same fill is an ``add``.
    """

    workdir = tmp_path / "workspace"
    workdir.mkdir()

    ensure_link(DATA_SOURCE, workdir / "data")

    base = workdir / "testTable.yaml"
    base.write_text("\n".join([
        "_scriptum_:",
        "  version: 4",
        "  documenttype: docx",
        "  datadir: ./data",
        "_content_:",
        "  - section:new:",
        "      - table:generic: {file: table1.csv}",
        "      - table:generic: {file: table1.csv, description: {from: row1}}",
        "      - table:generic: {file: table2.csv, description: 'Hello world'}",
        "      - marker:foo:",
        "          - table:generic: {file: table3.csv, description: {from: row1}}",
        "          # not existing",
        "          - table:generic: {file: table4.csv, description: {from: row1}}",
    ]), encoding='utf-8')

    monkeypatch.chdir(workdir)

    rdf = ReportDataFile(str(base))

    assert rdf.errors == []

    tables = [t for t in rdf.tasks if t.target == 'table:generic']
    assert len(tables) == 5
    assert [t.what for t in tables] == ['', '', '', 'add', 'add']
    assert all(t.value.type == 'file' and t.value.subtype == 'table' for t in tables)

    third = next(t for t in tables if t.value.object.filename.endswith('table3.csv'))
    assert third.where == 'marker:foo::1'
    third.value.load()
    csv = third.value.content
    assert csv.caption == 'Speed records of cars'
    assert csv.rows == 4
    assert csv.cols == 5
    assert csv.data[1][1] == 'Thrust SSC'

    described = next(t for t in tables if t.value.object.filename.endswith('table2.csv'))
    described.value.load()
    assert described.value.content.caption == 'Hello world'

    missing = next(t for t in tables if t.value.object.filename.endswith('table4.csv'))
    assert not missing.value.object.exists
