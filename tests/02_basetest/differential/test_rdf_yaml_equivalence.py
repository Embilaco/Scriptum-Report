"""What each fixture's ``.yaml`` generates, against what its ``.rdf`` did.

This is the safety net of the migration. Every docx case test asserts only
that a file was written and is not empty, which is how the clone-ordering
defect fixed in `b1a4afd` lived in shipped code for years with a green suite.
This reads the finished documents back instead.

Why a stored reference rather than a live comparison
----------------------------------------------------
It began by generating both sides in one run. That stopped working the moment
``StructuredElement.path`` became canonical: the text parser emitted
``section:title`` where the tree says ``section:title::1``, so the *old* side
degraded and there was nothing left to compare against.

So the reference was captured instead. Each case keeps its own beside the
fixture it belongs to -- ``<case>/expected/<stem>.json`` -- which is what each
``.rdf`` generated at `44267a8`, the last commit before the tree changed. That
is what let the text parser go: the ``.rdf`` files and the parser are gone, and
these references are the record of what they produced. A case whose
``.yaml`` stops saying this has changed meaning, whatever the reason.

Living next to the fixture rather than in one pile means a case is a directory
you can read end to end: the document, the template, the data and what it is
supposed to say.

What is compared
----------------
The sequence of non-empty paragraph texts, then every table cell, with runs of
digits **and weekday names** collapsed to ``#``. Both are for dates: a fixture
using ``date: now`` is evaluated when the document is built, and the reference
was built on another day -- which the digits hide and the leading ``Fri`` of
the default format does not. What the comparison exists for -- a paragraph
missing, an extra one, two in the wrong order -- survives it. The reading and
the normalising live in ``common_case`` (:func:`said`, :func:`normalise`,
:func:`reference`, :func:`difference`), shared with the case tests, so a case
and this harness cannot disagree about what "the same document" means.

Cases graduate
--------------
A case whose own test file reads its document back and compares it with the
reference leaves :data:`CASES` for :data:`GRADUATED`: the comparison is then
made where the case lives, next to the checks only that case can make (the
pictures, videos and tables a text comparison cannot see), and is not made
twice. ``04_examples/pptreport`` was the first. The reference stays in the
case's ``expected/`` and :func:`test_no_reference_is_left_behind` still
accounts for it.

What is not compared: field results
-----------------------------------
A Word template carries a *list of tables* and a *list of figures* -- TOC
fields whose stored result is whatever Word last wrote into them. A plain run
(``save()`` without ``finish``) leaves that result as the template had it,
``Table 1: <description/>`` three times; a ``finish=True`` run -- Windows with
Word, the only thing that can update a field -- rewrites it with one entry per
caption actually in the document. So the same document says two different
things in those lines depending on where it was built, and a reference
captured one way can never match a run made the other way.

Those entries are the one shape ``caption<TAB>page``, and :func:`comparable`
drops them from **both** sides. Nothing is lost: every caption is also a
caption paragraph of its own, which stays compared. One reference therefore
serves both -- the wordreport reference was captured with ``finish=True``
(``e60f4e0``) and the others without, and all compare against a plain run
anywhere, and against a finished run where Word is.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

import Scriptum
from Scriptum.rdf.reportDataFile import ReportDataFile

TESTS_ROOT = Path(__file__).resolve().parents[2]
if str(TESTS_ROOT / '02_basetest') not in sys.path:
    sys.path.append(str(TESTS_ROOT / '02_basetest'))

from common_case import said, normalise, difference  # noqa: E402
from common_case import reference as stored_reference  # noqa: E402

#: A field result of a list of tables / figures: ``caption<TAB>page``, after
#: the digits have been collapsed. Only Word updates these, so a finished run
#: and a plain run disagree on them by construction; see the module docstring.
FIELD_ENTRY = re.compile(r'\t#$')

#: (case directory relative to tests/, fixture stem, template file)
CASES = [
    ('02_basetest/docx_basic/simple', 'word_simple', 'template.docx'),
    ('02_basetest/docx_basic/images', 'word_images', 'template.docx'),
    ('02_basetest/docx_basic/tables', 'word_tables', 'template_table.docx'),
    ('04_examples/wordreport', 'word_input', 'template.docx'),
    ('04_examples/essay', 'essay', 'essay.docx'),
    ('02_basetest/pptx-basic/simple', 'powerpoint_simple', 'template.pptx'),
    # The last to join: template_text.docx spelled its depth-3 block
    # <subsubsubsection:secondsubsubi>, a name not on the docx ladder, while the
    # .yaml uses the ladder's sub3section. The tag was renamed in the template
    # and the reference re-captured -- it predated blueprint pruning and still
    # held the nested blueprint text a seconda clone used to leak.
    ('02_basetest/docx_basic/text', 'word_text', 'template_text.docx'),
]

#: (case directory relative to tests/, fixture stem, the test file that now
#: makes the comparison). See "Cases graduate" in the module docstring.
GRADUATED = [
    ('04_examples/pptreport', 'powerpoint_input', 'test_pptx_generation.py'),
]


def prepare(case):
    """A directory holding the fixtures, the template and a ``data``."""
    work = Path(tempfile.mkdtemp())
    source = TESTS_ROOT / case

    # Files only, so `expected/` stays where it is: the reference is what the
    # run is checked against, not an input to it.
    for pattern in ('*.yaml', '*.docx', '*.pptx'):
        for path in source.glob(pattern):
            shutil.copy(path, work)

    own_data = source / 'data'
    shutil.copytree(own_data if own_data.is_dir() else TESTS_ROOT / 'data_source',
                    work / 'data', dirs_exist_ok=True)
    return work


def generate(work, document_name, template, output=None):
    """Build one document. Returns what the run printed, for diagnosis.

    The two back ends are driven differently and always have been: Word
    typesets a document that already exists, PowerPoint *assembles* one from
    layouts and then drops the placeholder slide it started from. The steps
    here mirror ``common_case.run_docx_case`` and ``run_pptx_case``.
    """
    powerpoint = template.endswith('.pptx')
    output = output or ('out.pptx' if powerpoint else 'out.docx')

    os.chdir(work)
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        rdf = ReportDataFile(document_name)
        if powerpoint:
            managed = Scriptum.ManagedPptx(template)
            managed.artist(rdf, directfill=True, globalfill=True,
                           cleardust=True, setproperties=True)
            managed.remove_slide(0)
        else:
            managed = Scriptum.ManagedDocx(template, rdf)
            managed.typesetting(rdf)
        managed.save(output)
    return printed.getvalue()


def spoken(path):
    """What the finished document says, in order, dates neutralised."""
    return normalise(said(path))


def comparable(lines):
    """*lines* without the field results only Word updates -- the entries of
    a list of tables or figures -- so a reference captured with ``finish=True``
    and a run made without it (or the other way round) compare on what the
    document itself says."""
    return [line for line in lines if not FIELD_ENTRY.search(line)]


def reference_path(case, stem):
    """Where a case keeps what it is supposed to say."""
    return TESTS_ROOT / case / 'expected' / f'{stem}.json'


def reference(case, stem):
    """The stored reference, through the same normaliser as a fresh run."""
    return stored_reference(reference_path(case, stem))


def compare(case, stem, template):
    work = prepare(case)
    printed = generate(work, f'{stem}.yaml', template)
    got = comparable(spoken(work / ('out.pptx' if template.endswith('.pptx') else 'out.docx')))
    expected = comparable(reference(case, stem))
    complaints = [line for line in printed.splitlines()
                  if 'ERROR' in line or 'WARNING' in line]
    return expected, got, complaints


# ------------------------------------------------------- the harness works

def test_every_case_has_a_reference():
    """A missing reference would make a comparison vacuous."""
    for case, stem, template in CASES:
        assert reference_path(case, stem).is_file(), \
            f'{stem}: no reference at {reference_path(case, stem)}'
        assert len(reference(case, stem)) > 3, stem


def test_no_reference_is_left_behind():
    """Every ``expected/`` in the tree belongs to a case listed here, or to
    one that graduated to its own test file.

    A reference nobody compares against is worse than none: it looks like
    coverage and is not.
    """
    on_disk = {path.resolve() for path in TESTS_ROOT.rglob('expected/*.json')}
    claimed = {reference_path(case, stem).resolve()
               for case, stem, _ in CASES + GRADUATED}

    assert on_disk == claimed, f'orphaned: {sorted(on_disk - claimed)}'


def test_a_graduated_case_compares_in_its_own_test_file():
    """The test file a graduated case names exists beside it and reads its
    reference -- otherwise the reference is an orphan with an alibi."""
    for case, stem, test_file in GRADUATED:
        test = TESTS_ROOT / case / test_file
        assert test.is_file(), f'{case}: {test_file} is not there'
        assert f'{stem}.json' in test.read_text(encoding='utf-8'), \
            f'{case}/{test_file} does not read expected/{stem}.json'
        assert (case, stem) not in {(c, s) for c, s, _ in CASES}, \
            f'{case} is listed twice: compare it here or there, not both'


def test_generating_the_same_document_twice_says_the_same_thing():
    """Self-test of the comparison, including the digit collapsing: if this
    fails the harness is measuring its own noise rather than the translation."""
    case, stem, template = CASES[0]
    work = prepare(case)

    generate(work, f'{stem}.yaml', template, 'once.docx')
    generate(work, f'{stem}.yaml', template, 'twice.docx')

    assert spoken(work / 'once.docx') == spoken(work / 'twice.docx')


def test_field_results_are_dropped_from_both_sides_and_captions_are_not():
    """The wordreport reference was captured with ``finish=True`` and holds
    Word's refreshed lists; a plain run holds the template's stale ones. The
    filter removes exactly the entries (caption, tab, page) and keeps the
    caption paragraphs, so the two still compare -- and a caption that went
    missing would still be noticed."""
    stored = reference('04_examples/wordreport', 'word_input')
    entries = [line for line in stored if FIELD_ENTRY.search(line)]
    kept = comparable(stored)

    assert entries, 'the reference holds no list entry any more -- recaptured without finish?'
    assert all('\t' in line for line in entries)
    assert not any(FIELD_ENTRY.search(line) for line in kept)
    captions = [line for line in kept if line.startswith(('Table #: ', 'Figure #: '))]
    assert captions, 'the caption paragraphs must survive the filter'
    assert len(kept) == len(stored) - len(entries)


def test_the_difference_report_notices_what_it_should():
    assert 'first difference at line 1' in difference(['a', 'b'], ['a', 'c'])
    assert 'more line(s)' in difference(['a', 'b'], ['a'])
    assert difference(['a'], ['a']) == 'no difference'


# ---------------------------------------------------------- the comparison

@pytest.mark.parametrize('case, stem, template', CASES)
def test_the_yaml_document_says_what_the_rdf_document_said(case, stem, template):
    """The document a .yaml produces says what its .rdf produced.

    This is what the whole migration was for, checked the only way that could
    have caught the clone-ordering defect: by reading the finished document.
    """
    expected, got, complaints = compare(case, stem, template)

    assert got == expected, (
        difference(expected, got)
        + chr(10) + 'the run said: ' + repr(complaints[:3]))

