"""Every case keeps what its document must say, and compares against it itself.

Where this comes from
---------------------
This is what is left of the differential harness that carried the YAML
migration. It began by generating a fixture's ``.rdf`` and its ``.yaml`` in
one run and comparing the two documents; when ``StructuredElement.path``
became canonical the text parser's side degraded, so what each ``.rdf``
generated at `44267a8` -- the last commit before the tree changed -- was
captured instead, one ``<case>/expected/<stem>.json`` beside each fixture,
and the ``.rdf`` files and their parser could go (`a57cf68`). Those
references are the record of what the text format produced, and a case whose
``.yaml`` stops saying what its reference says has changed meaning, whatever
the reason.

For a while this module compared every case against its reference, because
every case test asserted only that a file was written -- which is how the
clone-ordering defect fixed in `b1a4afd` lived in shipped code for years
with a green suite. Then the cases graduated, one by one (`958d474` first):
each case test now builds its document the way the case runner does, compares
what it says with the reference, and reads back what a text comparison cannot
see -- pictures with their sizes, tables, movies, the outline. The reading,
normalising and comparing are shared in ``common_case`` (:func:`said`,
:func:`normalise`, :func:`reference`, :func:`difference`, :func:`portable`,
:func:`comparable`), so no two tests can disagree about what "the same
document" means.

What stays here
---------------
The registry of the cases and the checks that only make sense across them:

* every case directory that keeps a reference is listed here with the test
  file that reads it, every listed test file exists and names that reference,
  and no reference on disk is unlisted -- a reference nobody compares against
  is worse than none: it looks like coverage and is not;
* the shared pieces keep their meaning: a document generated twice says the
  same thing through them; ``normalise`` hides dates and only dates;
  ``portable`` takes exactly the workspace out of a quoted path;
  ``comparable`` drops exactly the field results only Word refreshes, and
  keeps every caption.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip('docx')    # every registered case builds a Word document

TESTS_ROOT = Path(__file__).resolve().parents[2]
if str(TESTS_ROOT / '02_basetest') not in sys.path:
    sys.path.append(str(TESTS_ROOT / '02_basetest'))

from common_case import CaseConfig, run_docx_case, DATA_SOURCE  # noqa: E402
from common_case import said, normalise, reference, difference  # noqa: E402
from common_case import portable, comparable, FIELD_ENTRY  # noqa: E402

#: (case directory relative to tests/, fixture stem, the test file that
#: builds the document and compares it with ``<case>/expected/<stem>.json``)
CASES = [
    ('02_basetest/docx_basic/simple', 'word_simple', 'test_docx_simple.py'),
    ('02_basetest/docx_basic/images', 'word_images', 'test_docx_images.py'),
    ('02_basetest/docx_basic/tables', 'word_tables', 'test_docx_tables.py'),
    ('02_basetest/docx_basic/text', 'word_text', 'test_docx_text.py'),
    ('02_basetest/docx_basic/ladder', 'ladder', 'test_docx_ladder_placement.py'),
    ('04_examples/wordreport', 'word_input', 'test_docx_generation.py'),
    ('04_examples/essay', 'essay', 'test_essay_docx_generation.py'),
    ('02_basetest/pptx-basic/simple', 'powerpoint_simple', 'test_pptx_simple.py'),
    ('04_examples/pptreport', 'powerpoint_input', 'test_pptx_generation.py'),
]


def reference_path(case, stem):
    """Where a case keeps what it is supposed to say."""
    return TESTS_ROOT / case / 'expected' / f'{stem}.json'


# ------------------------------------------------------------- the registry

def test_every_case_has_a_reference():
    """A missing reference would make a comparison vacuous."""
    for case, stem, _ in CASES:
        assert reference_path(case, stem).is_file(), \
            f'{stem}: no reference at {reference_path(case, stem)}'
        assert len(reference(reference_path(case, stem))) > 3, stem


def test_no_reference_is_left_behind():
    """Every ``expected/`` in the tree belongs to a case listed here."""
    on_disk = {path.resolve() for path in TESTS_ROOT.rglob('expected/*.json')}
    claimed = {reference_path(case, stem).resolve() for case, stem, _ in CASES}

    assert on_disk == claimed, f'orphaned: {sorted(on_disk - claimed)}'


def test_every_case_compares_in_its_own_test_file():
    """The test file a case names exists beside it and reads its reference --
    otherwise the reference is an orphan with an alibi."""
    for case, stem, test_file in CASES:
        test = TESTS_ROOT / case / test_file
        assert test.is_file(), f'{case}: {test_file} is not there'
        source = test.read_text(encoding='utf-8')
        assert f'{stem}.json' in source, f'{case}/{test_file} does not name expected/{stem}.json'
        assert 'reference(' in source and 'said(' in source, \
            f'{case}/{test_file} does not read the document back against it'


# ------------------------------------------------------- the shared pieces

def test_generating_the_same_document_twice_says_the_same_thing(tmp_path):
    """Self-test of the comparison, including the normalising and the path
    folding: the simple case built twice, in two workspaces, with ``date:
    now`` evaluated twice. If this fails the tests are measuring their own
    noise rather than the documents."""
    case = TESTS_ROOT / '02_basetest' / 'docx_basic' / 'simple'
    documents = []
    for run in ('once', 'twice'):
        config = CaseConfig(name=run, case_dir=case, document_name='word_simple.yaml',
                            template_doc_name='template.docx', output_name=f'{run}.docx',
                            include_patterns=['*.yaml', 'template.docx'],
                            data_source_dir=DATA_SOURCE)
        (tmp_path / run).mkdir()
        built = run_docx_case(config, tmp_path / run)
        documents.append(normalise(portable(said(built), built.parent)))

    assert documents[0] == documents[1], difference(*documents)
    assert len(documents[0]) > 20


def test_normalise_hides_dates_and_only_dates():
    assert normalise(['Fri 12. Aug 2026 14:24:59', 'Table 1: Tools used', 'Monday']) == [
        '# #. Aug # #:#:#', 'Table #: Tools used', 'Monday']


def test_portable_takes_the_workspace_out_of_a_quoted_path(tmp_path):
    """The back ends quote a missing file's path with ``repr``; the runner
    makes that path absolute. What is left reads like the reference: the
    data directory and the file, with ``/`` whatever the platform."""
    quoted = f"no file with image: {str(tmp_path / 'data' / 'gone.png')!r}"

    assert portable([quoted, 'untouched'], tmp_path) == [
        "no file with image: 'data/gone.png'", 'untouched']


def test_field_results_are_dropped_from_both_sides_and_captions_are_not():
    """The wordreport reference was captured with ``finish=True`` and holds
    Word's refreshed lists; a plain run holds the template's stale ones. The
    filter removes exactly the entries (caption, tab, page) and keeps the
    caption paragraphs, so the two still compare -- and a caption that went
    missing would still be noticed."""
    stored = reference(reference_path('04_examples/wordreport', 'word_input'))
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
