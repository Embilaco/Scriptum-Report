"""The node graph: positions, duplicate keys, encoding.

``yaml.safe_load`` is not usable for this format, and these tests are why.
Its output has no positions, so no diagnostic can point at a line; and its
mapping constructor keeps the *last* of a repeated key without a word, which
is exactly the silent overwrite that ruled mappings out for elements.
"""

from __future__ import annotations

import pytest

from Scriptum.rdf.loader import Diagnostics, DocumentError, Position, YamlSource
from Scriptum.rdf.loader import nodes


def source_of(text, name='doc.yaml'):
    diagnostics = Diagnostics()
    source = YamlSource.from_text(text, name, diagnostics)
    return source, diagnostics


# ------------------------------------------------------------- positions

def test_marks_are_reported_one_based():
    """PyYAML counts lines and columns from 0; editors and humans from 1.

    Converting in one place means no caller has to remember to, and an
    off-by-one here would send every diagnostic one line off target.
    """
    source, diagnostics = source_of(b'a: 1\nb: 2\n')
    assert not diagnostics

    _, second_key, _ = nodes.items(source.root, source, diagnostics)[1]
    assert second_key.start_mark.line == 1          # what PyYAML says
    assert source.position(second_key).line == 2    # what we say
    assert source.position(second_key).column == 1


def test_a_position_prints_as_file_line_column():
    assert str(Position('doc.yaml', 4, 7)) == 'doc.yaml:4:7'


def test_a_position_with_no_line_prints_only_the_file():
    """Used when the whole file is at fault. ':0:0' would send a reader
    looking for a line that is not the one to look at."""
    assert str(Position('doc.yaml', 0, 0)) == 'doc.yaml'


# --------------------------------------------------------- duplicate keys

def test_a_duplicate_key_is_reported_and_names_the_first_line():
    source, diagnostics = source_of(b'a: 1\nb: 2\na: 3\n')

    kept = nodes.items(source.root, source, diagnostics)

    assert [key for key, _, _ in kept] == ['a', 'b']
    assert len(diagnostics) == 1
    message = str(diagnostics.entries[0])
    assert "duplicate key 'a'" in message
    assert 'first written at line 1' in message
    assert 'doc.yaml:3:1' in message


def test_pyyaml_would_have_kept_the_last_one_silently():
    """The behaviour being guarded against, stated so the guard has a reason."""
    import yaml
    assert yaml.safe_load('a: 1\na: 3\n') == {'a': 3}


def test_pairs_are_raw_and_keep_duplicates():
    """The walker needs to see the repeat; deduplication is a later decision."""
    source, _ = source_of(b'a: 1\na: 3\n')
    assert len(nodes.pairs(source.root)) == 2


# ------------------------------------------------------------ node kinds

@pytest.mark.parametrize('text, expected', [
    (b'k: {a: 1}\n', 'a mapping'),
    (b'k: [1, 2]\n', 'a sequence'),
    (b'k: hello\n', 'a scalar'),
    (b'k:\n', 'empty'),
])
def test_describe_names_the_kind(text, expected):
    source, diagnostics = source_of(text)
    _, _, value_node = nodes.items(source.root, source, diagnostics)[0]
    assert nodes.describe(value_node) == expected


def test_null_and_the_empty_string_are_different():
    """``- BackCover:`` is an empty container; ``- rf2: ''`` is a fill whose
    value is the empty string. The format leans on YAML telling them apart."""
    source, diagnostics = source_of(b"empty:\nblank: ''\n")
    walked = dict((key, value) for key, _, value in
                  nodes.items(source.root, source, diagnostics))

    assert nodes.is_null(walked['empty'])
    assert not nodes.is_null(walked['blank'])
    assert source.value(walked['blank']) == ''


# --------------------------------------------------------------- loading

def test_scalars_are_still_constructible_after_the_parser_is_disposed():
    """Non-obvious dependency, so it is pinned rather than assumed.

    Values are built lazily -- the walk wants the node far more often than the
    value -- while the parser's state machine is released as soon as the
    document is composed. That only works because construction of an
    already-composed scalar does not go back through the parser.
    """
    source, _ = source_of(b'k: 0755\n')
    _, value_node = nodes.pairs(source.root)[0]
    assert source.value(value_node) == 755


