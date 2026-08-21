"""Includes: position places the content, and a fragment is relative to it.

The stated purpose of includes is reusable fragments -- a chapter such as
*experimental results* recurring with the same structure and different content.
Three things here serve that and are worth reading for:

* a fragment carries only its own level and the caller decides where it
  attaches, so the same file can be included in more than one place;
* including one fragment **twice** works, which the text format's shared
  visited set refused as a cycle;
* glob matches are **sorted**, because order defines instance identity and
  filesystem order does not.
"""

from __future__ import annotations

import textwrap

import pytest

from Scriptum.rdf.loader import (Container, Diagnostics, Fill, MAX_INCLUDE_DEPTH,
                                 YamlSource, read_content, read_root, walk)

SETTINGS = '_scriptum_:\n  version: 4\n  documenttype: docx\n'


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(textwrap.dedent(text).lstrip('\n'), encoding='utf-8')
    return path


def read(tmp_path, content, name='doc.yaml'):
    """Write *content* as a root document in tmp_path and walk it."""
    path = write(tmp_path, name, SETTINGS + textwrap.dedent(content))

    diagnostics = Diagnostics()
    source = YamlSource.from_path(path, diagnostics)
    header = read_root(source, diagnostics)
    tree = read_content(header.content_node, source, header.settings,
                        diagnostics)
    return tree, diagnostics


def canonicals(entries):
    return [e.address.canonical for e in entries]


# ------------------------------------------------------------- splicing

def test_a_fragment_lands_where_the_entry_sits(tmp_path):
    write(tmp_path, 'tools.yaml', """
        - subsection:tool:
            - head: Pepper
    """)
    tree, diagnostics = read(tmp_path, """
        _content_:
          - section:tool:
              - head: Tools
              - _include_: tools.yaml
              - head: After
    """)

    assert not diagnostics, diagnostics.report()
    children = tree[0].children
    assert [type(c).__name__ for c in children] == ['Fill', 'Container', 'Fill']
    assert children[1].address.canonical == 'subsection:tool::1'


def test_a_fragment_is_read_at_the_depth_it_is_included_at(tmp_path):
    """Its entries are ladder-checked where they land, not where they were
    written -- which is the whole of "relative to the inclusion point"."""
    write(tmp_path, 'part.yaml', '- subsection:b:\n    - head: x\n')
    _, diagnostics = read(tmp_path, """
        _content_:
          - _include_: part.yaml
    """)

    assert "namespace must be 'section'" in diagnostics.report()


def test_the_same_fragment_may_be_included_in_two_different_places(tmp_path):
    """The reuse the format exists for: one file, written once, attached
    wherever it fits."""
    write(tmp_path, 'results.yaml', '- subsection:results:\n    - head: x\n')
    tree, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: results.yaml
          - section:b:
              - _include_: results.yaml
    """)

    assert not diagnostics, diagnostics.report()
    assert canonicals(tree[0].children) == ['subsection:results::1']
    assert canonicals(tree[1].children) == ['subsection:results::1']


def test_including_one_fragment_twice_in_one_place_numbers_both(tmp_path):
    """Refused by the text format, which kept a shared set of every file it
    had seen and reported the second include as a cycle -- a cycle it was not.

    Sharing the parent's counters is what makes the two copies distinct
    instances rather than duplicates.
    """
    write(tmp_path, 'chapter.yaml', '- subsection:results:\n    - head: x\n')
    tree, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: chapter.yaml
              - _include_: chapter.yaml
    """)

    assert not diagnostics, diagnostics.report()
    assert canonicals(tree[0].children) == ['subsection:results::1',
                                            'subsection:results::2']


def test_an_include_inside_a_marker_adds_at_that_marker(tmp_path):
    """Position places the content. In the text format an ``@`` inside an
    included file changed the *caller's* marker and left it changed after the
    include returned; here the include either sits in the marker's sequence or
    it does not."""
    write(tmp_path, 'more.yaml', '- image:generic: {file: a.png}\n')
    tree, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - subsection:b:
                  - marker:content:
                      - _include_: more.yaml
    """)

    assert not diagnostics, diagnostics.report()
    added = tree[0].children[0].children[0].children[0]
    assert isinstance(added, Fill)
    assert added.marker == 'marker:content'


def test_a_fragment_may_include_another(tmp_path):
    write(tmp_path, 'inner.yaml', '- head: inner\n')
    write(tmp_path, 'outer.yaml', """
        - head: outer
        - _include_: inner.yaml
    """)
    tree, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: outer.yaml
    """)

    assert not diagnostics, diagnostics.report()
    assert [str(c.value) for c in tree[0].children] == ['outer', 'inner']


# ---------------------------------------------------------------- globs

def test_glob_matches_are_sorted(tmp_path):
    """glob returns filesystem order, which Python does not guarantee. Because
    order defines instance identity, the same inputs could otherwise produce
    different addresses on different machines, with nothing reporting it."""
    for name in ['part-c.yaml', 'part-a.yaml', 'part-b.yaml']:
        write(tmp_path, name, f'- head: {name[5]}\n')

    tree, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: 'part-*.yaml'
    """)

    assert not diagnostics, diagnostics.report()
    assert [str(c.value) for c in tree[0].children] == ['a', 'b', 'c']


def test_each_glob_match_continues_the_numbering(tmp_path):
    for name in ['part-a.yaml', 'part-b.yaml']:
        write(tmp_path, name, '- subsection:part:\n    - head: x\n')

    tree, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: 'part-*.yaml'
    """)

    assert not diagnostics, diagnostics.report()
    assert canonicals(tree[0].children) == ['subsection:part::1',
                                            'subsection:part::2']


