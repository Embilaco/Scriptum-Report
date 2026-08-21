"""``ReportDataFile`` reads a ``.yaml`` document through the loader.

The name stays, because the thing has not changed: it is still the report data
file, in a different syntax. What changes is the extension, and that is what
selects the reader.

The surface a back end uses is ``tasks``, ``settings`` and ``errors``, and all
three are filled the same way either reader fills them.
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


def test_an_rdf_still_goes_down_the_text_path(tmp_path):
    document = write(tmp_path, 'report.rdf', """
        *version=3
        *documenttype=docx
        section:a
        .head='Title'
    """)

    rdf = ReportDataFile(document)

    assert not rdf.errors
    assert not any('::' in a for t in rdf.tasks for a in t.myAddress)


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


def test_neither_reader_keeps_a_log(tmp_path):
    """``logs`` mirrored an assembled *text* file line by line, for debugging.

    A YAML document has no such assembly -- an include is spliced into a tree
    rather than pasted into a stream -- and the loader's diagnostics say more
    than the mirror ever did: file, line, column and the path through the
    document. Nothing outside the parser ever read it.
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


def test_an_unknown_setting_is_an_error_in_the_text_format_too(tmp_path):
    """The consequence of dropping the log, and the right one.

    An unrecognised ``*key`` used to be written to the log as an ignored entry
    while the parse carried on -- the tolerance that hid ``*timeformat`` for
    years. With no log that ignore would be completely silent, so it is now an
    error naming what is known, which is what the YAML schema already did.
    """
    document = write(tmp_path, 'report.rdf', """
        *version=3
        *documenttype=docx
        *timeformat='%H:%M'
        section:a
        .head='Title'
    """)

    with pytest.raises(Exception) as caught:
        ReportDataFile(document)

    report = str(caught.value)
    assert 'Unknown setting *timeformat' in report
    assert 'documenttitle' in report, 'the message lists what is known'
