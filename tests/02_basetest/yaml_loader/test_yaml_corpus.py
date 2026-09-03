"""Every fixture in the corpus, translated to YAML, loads cleanly.

The conversion could not be mechanical, and this file is where that is pinned
rather than asserted in prose. Three kinds of change were needed:

* **Re-opened roots collapse.** ``rdf_repeatSection.rdf`` opens ``section:a``
  three times to add children in three passes, which is how the text format
  *returned* to a section it had left. Under nesting you never leave it, so a
  line-by-line translation would have produced three sections.
* **Dotted fill lines become real nesting**, and are then ladder-checked --
  which the text format never did for them, because only a structural line
  validated its namespace.
* **Dead markers were decided, not reproduced.** Several ``@marker:...`` lines
  set a marker that the very next include immediately cleared, by opening an
  absolute root on its first line. Position now places content, so there is
  nothing to reproduce.

Each is recorded against the fixture it applies to below.

Every document is loaded in a prepared directory rather than in place, the way
``setupTestEnvironment`` prepares one for the docx cases: ``datadir`` has to
exist, and the corpus points at a ``data`` beside the document.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from Scriptum.rdf.loader import load

TESTS_ROOT = Path(__file__).resolve().parents[2]
DATA_SOURCE = TESTS_ROOT / 'data_source'


def tracked(pattern):
    """Every **tracked** file under ``tests/`` matching *pattern*, as posix
    paths relative to ``tests/``.

    ``git ls-files`` rather than ``rglob``, which is the same choice
    ``test_repo_hygiene`` made and for the same reason: what is not tracked is
    not this file's business. The two checks below classify the *corpus*, and
    a developer's untracked scratch directory is not part of it -- the
    ``Scriptum-Report-main`` worktree carries two gitignored folders of
    retired ``.rdf`` files, and while these walked the filesystem they failed
    there and passed everywhere else. A suite that is green in one worktree
    and red in another, over files git was never asked about, teaches nobody
    anything.

    Run from ``tests/`` so the pathspec needs no prefix and the output is
    already relative to it; git's ``*`` matches across directories, so one
    pattern reaches the whole tree.

    A failure of git itself is a **skip**, carrying git's own words. The case
    that costs an afternoon is running the suite in WSL against a *worktree*:
    its ``.git`` is a file whose ``gitdir:`` names the main checkout with a
    Windows path, which WSL's git resolves against the current directory and
    cannot follow. Both checks then quietly stop being enforced, and only the
    message says so. They run on every Windows run and on every CI leg, where
    the checkout is ordinary.
    """
    listed = subprocess.run(['git', 'ls-files', pattern], cwd=TESTS_ROOT,
                            capture_output=True, text=True)
    if listed.returncode != 0:
        said = ' '.join(listed.stderr.split())
        pytest.skip(f'git ls-files failed, nothing to classify here: '
                    f'{said or f"exit {listed.returncode}, nothing on stderr"}')
    return {line.replace('\\', '/') for line in listed.stdout.splitlines() if line}

#: Root documents: a ``_scriptum_`` mapping, loadable on their own.
ROOT_DOCUMENTS = [
    '02_basetest/docx_basic/images/word_images.yaml',
    '02_basetest/docx_basic/ladder/ladder.yaml',
    '02_basetest/docx_basic/simple/word_simple.yaml',
    '02_basetest/docx_basic/tables/word_tables.yaml',
    '02_basetest/docx_basic/text/word_text.yaml',
    '02_basetest/pptx-basic/simple/powerpoint_simple.yaml',
    '02_basetest/rdf/rdf_big_docx.yaml',
    '02_basetest/rdf/rdf_big_pptx.yaml',
    '02_basetest/rdf/rdf_multiSection.yaml',
    '02_basetest/rdf/rdf_repeatSection.yaml',
    '02_basetest/rdf/rdf_report_simple.yaml',
    '02_basetest/rdf/rdf_resource.yaml',
    '02_basetest/rdf/rdf_testMarker.yaml',
    '04_examples/essay/essay.yaml',
    '04_examples/pptreport/powerpoint_input.yaml',
    '04_examples/wordreport/word_input.yaml',
]

#: Fragments: bare sequences, reached through an include. Loading one as a root
#: document is an error, and the shape is what says so.
FRAGMENTS = [
    '02_basetest/docx_basic/text/textinclude1.yaml',
    '02_basetest/rdf/rdf_big_instructions01.yaml',
    '02_basetest/rdf/rdf_big_instructions02.yaml',
    '02_basetest/rdf/rdf_big_preparation01.yaml',
    '02_basetest/rdf/rdf_big_preparation01sub.yaml',
    '02_basetest/rdf/rdf_big_preparation02.yaml',
    '02_basetest/rdf/rdf_big_tool01.yaml',
    '04_examples/wordreport/instruction01.yaml',
    '04_examples/wordreport/instruction02.yaml',
    '04_examples/wordreport/preparation01.yaml',
    '04_examples/wordreport/testplan01.yaml',
    '04_examples/wordreport/tool01.yaml',
]


def prepare(relative, tmp_path):
    """Copy a document's whole directory somewhere it can resolve its data.

    Its includes come with it, because an include resolves against the file
    doing the including -- so the fragments have to travel as a unit.
    """
    document = TESTS_ROOT / relative
    for sibling in document.parent.glob('*.yaml'):
        shutil.copy(sibling, tmp_path / sibling.name)

    own_data = document.parent / 'data'
    source = own_data if own_data.is_dir() else DATA_SOURCE
    shutil.copytree(source, tmp_path / 'data', dirs_exist_ok=True)

    return tmp_path / document.name


@pytest.mark.parametrize('relative', ROOT_DOCUMENTS)
def test_a_root_document_loads_without_diagnostics(relative, tmp_path):
    document = load(prepare(relative, tmp_path))

    assert document.tasks, 'a document with no tasks is not a translation'
    assert document.settings.documenttype in ('docx', 'pptx')


@pytest.mark.parametrize('relative', FRAGMENTS)
def test_a_fragment_is_not_a_root_document(relative, tmp_path):
    """The shape carries the rule: a fragment has nowhere to put settings."""
    from Scriptum.rdf.loader import DocumentError

    with pytest.raises(DocumentError) as caught:
        load(prepare(relative, tmp_path))

    report = str(caught.value)
    assert 'root document is a mapping' in report
    assert 'included fragment' in report


def test_every_yaml_fixture_is_accounted_for():
    """The counterpart of test_all_rdf_files_are_accounted_for: a fixture
    added without a classification is a fixture nothing loads.

    Tracked files only -- see :func:`tracked` for why.
    """
    found = tracked('*.yaml')
    classified = set(ROOT_DOCUMENTS) | set(FRAGMENTS)

    assert not found - classified, 'unclassified YAML fixtures'
    assert not classified - found, 'stale YAML classifications'


def test_no_rdf_fixture_is_left():
    """The text format is gone, reader and all.

    This began as "every ``.rdf`` still has a ``.yaml`` beside it", the check
    that nothing was left untranslated while the two corpora sat side by side.
    The last ``.rdf`` went with the parser, so what has to hold now is the
    other thing: a ``.rdf`` **committed** under ``tests/`` is a file nothing
    reads, and it should be noticed rather than carried.

    Committed is the operative word. A retired ``.rdf`` kept locally and
    gitignored is a private note, not a corpus fixture, and it is not this
    test's business -- see :func:`tracked`.
    """
    assert not tracked('*.rdf'), 'no reader exists for these'


# --------------------------------------------------- the interesting ones

def test_repeated_sections_collapse_into_one_entry(tmp_path):
    """rdf_repeatSection.rdf opens section:a three times. Under nesting that
    is one section with three subsections, not three sections."""
    document = load(prepare('02_basetest/rdf/rdf_repeatSection.yaml', tmp_path))

    sections = [t.myAddress[0] for t in document.tasks]
    assert sorted(set(sections)) == ['section:a::1', 'section:b::1']


def test_a_repeated_subsection_is_numbered_not_renamed(tmp_path):
    document = load(prepare('02_basetest/rdf/rdf_repeatSection.yaml', tmp_path))

    instructions = [t.myAddress[-1] for t in document.tasks
                    if not t.target and t.myAddress[-1].startswith('subsection:')]
    assert instructions == ['subsection:instruction::1',
                            'subsection:instruction::2',
                            'subsection:instruction::3',
                            'subsection:instruction::1']
    assert not any('_c0' in a for t in document.tasks for a in t.myAddress)


def test_the_big_docx_document_splices_all_four_include_groups(tmp_path):
    document = load(prepare('02_basetest/rdf/rdf_big_docx.yaml', tmp_path))

    addresses = ['.'.join(t.myAddress) for t in document.tasks]
    assert any('subsection:tool::1' in a for a in addresses)
    assert any('subsection:preparation::1' in a for a in addresses)
    assert any('subsubsection:ingredients::2' in a for a in addresses)


def test_the_multi_section_document_reads_as_the_text_parser_read_it(tmp_path):
    """The shape the text parser's own suite pinned for this fixture, carried
    over: the same containers in the same order, every fill under the right
    one, and the global fill last -- in the canonical addresses now."""
    document = load(prepare('02_basetest/rdf/rdf_multiSection.yaml', tmp_path))

    shape = [('.'.join(t.myAddress), t.target, t.what) for t in document.tasks]
    assert shape == [
        ('section:instruction_bc::1', '', 'apply'),
        ('section:instruction_bc::1.subsection:instruction::1', '', 'apply'),
        ('section:instruction_bc::1.subsection:instruction::1.:head::1',
         'head', ''),
        ('section:instruction_bc::1.subsection:instruction::1'
         '.subsubsection:detail::1', '', 'apply'),
        ('section:instruction_bc::1.subsection:instruction::1'
         '.subsubsection:detail::1.:float::1', 'float', ''),
        ('section:instruction_bc::1.subsection:instruction::1'
         '.subsubsection:detail::1.:integer::1', 'integer', ''),
        ('section:instruction_bc::1.subsection:instruction::1'
         '.subsubsection:detail::1.text:description::1', 'text:description', ''),
        ('_global_.setup', 'setup', ''),
    ]
    assert [t.path for t in document.tasks][:2] == [
        ['section:instruction_bc'],
        ['section:instruction_bc', 'subsection:instruction'],
    ], 'path is the template address, without instance numbers'


def test_the_big_docx_document_knows_which_files_are_missing(tmp_path):
    """Existence is decided when the document is read (see *Content is lazy,
    existence is eager* on the values board), so the missing inputs are known
    before any document work begins. The text parser's suite pinned this list
    for the same fixture, in document order; it lost pudding.jpg when that
    file joined data_source (5bf0c37)."""
    document = load(prepare('02_basetest/rdf/rdf_big_docx.yaml', tmp_path))

    missing = []
    for task in document.tasks:
        value = task.value
        if value.type in ('file', 'parfile') and not value.object.exists:
            name = Path(value.object.filename).name
            if name not in missing:
                missing.append(name)

    assert missing == [
        'instruction2.png', 'instructiongeneral.csv',
        'instruction1.png', 'instruction1b.png', 'instruction2.csv',
        'plate1.png', 'plate1.txt', 'bc1.png', 'some.png', 'some.txt',
        'tools.csv', 'tool.par', 'todo.txt', 'ingredients1.csv',
        'ingredients2.csv', 'foo.txt', 'bar.csv',
    ]


def test_the_word_report_reaches_its_testplans_section(tmp_path):
    """In the .rdf that section is never opened by the master -- it is reached
    only because testplan01.rdf restates an absolute path and jumps there, past
    a phantom section:results and a marker that exists in no template."""
    document = load(prepare('04_examples/wordreport/word_input.yaml', tmp_path))

    addresses = ['.'.join(t.myAddress) for t in document.tasks]
    assert any(a.startswith('section:testplans::1.subsection:testplan::1')
               for a in addresses)
    assert not any('section:results' in a for a in addresses)
