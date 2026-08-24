# tests numbering counters, integers and floats, read from a report document

from pathlib import Path

from _setup_values import *


def test_counter_formats(tmp_path: Path):
    """Every counter kind NumberValue knows, and one it does not.

    ``numbering`` takes the kind, ``format`` the pattern and ``start`` the
    first value -- three keys, where the text format packed them into one
    colon-separated value. The kind is quoted because ``numbering:`` takes
    text and ``1`` alone would be an integer.
    """
    base = tmp_path / "testCounters.yaml"
    base.write_text("\n".join([
        "_scriptum_:",
        "  version: 4",
        "  documenttype: docx",
        "_content_:",
        "  - section:mysection:",
        "      - subsection:foo:",
        "          - number: {numbering: '1', format: '%s)', start: 2}",
        "          - roman: {numbering: I, format: '%s)', start: 4}",
        "          - freestyle: {numbering: F, format: '%s -', start: 'A;b;C;4;Jojo;K'}",
        "          - lowroman: {numbering: i, format: '%s )', start: 3}",
        "          - char: {numbering: A, format: '%s )', start: 3}",
        "          - lowchar: {numbering: a, format: '%s )', start: 6}",
        "          - strange: {numbering: U, format: '%s )', start: 6}",
        ]), encoding='utf-8')

    rdf = ReportDataFile(str(base))

    #print(next(t for t in rdf.tasks if t.target == "number").value)
    #print([t.value for t in rdf.tasks if t.value.type == 'numbering'])
    assert rdf.errors == [], f'Asserion failed: {rdf.errors}'
    numberings = [t.value for t in rdf.tasks if t.value.type == 'numbering']
    assert len(numberings) == 7
    assert not any("failed to" in v.object.str for v in numberings)
    assert any("unknown number format" in v.object.str for v in numberings)

    number = next(t for t in rdf.tasks if t.target == "number").value
    assert next(number.object) == '2)'
    assert next(number.object) == '3)'
    roman = next(t for t in rdf.tasks if t.target == "roman").value
    assert next(roman.object) == 'IV)'
    freestyle = next(t for t in rdf.tasks if t.target == "freestyle").value
    assert next(freestyle.object) == 'A -'
    assert next(freestyle.object) == 'b -'


def test_number_formats(monkeypatch: MonkeyPatch, tmp_path: Path):
    """A YAML integer is an int, a YAML float a float rendered with the
    configured ``floatformat``."""

    workdir = tmp_path / "workspace"
    workdir.mkdir()

    ensure_link(DATA_SOURCE, workdir / "data")

    base = workdir / "testCounters.yaml"
    base.write_text("\n".join([
        "# test report input",
        "_scriptum_:",
        "  version: 4",
        "  documenttype: docx",
        "  datadir: ./data",
        "# test floats and ints",
        "_content_:",
        "  - section:intro:",
        "      - value:count: 42",
        "      - mypi:pi: 3.141",
        ]), encoding='utf-8')

    monkeypatch.chdir(workdir)

    rdf = ReportDataFile(str(base))

    assert rdf.errors == [], f'Asserion failed: {rdf.errors}'

    contents = {}
    for task in rdf.tasks:
        task.value.load()
        #print(task.serial, task.value.content)
        if task.target:
            contents[task.target] = (task.value.type, task.value.content)

    assert contents == {
        'value:count': ('int', '42'),
        'mypi:pi': ('float', ' 3.1410'),   # 7.4f
    }
