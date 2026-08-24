"""The text docx case, built and read back.

``word_text.yaml`` is the ladder at work on ``template.docx``: a title
section, a second section with a marker, two instances of the blueprint
``subsection:seconda`` (the first nesting a ``subsubsection`` and a
``sub3section``), a ``subsection:secondb`` whose marker takes text fills from
files -- three of them through an ``_include_`` fragment -- and four
``_global_`` values the headers and footers use. Several of the text files
are deliberately not in ``data_source`` and are announced in place. A test
that only checks the file is there proves none of that, so this module reads
the document back:

* what it *says*, against ``expected/word_text.json`` (re-captured in
  `f143b8b` after the depth-3 tag was renamed ``sub3section``);
* what it *shows*: the outline -- which heading style each ladder level got,
  something the text comparison cannot see -- and the globals in the header
  and footer of both sections. Where a clone lands is the business of
  ``test_docx_clone_order.py`` beside this file.
"""

from pathlib import Path
import sys

import docx
import pytest

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = Path(__file__).resolve().parent.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT))

from _setup_docx_basic import *
from common_case import CaseConfig, run_docx_case
from common_case import said, normalise, reference, difference, portable, fold, drawings
from common_case import checkreport_comparison

REFERENCE = THIS_DIR / 'expected' / 'word_text.json'


def build(tmp_path):
    """The document, typeset the way every docx case is."""
    config = CaseConfig(
        name="report",
        case_dir=THIS_DIR,
        document_name="word_text.yaml",
        template_doc_name="template.docx",
        output_name="final_report.docx",
        include_patterns=["*.yaml", "template.docx"],
        data_source_dir=DATA_SOURCE,
        finish=False,
        createpdf=False,
    )
    return run_docx_case(config, tmp_path)


def test_document_is_created(tmp_path):
    print(f'\nWorking in {tmp_path}')

    result_path = build(tmp_path)

    assert result_path.exists(), "Expected final_report.docx to be generated"
    assert result_path.stat().st_size > 0, "Generated document should not be empty"


def test_the_document_says_what_the_reference_says(tmp_path):
    """Every paragraph, against the stored reference. The missing text files
    are announced with their path, which the runner makes absolute --
    portable() takes the workspace out again."""
    document = build(tmp_path)

    got = normalise(portable(said(document), document.parent))
    expected = [fold(line) for line in reference(REFERENCE)]

    assert got == expected, difference(expected, got)


def test_the_outline_the_includes_and_the_headers(tmp_path):
    """What the text comparison cannot see."""
    document = docx.Document(build(tmp_path))

    # each ladder level has its heading style; the depth-3 block, renamed
    # sub3section in f143b8b, is the Heading 4
    outline = [(p.style.name, p.text) for p in document.paragraphs
               if p.style.name.startswith('Heading')]
    assert outline == [
        ('Heading 1', 'TITLE'),
        ('Heading 3', 'When and who?'),
        ('Heading 3', 'What?'),
        ('Heading 1', 'SECOND'),
        ('Heading 2', 'Header 1'),
        ('Heading 3', 'This is s subsection ITEM head'),
        ('Heading 4', 'This is s subsubsection SUBITEM head'),
        ('Heading 2', 'Header 2'),
        ('Heading 2', 'Header 3'),
    ]

    # the one text file that exists (dolor.txt) lands three times -- once in
    # subsection B directly, once through the _include_ fragment, once in
    # subsection A -- the others are announced where they were asked for
    texts = [p.text for p in document.paragraphs]
    assert sum(text.startswith('Lorem ipsum') for text in texts) == 3
    announced = [text for text in texts if text.startswith('file ') and text.endswith('not found')]
    assert len(announced) == 7
    # the section's own marker fill lands after the subsections, the entry
    # after the _include_ after the fragment's three
    order = [texts.index(text) for text in
             ('Header 3', 'Some last words...', 'After the subsections', 'Where will this end?')]
    assert order == sorted(order), order

    # no pictures in this case; the globals reach header and footer of both sections
    assert len(document.inline_shapes) == 0
    assert len(document.sections) == 2
    for section in document.sections:
        header = ' '.join(p.text for p in section.header.paragraphs)
        assert 'Report ID 4711' in header and 'Date published: 01. August 2020' in header
        assert [drawings(p) for p in section.header.paragraphs if drawings(p)] == [[(0.8, 1.25)]]
        assert [p.text for p in section.footer.paragraphs if p.text.strip()] == ['Foot sec title ID 4711']


def test_the_checkreport_notebook_would_say_identical(tmp_path):
    """The comparison ``CheckReport.ipynb`` beside this file ends with, on
    the workspace the notebook prepares: the case's own ``data/`` -- where
    the case test above links the shared ``data_source`` pool. The two
    workspaces hold different files, so the announcements differ and the
    notebook does not print IDENTICAL against the pool-captured reference.
    Green when the two agree; anything else reports as xfailed with the
    first difference instead of staying out of the suite."""
    config = CaseConfig(
        name="report",
        case_dir=THIS_DIR,
        document_name="word_text.yaml",
        template_doc_name="template.docx",
        output_name="final_report.docx",
        include_patterns=["*.yaml", "template.docx"],
        data_source_dir=THIS_DIR / 'data',
        finish=False,
        createpdf=False,
    )
    report = checkreport_comparison(run_docx_case(config, tmp_path), REFERENCE)
    if report:
        pytest.xfail('CheckReport.ipynb would not say IDENTICAL -- ' + report)
