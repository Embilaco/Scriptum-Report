"""Document shape and the ``_scriptum_`` settings block.

The shape carries two rules on its own, which is the point of choosing it:
settings and ``_global_`` are root-only because an included fragment is a bare
sequence and has nowhere to put them, and the two document kinds are told apart
by the kind of their top node rather than by anything either has to declare.

The settings block is where the text format's quietest trap was: an unknown
``*key`` was logged as ignored and the parse continued, which is how
``*timeformat`` survived for years as a setting nobody had implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from Scriptum.rdf.loader import (CONTENT_KEY, Diagnostics, GLOBAL_KEY,
                                 SETTINGS_KEY, YamlSource, read_fragment,
                                 read_root)

MINIMAL = """
_scriptum_:
  version: 4
  documenttype: docx
"""


def read(text, name='doc.yaml'):
    diagnostics = Diagnostics()
    source = YamlSource.from_text(text.encode('utf-8'), name, diagnostics)
    header = read_root(source, diagnostics) if source else None
    return header, diagnostics


# ------------------------------------------------------------ the shapes

def test_a_root_document_is_a_mapping_of_the_three_reserved_keys(tmp_path,
                                                                 monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'data').mkdir()

    header, diagnostics = read("""
_scriptum_:
  version: 4
  documenttype: docx
  datadir: ./data
  documenttitle: 'A pudding'
  csvseparator: ';'
_global_:
  report:id: ID 4711
  report:status: Draft
_content_:
  - section:title:
      - head: Serving
""")

    assert not diagnostics, diagnostics.report()
    assert header.settings.version == 4
    assert header.settings.documenttype == 'docx'
    assert header.settings.datadir == Path('data')
    assert header.settings.documenttitle == 'A pudding'
    assert header.settings.csvseparator == ';'
    assert len(header.global_node.value) == 2
    assert len(header.content_node.value) == 1


def test_global_and_content_are_optional():
    header, diagnostics = read(MINIMAL)

    assert not diagnostics, diagnostics.report()
    assert header.global_node is None
    assert header.content_node is None


def test_an_included_fragment_is_a_bare_sequence():
    diagnostics = Diagnostics()
    source = YamlSource.from_text(b'- head: Serving\n', 'frag.yaml', diagnostics)

    assert read_fragment(source, diagnostics) is not None
    assert not diagnostics


def test_a_fragment_read_as_a_root_document_says_so():
    """It fails on the missing settings rather than half-working."""
    _, diagnostics = read('- head: Serving\n', 'frag.yaml')

    report = diagnostics.report()
    assert 'root document is a mapping' in report
    assert 'included fragment' in report


def test_a_root_document_read_as_a_fragment_says_so():
    diagnostics = Diagnostics()
    source = YamlSource.from_text(MINIMAL.encode('utf-8'), 'doc.yaml', diagnostics)

    assert read_fragment(source, diagnostics) is None
    report = diagnostics.report()
    assert 'sequence of entries' in report
    assert SETTINGS_KEY in report


def test_settings_are_rejected_in_a_fragment_by_the_shape_itself():
    """There is no check for this, and there does not need to be: a sequence
    has no top-level keys, so a fragment cannot carry a settings block."""
    diagnostics = Diagnostics()
    source = YamlSource.from_text(b'- head: Serving\n', 'frag.yaml', diagnostics)
    fragment = read_fragment(source, diagnostics)

    assert fragment is not None
    assert not hasattr(fragment, 'keys')


@pytest.mark.parametrize('key', ['section:title', 'content', '_contnet_'])
def test_an_unknown_top_level_key_is_rejected(key):
    _, diagnostics = read(MINIMAL + f'\n{key}:\n  - head: x\n')

    report = diagnostics.report()
    assert 'not allowed at the top level' in report
    assert CONTENT_KEY in report


def test_content_must_be_a_sequence():
    """Order matters there, and repetition is how a template block becomes two
    addressable instances."""
    _, diagnostics = read(MINIMAL + f'\n{CONTENT_KEY}: not-a-sequence\n')

    report = diagnostics.report()
    assert f'{CONTENT_KEY} must be a sequence' in report
    assert 'starts with "-"' in report


def test_global_must_be_a_mapping():
    """The mirror image of content, and for the mirror-image reason.

    A global fill matches on puretag alone, so it reaches every tag of that
    name in the document. There is no instance for a second entry with the
    same address to distinguish itself by, so a repeat would be a
    contradiction rather than an ordering -- and order is meaningless for the
    same reason. A mapping says exactly that; a sequence would not.
    """
    _, diagnostics = read(MINIMAL + f'\n{GLOBAL_KEY}: not-a-mapping\n')

    assert f'{GLOBAL_KEY} must be a mapping' in diagnostics.report()


def test_a_sequence_under_global_is_told_why_it_takes_no_dashes():
    _, diagnostics = read(MINIMAL + f'\n{GLOBAL_KEY}:\n  - report:id: x\n')

    report = diagnostics.report()
    assert f'{GLOBAL_KEY} must be a mapping' in report
    assert 'take no "-"' in report


def test_a_repeated_global_address_is_rejected():
    """The uniqueness a mapping claims has to be one the loader enforces.

    A mapping is what lost the elements argument -- PyYAML collapses duplicate
    keys to the last without a word. That objection does not reach here only
    because this loader never lets PyYAML construct a mapping: it walks the
    node graph, where the repeat is still visible.
    """
    _, diagnostics = read(f"""{MINIMAL}
{GLOBAL_KEY}:
  report:id: ID 4711
  report:status: Draft
  report:id: ID 0815