def test_a_utf8_document_round_trips():
    source, diagnostics = source_of('k: Grüße\n'.encode('utf-8'))
    assert not diagnostics
    _, value_node = nodes.pairs(source.root)[0]
    assert source.value(value_node) == 'Grüße'


def test_a_utf16_document_is_decoded_from_its_bom():
    """YAML defines UTF-8, plus UTF-16/32 when a BOM says so. Feeding bytes
    rather than a decoded string is what lets PyYAML apply that rule -- and it
    is the whole of the fix for ``.rdf`` being read in the platform default."""
    source, diagnostics = source_of('k: Grüße\n'.encode('utf-16'))
    assert not diagnostics
    _, value_node = nodes.pairs(source.root)[0]
    assert source.value(value_node) == 'Grüße'


def test_malformed_yaml_becomes_a_diagnostic_not_an_exception():
    """Errors accumulate; nothing raises until the root document says so."""
    source, diagnostics = source_of(b'_scriptum_:\n  - a\n b: c\n')

    assert source is None
    assert len(diagnostics) == 1
    assert 'doc.yaml:3:2' in str(diagnostics.entries[0])


def test_an_empty_document_is_reported():
    source, diagnostics = source_of(b'')
    assert source is None
    assert 'empty' in diagnostics.report()


def test_a_missing_file_is_reported_rather_than_raised():
    diagnostics = Diagnostics()
    assert YamlSource.from_path('no-such-file.yaml', diagnostics) is None
    assert len(diagnostics) == 1


def test_from_path_reads_a_real_file(tmp_path):
    document = tmp_path / 'frag.yaml'
    document.write_text('- head: Serving\n', encoding='utf-8')

    diagnostics = Diagnostics()
    source = YamlSource.from_path(document, diagnostics)

    assert not diagnostics
    assert nodes.is_sequence(source.root)
    assert source.filename == str(document)


# ----------------------------------------------------------- diagnostics

def test_diagnostics_are_reported_in_line_order_within_a_file():
    """The walk checks a document's top-level keys before the settings block
    nested inside it, so insertion order can put line 7 above line 3."""
    diagnostics = Diagnostics()
    source, _ = source_of(b'a: 1\nb: 2\nc: 3\n')
    third = nodes.pairs(source.root)[2][0]
    first = nodes.pairs(source.root)[0][0]

    diagnostics.error('later', node=third, filename='doc.yaml')
    diagnostics.error('earlier', node=first, filename='doc.yaml')

    assert [d.message for d in diagnostics.ordered()] == ['earlier', 'later']
    assert diagnostics.report().index('earlier') < diagnostics.report().index('later')


def test_files_keep_the_order_they_were_first_reported_in():
    """Across files that order is include order, which carries meaning."""
    diagnostics = Diagnostics()
    diagnostics.error('in second file', filename='b.yaml')
    diagnostics.error('in first file', filename='a.yaml')

    assert [d.position.filename for d in diagnostics.ordered()] == \
        ['b.yaml', 'a.yaml']


def test_raise_if_any_carries_every_diagnostic():
    diagnostics = Diagnostics()
    diagnostics.error('one', filename='a.yaml')
    diagnostics.error('two', filename='a.yaml')

    with pytest.raises(DocumentError) as caught:
        diagnostics.raise_if_any()

    assert len(caught.value.diagnostics) == 2
    assert 'one' in str(caught.value) and 'two' in str(caught.value)


def test_raise_if_any_is_quiet_when_there_is_nothing_wrong():
    Diagnostics().raise_if_any()


def test_a_diagnostic_with_no_filename_still_renders():
    """__str__ returning None is a TypeError, which would turn a report about
    someone's document into a crash inside the error reporting itself."""
    assert str(Position(None, 0, 0)) == '<document>'
    assert str(Position(None, 3, 1)) == '<document>:3:1'

    diagnostics = Diagnostics()
    diagnostics.error('something went wrong')
    assert 'something went wrong' in diagnostics.report()