def test_a_glob_that_matches_the_including_document_reports_it(tmp_path):
    """``*.yaml`` sweeps up the root document too, which is neither a fragment
    nor something to recurse into. Both facts are reported rather than one of
    them being silently survivable."""
    write(tmp_path, 'part-a.yaml', '- head: x\n')

    _, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: '*.yaml'
    """)

    assert 'includes itself' in diagnostics.report()


def test_a_glob_matching_nothing_is_an_error(tmp_path):
    _, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: 'nothing-*.yaml'
    """)

    assert 'matched no files' in diagnostics.report()


def test_a_missing_file_is_an_error(tmp_path):
    _, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: absent.yaml
    """)

    assert 'cannot find' in diagnostics.report()


# ------------------------------------------------------------ resolution

def test_a_path_is_relative_to_the_file_doing_the_including(tmp_path):
    """``&include`` resolved against the working directory, which made a
    report's meaning depend on how the process happened to be launched. Here a
    set of fragments moves as a unit."""
    (tmp_path / 'parts').mkdir()
    write(tmp_path, 'parts/inner.yaml', '- head: inner\n')
    write(tmp_path, 'parts/outer.yaml', '- _include_: inner.yaml\n')

    tree, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: parts/outer.yaml
    """)

    assert not diagnostics, diagnostics.report()
    assert str(tree[0].children[0].value) == 'inner'


def test_a_diagnostic_inside_a_fragment_names_the_fragment(tmp_path):
    write(tmp_path, 'broken.yaml', "- '2024': nope\n")
    _, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: broken.yaml
    """)

    report = diagnostics.report()
    assert 'broken.yaml' in report
    assert 'begins with a letter' in report


def test_an_all_digit_key_is_told_to_quote_itself_first(tmp_path):
    """A two-step diagnostic, each step clear.

    YAML types ``- 2024:`` as an *integer* key, so it never reaches the address
    rule that would have explained itself -- what comes back is "a key must be
    plain text", which does not say what to do. Quoting it gets the real
    message, that an address begins with a letter.
    """
    write(tmp_path, 'broken.yaml', '- 2024: nope\n')
    _, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: broken.yaml
    """)

    report = diagnostics.report()
    assert 'a key must be plain text' in report
    assert "Quote it if you meant the text '2024'" in report


# ---------------------------------------------------------------- cycles

def test_a_file_that_includes_itself_is_reported(tmp_path):
    write(tmp_path, 'loop.yaml', '- _include_: loop.yaml\n')
    _, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: loop.yaml
    """)

    assert 'includes itself' in diagnostics.report()


def test_mutual_recursion_is_reported(tmp_path):
    write(tmp_path, 'ping.yaml', '- _include_: pong.yaml\n')
    write(tmp_path, 'pong.yaml', '- _include_: ping.yaml\n')
    _, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: ping.yaml
    """)

    assert 'includes itself' in diagnostics.report()


def test_a_cycle_is_a_stack_not_a_history(tmp_path):
    """The distinction the text format got wrong.

    A file is a cycle only while it is still *open*. Keeping a set of every
    file ever seen -- which is what ``_visited`` did -- makes the second use of
    a shared fragment look like recursion, and refuses exactly the reuse
    includes exist for.
    """
    write(tmp_path, 'common.yaml', '- head: shared\n')
    write(tmp_path, 'one.yaml', '- _include_: common.yaml\n')
    write(tmp_path, 'two.yaml', '- _include_: common.yaml\n')

    tree, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: one.yaml
              - _include_: two.yaml
    """)

    assert not diagnostics, diagnostics.report()
    assert len(tree[0].children) == 2


def test_includes_may_not_nest_past_the_depth_cap(tmp_path):
    for level in range(MAX_INCLUDE_DEPTH + 2):
        write(tmp_path, f'level{level}.yaml', f'- _include_: level{level + 1}.yaml\n')

    _, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: level0.yaml
    """)

    assert f'more than {MAX_INCLUDE_DEPTH} deep' in diagnostics.report()


# ----------------------------------------------------------------- shape

def test_a_root_document_cannot_be_included_as_a_fragment(tmp_path):
    """Settings and ``_global_`` are root-only, and a fragment is a bare
    sequence with nowhere to put them -- so the shape says which is which."""
    write(tmp_path, 'whole.yaml', SETTINGS + '_content_:\n  - section:b:\n')
    _, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: whole.yaml
    """)

    report = diagnostics.report()
    assert 'sequence of entries' in report
    assert '_scriptum_' in report


@pytest.mark.parametrize('written', ['[a, b]', '{a: b}', "''"])
def test_an_include_takes_one_path_or_glob(tmp_path, written):
    _, diagnostics = read(tmp_path, f"""
        _content_:
          - section:a:
              - _include_: {written}
    """)

    assert '_include_' in diagnostics.report()


def test_an_included_entry_is_reached_by_walk(tmp_path):
    write(tmp_path, 'part.yaml', '- head: from the fragment\n')
    tree, diagnostics = read(tmp_path, """
        _content_:
          - section:a:
              - _include_: part.yaml
    """)

    assert not diagnostics, diagnostics.report()
    assert [e.address.puretag for e in walk(tree)] == ['section:a', 'head']
