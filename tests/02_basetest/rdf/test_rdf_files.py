import os
from datetime import datetime


from _setup_rdf import *

def test_marker_behavior(tmp_path):
    src = Path(__file__).parent / "rdf_testMarker.rdf"
    content = [line for line in src.read_text().splitlines() if not line.startswith("*datadir=data")]
    file_path = tmp_path / "rdf_testMarker.rdf"
    file_path.write_text("\n".join(content))
    (tmp_path / "foo").mkdir()
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        rdf = ReportDataFile(str(file_path))
    finally:
        os.chdir(cwd)
    images = [t for t in rdf.tasks if t.target == "image:generic"]
    assert len(images) == 3
    ReportTask._newPaths.clear()
    
def test_multi_section_paths_and_consistency():
    base = Path(__file__).parent / "rdf_multiSection.rdf"
    rdf = ReportDataFile(str(base))

    paths = [tuple(task.path) for task in rdf.tasks]
    assert paths == [
        ('global', 'setup'), 
        ('section:instruction_bc', 'subsection:instruction'), 
        ('section:instruction_bc', 'subsection:instruction', 'head'), 
        ('section:instruction_bc', 'subsection:instruction', 'subsubsection:detail'), 
        ('section:instruction_bc', 'subsection:instruction', 'subsubsection:detail', 'float'), 
        ('section:instruction_bc', 'subsection:instruction', 'subsubsection:detail', 'integer'), 
        ('section:instruction_bc', 'subsection:instruction', 'subsubsection:detail', 'text:description')
    ]
    addresses = [tuple(task.myAddress) for task in rdf.tasks]
    assert addresses == paths

    copy_operations = [
        (tuple(task.path), task.what)
        for task in rdf.tasks
        if task.target == ""
    ]
    assert copy_operations == [
        (('section:instruction_bc', 'subsection:instruction'), 'copy'), 
        (('section:instruction_bc', 'subsection:instruction', 'subsubsection:detail'), 'copy')
    ]

def test_repeat_section_generates_unique_addresses():
    base = Path(__file__).parent / "rdf_repeatSection.rdf"
    rdf = ReportDataFile(str(base))

    addresses = [".".join(task.myAddress) for task in rdf.tasks]
    assert addresses == [
        'section:a.subsection:instruction', 
        'section:a.subsection:instruction.subsubsection:test', 
        'section:a.subsection:instruction.subsubsection:test.head', 
        'section:a.subsection:instruction_c002', 
        'section:a.subsection:instruction_c002.head', 
        'section:a.subsection:instruction_c003', 
        'section:a.subsection:instruction_c003.head', 
        'section:b.head', 
        'section:b.subsection:instruction', 
        'section:b.subsection:instruction.subsubsection:test',         
        'section:b.subsection:instruction.subsubsection:test.head', 
        'section:a.subsection:instruction_c003.subsubsection:test', 
        'section:a.subsection:instruction_c003.subsubsection:test.head', 
        'section:a.subsection:instruction_c003.subsubsection:test_c002', 
        'section:a.subsection:instruction_c003.subsubsection:test_c002.head'
    ]
    operations = [
        (".".join(task.myAddress), task.what)
        for task in rdf.tasks
        if task.target == ""
    ]
    assert operations == [
        ('section:a.subsection:instruction', 'copy'), 
        ('section:a.subsection:instruction.subsubsection:test', 'copy'), 
        ('section:a.subsection:instruction_c002', 'copy'), 
        ('section:a.subsection:instruction_c003', 'copy'), 
        ('section:b.subsection:instruction', 'copy'), 
        ('section:b.subsection:instruction.subsubsection:test', 'copy'), 
        ('section:a.subsection:instruction_c003.subsubsection:test', 'apply'), 
        ('section:a.subsection:instruction_c003.subsubsection:test_c002', 'copy')
        ]

    assert ReportTask._newPaths == {
        'section:a.subsection:instruction': ['section:a.subsection:instruction_c002', 'section:a.subsection:instruction_c003'], 
        'section:a.subsection:instruction.head': ['section:a.subsection:instruction_c003.head'], 
        'section:a.subsection:instruction.subsubsection:test': ['section:a.subsection:instruction_c003.subsubsection:test', 
                                                                'section:a.subsection:instruction_c003.subsubsection:test_c002'], 
        'section:a.subsection:instruction.subsubsection:test.head': ['section:a.subsection:instruction_c003.subsubsection:test.head', 
                                                                     'section:a.subsection:instruction_c003.subsubsection:test_c002.head']
        }

    ReportTask._newPaths.clear()
    
    