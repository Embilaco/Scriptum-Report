"""What each fixture's ``.yaml`` generates, against what its ``.rdf`` did.

This is the safety net for the last piece of the migration. Every docx case
test asserts only that a file was written and is not empty, which is how the
clone-ordering defect fixed in `b1a4afd` lived in shipped code for years with a
green suite. This reads the finished documents back instead.

Why a stored reference rather than a live comparison
----------------------------------------------------
It began by generating both sides in one run. That stopped working the moment
``StructuredElement.path`` became canonical: the text parser emits
``section:title`` where the tree now says ``section:title::1``, so the *old*
side degrades and there is nothing left to compare against.

So the reference is captured instead. ``expected/*.json`` is what each ``.rdf``
generated at `44267a8`, the last commit before the tree changed. That decouples
the check from a parser which is on its way out -- when the text format goes,
these keep working.

What is compared
----------------
The sequence of non-empty paragraph texts, then every table cell, with runs of
digits collapsed to ``#``. The collapsing is for dates: a fixture using
``date:now`` is evaluated when the document is built, and the reference was
built on another day. What the comparison exists for -- a paragraph missing, an
extra one, two in the wrong order -- survives it.

One trap this had to avoid
--------------------------
The reader keeps **process-global state** and one root document per interpreter
is the standing rule, so :func:`reset` clears it before each generation rather
than relying on the suite's autouse fixture. A previous session was misled by
exactly that.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

import docx
import pytest

import Scriptum
from Scriptum.rdf.reportDataFile import ReportDataFile
from Scriptum.rdf.tasks import ReportTask

TESTS_ROOT = Path(__file__).resolve().parents[2]
EXPECTED = Path(__file__).resolve().parent / 'expected'
DIGITS = re.compile(r'\d+')

#: (case directory relative to tests/, fixture stem, template file)
CASES = [
    ('02_basetest/docx_basic/simple', 'word_simple', 'template.docx'),
    ('02_basetest/docx_basic/images', 'word_images', 'template_image.docx'),
    ('02_basetest/docx_basic/tables', 'word_tables', 'template_table.docx'),
    ('02_basetest/docx_basic/text', 'word_text', 'template_text.docx'),
    ('04_examples/wordreport', 'word_input', 'template.docx'),
    ('04_examples/essay', 'essay', 'essay.docx'),
]

#: Why none of them match yet. Removing this and the marker is the last step.
NOT_WIRED = (
    'StructuredElement.path and the addressbook are keyed on template names, '
    'so a task carrying the four-slot form finds nothing and the run fills '
    'nothing, saying "cannot find section: section:x::1"'
)


def reset():
    """Clear the process-global state the reader keeps between generations."""
    ReportTask._serial = 0
    ReportTask._tree = {}
    ReportTask._allPaths = {}
    ReportTask._newPaths = {}
    ReportDataFile._depth = 0
    ReportDataFile._global_settings = {}


def prepare(case):
    """A directory holding the fixtures, the template and a ``data``."""
    work = Path(tempfile.mkdtemp())
    source = TESTS_ROOT / case

    for pattern in ('*.yaml', '*.docx'):
        for path in source.glob(pattern):
            shutil.copy(path, work)

    own_data = source / 'data'
    shutil.copytree(own_data if own_data.is_dir() else TESTS_ROOT / 'data_source',
                    work / 'data', dirs_exist_ok=True)
    return work


def generate(work, document_name, template, output='out.docx'):
    """Build one document. Returns what the run printed, for diagnosis."""
    os.chdir(work)
    reset()
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        rdf = ReportDataFile(document_name)
        managed = Scriptum.ManagedDocx(template, rdf)
        managed.typesetting(rdf)
        managed.save(output)
    return printed.getvalue()


def spoken(path):
    """What the finished document says, in order, dates neutralised."""
    document = docx.Document(path)
    said = [p.text.strip() for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            said.extend(cell.text.strip() for cell in row.cells)
    return [DIGITS.sub('#', line) for line in said if line]


def reference(stem):
    return json.loads((EXPECTED / f'{stem}.json').read_text(encoding='utf-8'))


def difference(expected, got):
    """A readable account of the first place the two diverge."""
    for index, (a, b) in enumerate(zip(expected, got)):
        if a != b:
            return (f'first difference at line {index}:\n'
                    f'  expected: {a[:120]!r}\n'
                    f'  got     : {b[:120]!r}')
    if len(expected) != len(got):
        longer, name = ((expected, 'the reference') if len(expected) > len(got)
                        else (got, 'this run'))
        extra = longer[min(len(expected), len(got)):][:4]
        return (f'{name} says {abs(len(expected) - len(got))} more line(s): '
                f'{[line[:60] for line in extra]}')
    return 'no difference'


def compare(case, stem, template):
    work = prepare(case)
    printed = generate(work, f'{stem}.yaml', template)
    got = spoken(work / 'out.docx')
    expected = reference(stem)
    complaints = [line for line in printed.splitlines()
                  if 'ERROR' in line or 'WARNING' in line]
    return expected, got, complaints


# ------------------------------------------------------- the harness works

def test_every_case_has_a_reference():
    """A missing reference would make a comparison vacuous."""
    for case, stem, template in CASES:
        assert (EXPECTED / f'{stem}.json').is_file(), stem
        assert len(reference(stem)) > 3, stem


def test_generating_the_same_document_twice_says_the_same_thing():
    """Self-test of the comparison, including the digit collapsing: if this
    fails the harness is measuring its own noise rather than the translation."""
    case, stem, template = CASES[0]
    work = prepare(case)

    generate(work, f'{stem}.yaml', template, 'once.docx')
    generate(work, f'{stem}.yaml', template, 'twice.docx')

    assert spoken(work / 'once.docx') == spoken(work / 'twice.docx')


def test_the_difference_report_notices_what_it_should():
    assert 'first difference at line 1' in difference(['a', 'b'], ['a', 'c'])
    assert 'more line(s)' in difference(['a', 'b'], ['a'])
    assert difference(['a'], ['a']) == 'no difference'


# ---------------------------------------------------------- the comparison

@pytest.mark.parametrize('case, stem, template', CASES)
@pytest.mark.xfail(strict=True, reason=NOT_WIRED)
def test_the_yaml_document_says_what_the_rdf_document_said(case, stem, template):
    """The last step of the migration makes these pass.

    ``strict=True`` on purpose: when the back end starts resolving the new
    addresses these begin passing, and a strict xfail turns that into a
    failure -- the only reliable way for the change to announce itself
    rather than being noticed months later.
    """
    expected, got, complaints = compare(case, stem, template)

    assert got == expected, (
        difference(expected, got)
        + chr(10) + 'the run said: ' + repr(complaints[:3]))
