"""The tables docx case, built and read back.

``word_tables.yaml`` fills the title section of ``template.docx`` with
tables from the case's own ``data/``: a fixed revisions table that takes the
``_global_`` author, ``table:inline`` from a CSV, a ``table:generic`` clone
added at the marker, and ``table:orange`` -- a blueprint that lives in the
title section itself, not in ``section:template`` -- used twice: filled in
place for its first instance (description ``from: row1``) and **added at a
marker** for its second. The add works since the lookup was widened per the
decision on the DOCX board (*Can a block flagged `template` outside
section:template be added at a marker?*): a bare name matches any flagged
block, the template section first. Until then the add was refused with two
warnings, which this file pinned. A test that only checks the file is there
proves none of that, so this module reads the document back:

* what it *says*, against ``expected/word_tables.json`` (re-captured with
  the widened lookup; before that at `a58702e`, when the fixture got its own
  data and real CSV files);
* what it *shows*: the tables' shapes and the CSV content in their cells --
  including what the clone shows where a CSV cell is empty.
"""

import re
from pathlib import Path
import sys

import pytest

docx = pytest.importorskip('docx')

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = Path(__file__).resolve().parent.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT))

from _setup_docx_basic import *
from common_case import CaseConfig, run_docx_case
from common_case import said, normalise, reference, difference, portable, fold
from common_case import checkreport_comparison

REFERENCE = THIS_DIR / 'expected' / 'word_tables.json'

def build(tmp_path):
    """The document, typeset the way every docx case is."""
    config = CaseConfig(
        name="report",
        case_dir=THIS_DIR,
        document_name="word_tables.yaml",
        template_doc_name="template.docx",
        output_name="final_report.docx",
        include_patterns=["*.yaml", "template.docx"],
        data_source_dir=THIS_DIR / 'data',
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
    """Every paragraph, then every table cell, against the stored reference."""
    document = build(tmp_path)

    got = normalise(portable(said(document), document.parent))
    expected = [fold(line) for line in reference(REFERENCE)]

    assert got == expected, difference(expected, got)


def test_the_tables_their_content_and_the_in_content_blueprint(tmp_path, capsys):
    """What the text comparison cannot see, and what the run says about it.

    The blueprint of the title section is content for its first instance and
    a template for its second: filled in place, then cloned to the marker.
    A run of this fixture warns about nothing any more.
    """
    document = docx.Document(build(tmp_path))
    warnings = [line for line in capsys.readouterr().out.splitlines() if 'WARNING' in line]

    assert warnings == []

    # title table, revisions table, table:inline from instructionsrocket.csv,
    # table:orange in place from table2.csv, the table:generic clone from
    # technologies.csv, and the table:orange clone added at the marker
    tables = document.tables
    assert [(len(t.rows), len(t.columns)) for t in tables] == [
        (1, 2), (5, 3), (4, 3), (8, 3), (6, 4), (6, 4)]

    # date:creation is `date: today` in the default ISO date format. It was
    # `date: now` until the seconds made a CI run flaky -- this fixture is
    # compared against its hand translation in two separate loads, and a
    # second ticking between them failed the comparison.
    assert re.search(r'^Date: \d{4}-\d{2}-\d{2}$', tables[0].cell(0, 1).text)

    # the fixed revisions table took the _global_ author
    assert [c.text for c in tables[1].rows[0].cells] == ['Date', 'Who', 'What']
    assert [c.text for c in tables[1].rows[1].cells] == ['', 'James Bond', 'Initial revision']

    # the CSV content, header rows and a data row each
    assert [c.text for c in tables[2].rows[0].cells] == ['Check', 'Task', 'Importance']
    assert [c.text for c in tables[2].rows[1].cells][:2] == ['Rocket', 'ask someone to get one for you']
    assert [c.text for c in tables[3].rows[0].cells] == ['Rank', 'Country', 'Income']
    assert [c.text for c in tables[3].rows[1].cells] == ['1', 'Luxembourg', '$140,941']
    assert [c.text for c in tables[4].rows[1].cells] == [
        'Technology', 'Typical Period', 'Key Strengths', 'Key Limitations']

    # the clone carries the same CSV -- and, unlike the generic clone from
    # section:template, its blueprint has sample text in its cells. Since the
    # empty-cell decision (2026-08-25) every cell of the CSV's grid is
    # written -- a blank where the CSV is empty or the row short -- so the
    # sample text ('overwritten' lived here) cannot show through any more
    assert [c.text for c in tables[5].rows[1].cells] == [
        'Technology', 'Typical Period', 'Key Strengths', 'Key Limitations']
    assert [c.text for c in tables[5].rows[0].cells] == [
        'Comparison of writing and typography technologies.', ' ', ' ', ' ']

    # the captions: the descriptions given, the one taken from row1, and the
    # clone's -- it was added without a description
    captions = [p.text for p in document.paragraphs if p.text.startswith('Table ')]
    assert captions == ['Table 1: rocket preparation', 'Table 1: Income by country',
                        "Table 4: tech isn't it", 'Table 1: ']
    assert not any('non existing file' in p.text for p in document.paragraphs)


def test_the_checkreport_notebook_would_say_identical(tmp_path):
    """The comparison ``CheckReport.ipynb`` beside this file ends with --
    plain, no ``comparable()`` -- on a plain build (the notebook itself runs
    ``finish=True``, which changes nothing a text comparison sees unless Word
    refreshes a field). Green when the notebook would print IDENTICAL;
    anything else reports as xfailed with the first difference."""
    report = checkreport_comparison(build(tmp_path), REFERENCE)
    if report:
        pytest.xfail('CheckReport.ipynb would not say IDENTICAL -- ' + report)