""")

    report = diagnostics.report()
    assert "duplicate key 'report:id'" in report
    assert f'at {GLOBAL_KEY}' in report


def test_global_entries_need_no_dashes():
    header, diagnostics = read(f"""{MINIMAL}
{GLOBAL_KEY}:
  report:id: ID 4711
  date:published: 01. August 2020
  report:version: 1.0
""")

    assert not diagnostics, diagnostics.report()
    assert len(header.global_node.value) == 3


def test_a_missing_settings_block_is_reported():
    _, diagnostics = read('_content_:\n  - head: x\n')

    assert f'{SETTINGS_KEY} is required' in diagnostics.report()


def test_the_settings_block_must_be_a_mapping():
    _, diagnostics = read('_scriptum_:\n  - version: 4\n')

    assert f'{SETTINGS_KEY} must be a mapping' in diagnostics.report()


# ---------------------------------------------------------- the schema

def test_an_unknown_setting_is_an_error_not_a_shrug():
    """The change from ``*key=value``. ``*timeformat`` was accepted and
    ignored for years because the text format logged unknown keys and moved
    on -- a typo cost nothing but an unchanged default and no diagnostic."""
    _, diagnostics = read(MINIMAL + '  timeformat: "%H:%M"\n')

    report = diagnostics.report()
    assert "unknown setting 'timeformat'" in report
    assert 'documenttitle' in report          # the message lists what is known


def test_a_setting_name_is_lowercased_like_every_other_key():
    """The text format lowercased addresses but not setting names, so a
    capitalised one fell through to 'unknown' and vanished."""
    header, diagnostics = read("""
_scriptum_:
  Version: 4
  DocumentType: docx
  DocumentTitle: 'A pudding'
