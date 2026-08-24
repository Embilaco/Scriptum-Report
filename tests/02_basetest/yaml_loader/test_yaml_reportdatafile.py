"""``ReportDataFile`` reads a ``.yaml`` document through the loader.

The name stays, because the thing has not changed: it is still the report data
file, in a different syntax. What changed is the extension -- and it is the
only thing the class reads now. The ``.rdf`` text parser that used to sit
behind the same name is gone, so anything that is not a ``.yaml`` document is
refused with a message rather than guessed at.

The surface a back end uses is ``tasks``, ``settings`` and ``errors``.
"""

from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest

from Scriptum.rdf.loader import DocumentError, load
from Scriptum.rdf.reportDataFile import ReportDataFile

TESTS_ROOT = Path(__file__).resolve().parents[2]

DOCUMENT = """
_scriptum_:
  version: 4
  documenttype: docx
_global_:
  report:status: Draft
_content_:
  - section:a:
      - head: Title
      - subsection:b:
          - head: Nested
"""


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(textwrap.dedent(text).lstrip('\n'), encoding='utf-8')
    return path


def test_a_yaml_document_is_read_through_the_loader(tmp_path):
    document = write(tmp_path, 'report.yaml', DOCUMENT)

    rdf = ReportDataFile(document)

    assert not rdf.errors
    assert rdf.settings.documenttype == 'docx'
    assert [t.what for t in rdf.tasks] == ['apply', '', 'apply', '', '']


def test_it_produces_exactly_what_load_produces(tmp_path):
    """The facade adds nothing of its own."""
    document = write(tmp_path, 'report.yaml', DOCUMENT)

    direct = load(document)
    through = ReportDataFile(document)

    assert ['.'.join(t.myAddress) for t in through.tasks] == \
        ['.'.join(t.myAddress) for t in direct.tasks]


@pytest.mark.parametrize('suffix', ['.yaml', '.yml'])
def test_either_extension_selects_the_loader(tmp_path, suffix):
    document = write(tmp_path, f'report{suffix}', DOCUMENT)

    assert ReportDataFile(document).settings.documenttype == 'docx'


@pytest.mark.parametrize('name', ['report.rdf', 'report.txt', 'report'])
def test_anything_but_a_yaml_document_is_refused(tmp_path, name):
    """The text format is not read any more, and it says so rather than
    falling through to a parser that does not exist or to a YAML parse of a
    file that is not one."""
    document = write(tmp_path, name, """
        *version=3
        *documenttype=docx
        section:a
        .head='Title'
    """)

    with pytest.raises(DocumentError) as caught:
        ReportDataFile(document)

    report = str(caught.value)
    assert 'not a report document' in report
    assert '.yaml' in report
    assert name in report


def test_errors_are_filled_and_the_exception_still_carries_them(tmp_path):
    """Readable either way: a caller that catches gets the whole set, and a
    caller that inspects the object afterwards finds the same list."""
    document = write(tmp_path, 'broken.yaml', """
        _scriptum_:
          version: 2
          documentype: docx
        _content_:
          - section:a:
              - head: x
    """)

    rdf = None
    with pytest.raises(DocumentError) as caught:
        rdf = ReportDataFile(document)

    assert rdf is None                      # the constructor did not return
    assert len(caught.value.diagnostics) >= 3
    assert 'needs at least 4' in str(caught.value)


def test_a_missing_file_is_reported_rather_than_silently_empty(tmp_path):
    with pytest.raises(DocumentError) as caught:
        ReportDataFile(tmp_path / 'absent.yaml')

    assert 'cannot read' in str(caught.value)


def test_the_reader_keeps_no_log(tmp_path):
    """``logs`` mirrored an assembled *text* file line by line, for debugging.

    A YAML document has no such assembly -- an include is spliced into a tree
    rather than pasted into a stream -- and the loader's diagnostics say more
    than the mirror ever did: file, line, column and the path through the
    document. Nothing outside the text parser ever read it, and it went before
    the parser did.
    """
    document = write(tmp_path, 'report.yaml', DOCUMENT)

    assert not hasattr(ReportDataFile(document), 'logs')


def test_the_translated_corpus_loads_through_the_facade(tmp_path):
    """One real document, includes and all, through the public entry point."""
    source = TESTS_ROOT / '02_basetest' / 'rdf'
    for sibling in source.glob('*.yaml'):
        shutil.copy(sibling, tmp_path / sibling.name)
    shutil.copytree(TESTS_ROOT / 'data_source', tmp_path / 'data',
                    dirs_exist_ok=True)

    rdf = ReportDataFile(tmp_path / 'rdf_big_docx.yaml')

    assert not rdf.errors
    assert len(rdf.tasks) > 50
    assert rdf.tasks[-1].path == ['_global_']


def test_two_documents_in_one_interpreter_do_not_see_each_other(tmp_path):
    """The text parser numbered repeats through a process-global tree and
    counted serials on the class, which is why one root document per
    interpreter used to be a rule. Nothing is kept between documents now: the
    second document reads exactly as it would have on its own."""
    first = write(tmp_path, 'first.yaml', DOCUMENT)
    second = write(tmp_path, 'second.yaml', DOCUMENT)

    alone = ReportDataFile(first)
    ReportDataFile(first)
    again = ReportDataFile(second)

    assert [t.serial for t in again.tasks] == [t.serial for t in alone.tasks]
    assert [t.myAddress for t in again.tasks] == [t.myAddress for t in alone.tasks]
    assert again.tasks[0].serial == 1
