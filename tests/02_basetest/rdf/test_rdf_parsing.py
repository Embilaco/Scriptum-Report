import sys
import types
from pathlib import Path

from pytest import MonkeyPatch

from _setup_rdf import *

def test_include_combines_tasks(tmp_path: Path):
    child = tmp_path / "child.rdf"
    child.write_text(".value=2\n")

    parent = tmp_path / "parent.rdf"
    parent.write_text("\n".join([
        "*version=100",
        "*documenttype=pptx",
        "section:parent",
        ".value=1",
        f"&include=file:{child}",
        ""
    ]))

    rdf = ReportDataFile(str(parent))
    value_tasks = [t for t in rdf.tasks if t.target == "value"]
    assert {str(t.value) for t in value_tasks} == {"1", "2"}


def test_recursion_depth_limit(tmp_path: Path):
    child = tmp_path / "child.rdf"
    child.write_text("\n")

    parent = tmp_path / "parent.rdf"
    parent.write_text("\n".join([
        "*version=100",
        "*documenttype=pptx",
        "section:root",
        f"&include=file:{child}",
        ""
    ]))

    ReportDataFile._rlimit = 1
    with pytest.raises(Exception) as excinfo:
        ReportDataFile(str(parent))
    assert "Too many recursions" in str(excinfo.value)
    ReportDataFile._depth = 0


def test_malformed_lines_populate_errors(tmp_path: Path):
    bad = tmp_path / "bad.rdf"
    bad.write_text("+value=1\n@marker+value=2\n")

    settings = SETTINGS()
    settings.version = 3
    settings.documenttype = "pptx"

    rdf = ReportDataFile(str(bad), _root=["section"], _settings=settings)

    assert any("Adding content (+)" in e for e in rdf.errors)
    assert any("(@) and (+)" in e for e in rdf.errors)

# bigger test with 'basetest_docx.rdf'
def test_details_on_huge_rdf(monkeypatch: MonkeyPatch, tmp_path: Path):
    report_path = Path(__file__).parent / "rdf_big_docx.rdf"
    report_dir = report_path.parent

    workdir = tmp_path / "workspace"
    workdir.mkdir()

    include_patterns = [
        "rdf_big*.rdf",
    ]
    include_files = set()
    for pattern in include_patterns:
        include_files.update(report_dir.glob(pattern))
    for src in include_files:
        ensure_link(src, workdir / src.name)

    ensure_link(DATA_SOURCE, workdir / "data")

    monkeypatch.chdir(workdir)

    rdf = ReportDataFile(str(report_path))

    # no errors
    assert rdf.errors == []

    addresses = []
    for task in rdf.tasks:
        if task.path != task.myAddress and task.myAddress not in addresses:
            addresses.append(task.myAddress)

    missing = []
    for task in rdf.tasks:
        if (task.value.type in ['file', 'parfile'] 
            and 
            not task.value.object.exists 
            and 
            task.myAddress not in missing):
            missing.append(task.value.object.filename.replace('\\','/'))

    assert missing == [
        'data/pudding.jpg',
        'data/instruction2.png', 
        'data/instructiongeneral.csv', 
        'data/instruction1.png', 
        'data/instruction1b.png', 
        'data/instruction2.png', 
        'data/instruction2.csv', 
        'data/plate1.png', 
        'data/plate1.txt', 
        'data/bc1.png',
        'data/some.png', 
        'data/some.txt', 
        'data/tools.csv', 
        'data/tool.par', 
        'data/todo.txt', 
        'data/ingredients1.csv', 
        'data/ingredients2.csv', 
        'data/foo.txt', 
        'data/bar.csv'], f'Assertion failed, found {missing}'

    assert addresses == [
        ['section:instruction_bc', 'subsection:instruction', 'image:generic_c002'], 
        ['section:instruction_bc', 'subsection:instruction_c002'], 
        ['section:instruction_bc', 'subsection:instruction_c002', 'head'], 
        ['section:instruction_bc', 'subsection:instruction_c002', 'text:description'], 
        ['section:instruction_bc', 'subsection:instruction_c002', 'image:generic'], 
        ['section:instruction_bc', 'subsection:instruction_c002', 'table:generic'], 
        ['section:instruction_bc', 'subsection:bc', 'image:generic_c002'], 
        ['section:instruction_bc', 'subsection:bc', 'text:generic_c002'], 
        ['section:instruction_bc', 'subsection:bc', 'image:generic_c003'], 
        ['section:instruction_bc', 'subsection:bc', 'text:generic_c003'], 
        ['section:preparations', 'subsection:preparation', 'subsubsection:ingredients_c002'], 
        ['section:preparations', 'subsection:preparation', 'subsubsection:ingredients_c002', 'text:description'], 
        ['section:preparations', 'subsection:preparation', 'subsubsection:ingredients_c002', 'table:generic'], 
        ['section:preparations', 'subsection:preparation_c002'], 
        ['section:preparations', 'subsection:preparation_c002', 'preparation:id'], 
        ['section:preparations', 'subsection:preparation_c002', 'text:description'], 
        ['section:preparations', 'subsection:preparation_c002', 'subsubsection:requisites'], 
        ['section:preparations', 'subsection:preparation_c002', 'subsubsection:requisites', 'text:description'], 
        ['section:preparations', 'subsection:preparation_c002', 'subsubsection:requisites', 'table:left'], 
        ['section:preparations', 'subsection:preparation_c002', 'subsubsection:todo'], 
        ['section:preparations', 'subsection:preparation_c002', 'subsubsection:todo', 'todo:id'], 
        ['section:preparations', 'subsection:preparation_c002', 'subsubsection:todo', 'text:description'], 
        ['section:preparations', 'subsection:preparation_c002', 'subsubsection:todo', 'table:generic']
        ], f'Assertion failed, found {addresses}'