""")

    assert not diagnostics, diagnostics.report()
    assert header.settings.documenttitle == 'A pudding'


@pytest.mark.parametrize('name', ['version', 'documenttype'])
def test_required_settings_are_required(name):
    lines = [line for line in MINIMAL.strip().splitlines()
             if not line.strip().startswith(name)]
    _, diagnostics = read('\n'.join(lines) + '\n')

    assert f'{name} is required' in diagnostics.report()


def test_the_version_floor_is_four():
    """The text format required 3. A separate floor means a document can be
    identified as one format or the other without guessing from its name."""
    _, diagnostics = read('_scriptum_:\n  version: 3\n  documenttype: docx\n')

    assert 'needs at least 4' in diagnostics.report()


@pytest.mark.parametrize('written', ['four', 'true', '4.0'])
def test_a_version_that_is_not_a_whole_number_is_rejected(written):
    _, diagnostics = read(
        f'_scriptum_:\n  version: {written}\n  documenttype: docx\n')

    assert 'must be a whole number' in diagnostics.report()


def test_a_boolean_version_is_rejected_although_bool_is_an_int():
    """``isinstance(True, int)`` is True, so this needs its own check."""
    _, diagnostics = read('_scriptum_:\n  version: true\n  documenttype: docx\n')

    assert 'a true/false value' in diagnostics.report()


def test_an_unknown_documenttype_lists_the_known_ones():
    _, diagnostics = read('_scriptum_:\n  version: 4\n  documenttype: pdf\n')

    report = diagnostics.report()
    assert 'not a known document type' in report
    assert 'docx' in report and 'pptx' in report


def test_documenttype_is_lowercased():
    header, diagnostics = read('_scriptum_:\n  version: 4\n  documenttype: DOCX\n')

    assert not diagnostics, diagnostics.report()
    assert header.settings.documenttype == 'docx'


def test_a_datadir_that_does_not_exist_is_reported():
    _, diagnostics = read(MINIMAL + '  datadir: ./nowhere\n')

    assert "does not exist" in diagnostics.report()


def test_a_windows_shaped_datadir_still_resolves(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'data').mkdir()

    header, diagnostics = read(MINIMAL + "  datadir: '.\\\\data'\n")

    assert not diagnostics, diagnostics.report()
    assert header.settings.datadir == Path('data')


@pytest.mark.parametrize('written', ["';;'", "''", '4'])
def test_a_separator_must_be_exactly_one_character(written):
    _, diagnostics = read(MINIMAL + f'  csvseparator: {written}\n')

    assert 'csvseparator must be' in diagnostics.report()


def test_a_setting_that_should_be_text_rejects_a_number():
    _, diagnostics = read(MINIMAL + '  documenttitle: 4711\n')

    report = diagnostics.report()
    assert 'must be text' in report
    assert 'Quote it' in report


@pytest.mark.parametrize('written', ['{a: 1}', '[1, 2]'])
def test_a_setting_must_be_a_single_value(written):
    _, diagnostics = read(MINIMAL + f'  documenttitle: {written}\n')

    assert 'must be a single value' in diagnostics.report()


def test_a_duplicate_setting_is_reported_and_the_first_one_stands():
    """Never last-wins. Silent overriding is the failure this format is
    shaped to avoid, and it must not come back through the header."""
    header, diagnostics = read("""
_scriptum_:
  version: 4
  documenttype: docx
  version: 5
""")

    assert "duplicate key 'version'" in diagnostics.report()
    assert header.settings.version == 4


def test_every_problem_is_reported_not_just_the_first():
    """Errors accumulate: a document with six mistakes reports six."""
    _, diagnostics = read("""
_scriptum_:
  version: 2
  documentype: docx
  csvseparator: ';;'
  datadir: ./nowhere
_global_: not-a-sequence
_contnet_:
  - a: 1
""")

    assert len(diagnostics) >= 6
    report = diagnostics.report()
    for expected in ['needs at least 4', "unknown setting 'documentype'",
                     'csvseparator must be', 'does not exist',
                     f'{GLOBAL_KEY} must be a mapping',
                     'not allowed at the top level',
                     'documenttype is required']:
        assert expected in report, expected


def test_diagnostics_point_at_the_offending_line():
    _, diagnostics = read(MINIMAL + '  timeformat: "%H:%M"\n')

    position = diagnostics.entries[0].position
    assert position.filename == 'doc.yaml'
    assert position.line == 5
    assert 'doc.yaml:5:' in str(diagnostics.entries[0])


def test_a_diagnostic_names_the_part_of_the_document_it_is_in():
    _, diagnostics = read(MINIMAL + '  timeformat: "%H:%M"\n')

    assert f'at {SETTINGS_KEY}' in str(diagnostics.entries[0])
