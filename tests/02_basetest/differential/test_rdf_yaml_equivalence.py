"""Generate the same report from its ``.rdf`` and its ``.yaml`` and compare.

This is the safety net for the last piece of the migration, and it exists
because of what the DOCX board now warns about placement: a mistake there
produces a document that is **plausible and wrong** rather than one that fails.
The clone-ordering defect fixed in `b1a4afd` lived in shipped code for years
with a green suite, because every case test asserts only that a file was
written and is not empty.

So this reads the finished documents back. If the corpus translation is
faithful and the back end resolves the new addresses, the two documents say the
same things in the same order.

What is compared
----------------
The sequence of non-empty paragraph texts, then every table cell, with runs of
digits collapsed to ``#``. The collapsing is for dates: a fixture using
``date:now`` is evaluated once per generation, and the two runs can straddle a
second. Everything the comparison is actually for -- a paragraph missing, an
extra one, two in the wrong order -- survives it.

One trap this had to avoid
--------------------------
Both readers keep **process-global state**, and one root document per
interpreter is the standing rule. Generating twice in one test breaks it unless
the state is reset in between, and a previous session was misled by exactly
that. :func:`reset` does it explicitly rather than relying on the suite's
autouse fixture, because the reset has to happen *between* the two generations
and not merely around the test.
"""

from __future__ import annotations

import contextlib
import io
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
DIGITS = re.compile(r'\d+')

#: (case directory relative to tests/, fixture stem, template file)
DOCX_CASES = [
    ('02_basetest/docx_basic/simple', 'word_simple', 'template.docx'),
    ('02_basetest/docx_basic/images', 'word_images', 'template_image.docx'),
    ('02_basetest/docx_basic/tables', 'word_tables', 'template_table.docx'),
    ('02_basetest/docx_basic/text', 'word_text', 'template_text.docx'),
    ('04_examples/wordreport', 'word_input', 'template.docx'),
    ('04_examples/essay', 'essay', 'essay.docx'),
]

#: Why the YAML side does not match yet. Removing this and the xfail marker is
#: the last step of the migration.
NOT_WIRED = (
    'StructuredElement.path and the addressbook are keyed on template names, '
    'so a task carrying the four-slot form finds nothing: the run reports '
    '"cannot find section: section:x::1" and fills nothing'
)


def reset():
    """Clear the process-global state both readers keep between two runs."""
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

    for pattern in ('*.rdf', '*.yaml', '*.docx'):
        for path in source.glob(pattern):
            shutil.copy(path, work)

    own_data = source / 'data'
    shutil.copytree(own_data if own_data.is_dir() else TESTS_ROOT / 'data_source',
                    work / 'data', dirs_exist_ok=True)
    return work


def generate(work, document_name, template, output):
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


def difference(left, right):
    """A readable account of the first place the two documents diverge."""
    for index, (a, b) in enumerate(zip(left, right)):
        if a != b:
            return (f'first difference at line {index}:\n'
                    f'  rdf : {a!r}\n'
                    f'  yaml: {b!r}')
    if len(left) != len(right):
        longer, name = (left, 'rdf') if len(left) > len(right) else (right, 'yaml')
        extra = longer[min(len(left), len(right)):][:5]
        return f'{name} says {abs(len(left) - len(right))} more line(s): {extra}'
    return 'no difference'


# --------------------------------------------------------- the harness works

@pytest.mark.parametrize('case, stem, template', DOCX_CASES)
def test_the_rdf_side_produces_a_document_that_says_something(case, stem, template):
    """Without this, a broken harness would make every comparison below xfail
    for the wrong reason and look like a known gap."""
    work = prepare(case)

    generate(work, f'{stem}.rdf', template, 'out.docx')

    assert len(spoken(work / 'out.docx')) > 3


def test_comparing_a_document_with_itself_matches():
    """Self-test of the comparison, including the digit collapsing: a document
    generated twice from the same source must compare equal, or the harness is
    measuring its own noise rather than the translation."""
    case, stem, template = DOCX_CASES[0]
    work = prepare(case)

    generate(work, f'{stem}.rdf', template, 'once.docx')
    generate(work, f'{stem}.rdf', template, 'twice.docx')

    assert spoken(work / 'once.docx') == spoken(work / 'twice.docx')


def test_the_comparison_notices_a_missing_line():
    """And a self-test of the difference report itself."""
    assert 'first difference at line 1' in difference(['a', 'b'], ['a', 'c'])
    assert 'more line(s)' in difference(['a', 'b'], ['a'])
    assert difference(['a'], ['a']) == 'no difference'


# ------------------------------------------------------------ the comparison

@pytest.mark.parametrize('case, stem, template', DOCX_CASES)
@pytest.mark.xfail(strict=True, reason=NOT_WIRED)
def test_the_yaml_document_says_what_the_rdf_document_says(case, stem, template):
    """The last step of the migration makes these pass.

    ``strict=True`` on purpose: when the back end starts resolving the new
    addresses these begin passing, and a strict xfail turns that into a
    failure -- which is the only reliable way for the change to announce
    itself rather than being noticed months later.
    """
    work = prepare(case)

    generate(work, f'{stem}.rdf', template, 'from_rdf.docx')
    printed = generate(work, f'{stem}.yaml', template, 'from_yaml.docx')

    from_rdf = spoken(work / 'from_rdf.docx')
    from_yaml = spoken(work / 'from_yaml.docx')

    complaints = [line for line in printed.splitlines()
                  if 'ERROR' in line or 'WARNING' in line]
    assert from_rdf == from_yaml, (
        f'{difference(from_rdf, from_yaml)}\n'
        f'the yaml run said: {complaints[:3]}')
