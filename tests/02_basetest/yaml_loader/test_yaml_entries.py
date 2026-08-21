"""Walking ``_content_``: entry shape, the ladder, and instance numbering.

The three things worth reading these for:

* what an entry *is* comes from the kind of its value, with no keyword;
* depth in the document is depth in the namespace ladder, counted in
  containers, which is what makes gaps and mixing-roots unspellable;
* a repeated address is a second instance, because re-opening a root is not
  expressible under nesting and is not needed.
"""

from __future__ import annotations

import textwrap

import pytest

from Scriptum.rdf.loader import (Container, Diagnostics, Fill, Marker,
                                 YamlSource, read_content, read_root, walk)


def read(content, documenttype='docx'):
    """Wrap *content* as the ``_content_`` of a document and walk it."""
    body = textwrap.indent(textwrap.dedent(content).strip('\n'), '  ')
    document = (f'_scriptum_:\n  version: 4\n  documenttype: {documenttype}\n'
                f'_content_:\n{body}\n')

    diagnostics = Diagnostics()
    source = YamlSource.from_text(document.encode('utf-8'), 'doc.yaml',
                                  diagnostics)
    header = read_root(source, diagnostics)
    tree = read_content(header.content_node, source, header.settings,
                        diagnostics)
    return tree, diagnostics


def canonicals(entries):
    return [e.address.canonical for e in entries]


# ------------------------------------------------- the value's kind decides

def test_a_sequence_value_is_a_container_and_a_scalar_is_a_fill():
    tree, diagnostics = read("""
        - section:title:
            - head: Serving
    """)

    assert not diagnostics, diagnostics.report()
    section, = tree
    assert isinstance(section, Container)
    fill, = section.children
    assert isinstance(fill, Fill)


def test_a_mapping_value_is_a_fill_with_an_explicit_source():
    tree, diagnostics = read("""
        - section:title:
            - image:main: {file: pudding.jpg, width: 4cm}
    """)

    assert not diagnostics, diagnostics.report()
    fill, = tree[0].children
    assert isinstance(fill, Fill)


def test_a_null_value_is_a_container_with_an_empty_body():
    """``- BackCover:`` is a slide that exists only to be created; the corpus
    has one. Distinct from ``''``, which is a fill holding the empty string."""
    tree, diagnostics = read('- BackCover:\n', documenttype='pptx')

    assert not diagnostics, diagnostics.report()
    slide, = tree
    assert isinstance(slide, Container)
    assert slide.children == []


def test_an_empty_string_value_is_a_fill_not_a_container():
    tree, diagnostics = read("""
        - section:title:
            - rf2: ''
    """)

    assert not diagnostics, diagnostics.report()
    assert isinstance(tree[0].children[0], Fill)


# ------------------------------------------------------------ entry shape

def test_an_entry_must_be_a_mapping():
    _, diagnostics = read('- just a scalar\n')

    assert 'an entry is a mapping of one address' in diagnostics.report()


def test_an_entry_has_exactly_one_key():
    _, diagnostics = read("""
        - section:title:
            - head: Serving
          section:other:
            - head: Other
    """)

    report = diagnostics.report()
    assert 'exactly one key' in report
    assert 'needs its own "-"' in report


def test_an_empty_entry_is_reported():
    _, diagnostics = read('- {}\n')

    assert 'needs an address' in diagnostics.report()


# ---------------------------------------------------------------- the ladder

def test_the_docx_ladder_is_mandatory_at_every_level():
    tree, diagnostics = read("""
        - section:a:
            - subsection:b:
                - subsubsection:c:
                    - head: deep
    """)

    assert not diagnostics, diagnostics.report()
    assert canonicals(tree) == ['section:a::1']
    assert canonicals(tree[0].children) == ['subsection:b::1']
    assert canonicals(tree[0].children[0].children) == ['subsubsection:c::1']


def test_a_container_at_the_wrong_depth_names_the_ladder():
    _, diagnostics = read("""
        - section:a:
            - subsubsection:c:
                - head: x
    """)

    report = diagnostics.report()
    assert "namespace must be 'subsection'" in report
    assert 'section > subsection > subsubsection' in report


def test_a_gap_in_the_ladder_has_no_spelling():
    """Not a rule that is checked -- a rule that cannot be written.

    You cannot nest at depth 2 without writing the depth-1 parent, so
    "skipping a level" is not expressible. What is left is the wrong namespace
    at a depth, which is the test above.
    """
    _, diagnostics = read('- subsection:b:\n    - head: x\n')

    assert "namespace must be 'section'" in diagnostics.report()


def test_nothing_nests_past_the_bottom_of_the_ladder():
    _, diagnostics = read("""
        - section:a:
            - subsection:b:
                - subsubsection:c:
                    - sub3section:d:
                        - sub4section:e:
                            - sub5section:f:
                                - sub5section:g:
                                    - head: x
    """)

    assert 'nothing nests this deep' in diagnostics.report()


def test_a_null_container_at_the_wrong_depth_is_told_about_the_empty_string():
    """``- head:`` inside a section is an empty container, which is almost
    never what the author meant. The diagnostic says what they probably want."""
    _, diagnostics = read("""
        - section:a:
            - head:
    """)

    report = diagnostics.report()
    assert "write '' instead" in report


def test_pptx_addresses_a_slide_by_its_layout_name():
    """PowerPoint's ladder is not mandatory, so a bare name is a container."""
    tree, diagnostics = read("""
        - TitleSlide:
            - title: Test report
        - slide:Material:
            - title: Test C report
    """, documenttype='pptx')

    assert not diagnostics, diagnostics.report()
    assert canonicals(tree) == [':titleslide::1', 'slide:material::1']


def test_pptx_has_only_one_level():
    _, diagnostics = read("""
        - TitleSlide:
            - subsection:b:
                - head: x
    """, documenttype='pptx')

    assert 'nothing nests this deep' in diagnostics.report()


def test_a_wrong_namespace_is_still_wrong_where_the_ladder_is_optional():
    _, diagnostics = read('- image:generic:\n    - head: x\n',
                          documenttype='pptx')

    assert "namespace must be 'slide'" in diagnostics.report()


def test_a_fill_needs_a_container_around_it():
    """The text format's "Using (=) without a section root" rule, kept: a
    value belongs to an element, and _content_ holds the elements."""
    _, diagnostics = read('- head: Serving\n')

    report = diagnostics.report()
    assert 'needs a container around it' in report


def test_a_fill_is_not_a_level_of_the_ladder():
    """Fills and containers sit side by side in one body; only containers
    count toward depth. ``section:b`` in rdf_repeatSection.rdf does exactly
    this -- a head, then a subsection."""
    tree, diagnostics = read("""
        - section:b:
            - head: S b
            - subsection:instruction:
                - head: Temperatures
    """)

    assert not diagnostics, diagnostics.report()
    head, subsection = tree[0].children
    assert isinstance(head, Fill) and isinstance(subsection, Container)


# ------------------------------------------------------------- numbering

def test_a_repeated_address_is_a_second_instance():
    """The whole replacement for _cNNN renaming, and for re-opening a root."""
    tree, diagnostics = read("""
        - section:instruction_bc:
            - subsection:instruction:
                - head: Instruction 1
            - subsection:instruction:
                - head: Serving
    """)

    assert not diagnostics, diagnostics.report()
    assert canonicals(tree[0].children) == ['subsection:instruction::1',
                                            'subsection:instruction::2']


def test_sibling_counters_do_not_interfere():
    """Numbering is scoped to the parent path, as checkPath already scopes it:
    section:a and section:c each count their own subsection:b."""
    tree, diagnostics = read("""
        - section:a:
            - subsection:b:
                - head: one
            - subsection:b:
                - head: two
        - section:c:
            - subsection:b:
                - head: three
    """)

    assert not diagnostics, diagnostics.report()
    assert canonicals(tree[0].children) == ['subsection:b::1', 'subsection:b::2']
    assert canonicals(tree[1].children) == ['subsection:b::1']


def test_a_different_address_starts_its_own_count():
    tree, diagnostics = read("""
        - section:a:
            - subsection:b:
                - head: x
            - subsection:c:
                - head: y
    """)

    assert not diagnostics, diagnostics.report()
    assert canonicals(tree[0].children) == ['subsection:b::1', 'subsection:c::1']


def test_fills_are_numbered_too():
    """A repeated target is a second tag to fill, exactly as a repeated
    container is a second block -- which is what checkPath does today, keyed
    on the path including the target."""
    tree, diagnostics = read("""
        - section:a:
            - head: first
            - head: second
    """)

    assert not diagnostics, diagnostics.report()
    assert canonicals(tree[0].children) == [':head::1', ':head::2']


def test_a_top_level_repeat_is_two_containers():
    """rdf_repeatSection.rdf opens section:a three times to add children in
    three passes. Under nesting that is three sections, so converting it line
    by line would be wrong -- the children belong in one entry."""
    tree, diagnostics = read("""
        - section:a:
            - head: one
        - section:a:
            - head: two
    """)

    assert not diagnostics, diagnostics.report()
    assert canonicals(tree) == ['section:a::1', 'section:a::2']


def test_an_entry_carries_the_path_a_task_will_need():
    tree, _ = read("""
        - section:a:
            - subsection:b:
                - head: x
    """)

    head = tree[0].children[0].children[0]
    assert head.canonical_path == ('section:a::1', 'subsection:b::1')


# --------------------------------------------------------------- markers

def test_a_marker_holds_the_things_to_add_there():
    tree, diagnostics = read("""
        - section:a:
            - subsection:b:
                - marker:content:
                    - image:generic: {file: one.png}
                    - image:generic: {file: two.png}
    """)

    assert not diagnostics, diagnostics.report()
    marker, = tree[0].children[0].children
    assert isinstance(marker, Marker)
    assert all(isinstance(child, Fill) for child in marker.children)
    assert [child.marker for child in marker.children] == \
        ['marker:content', 'marker:content']


def test_a_marker_takes_no_id():
    """It names a position in the template, not an instance in the output, so
    two entries naming it mean the same place -- which is what the corpus does
    in word_tables.rdf, twice in one section with a fill between."""
    tree, diagnostics = read("""
        - section:a:
            - marker:content:
                - image:generic: {file: one.png}
            - table:orange: {file: t.csv}
            - marker:content:
                - image:generic: {file: two.png}
    """)

    assert not diagnostics, diagnostics.report()
    first, _, second = tree[0].children
    assert first.address.id is None and second.address.id is None


def test_a_marker_does_not_scope_numbering():
    """Adds count against the enclosing container, as checkPath does today --
    markers were never part of a path. So the second marker's image:generic
    continues at 2 rather than restarting."""
    tree, diagnostics = read("""
        - section:a:
            - marker:content:
                - image:generic: {file: one.png}
            - marker:other:
                - image:generic: {file: two.png}
    """)

    assert not diagnostics, diagnostics.report()
    first, second = tree[0].children
    assert first.children[0].address.canonical == 'image:generic::1'
    assert second.children[0].address.canonical == 'image:generic::2'


def test_a_marker_needs_a_container_around_it():
    _, diagnostics = read("""
        - marker:content:
            - image:generic: {file: one.png}
    """)

    assert 'needs a container around it' in diagnostics.report()


def test_a_marker_cannot_be_nested_in_a_marker():
    _, diagnostics = read("""
        - section:a:
            - marker:content:
                - marker:other:
                    - image:generic: {file: one.png}
    """)

    assert 'names no place at all' in diagnostics.report()


def test_a_marker_with_a_value_instead_of_a_list_is_reported():
    _, diagnostics = read("""
        - section:a:
            - marker:content: something
    """)

    assert 'not a value of its own' in diagnostics.report()


def test_a_container_inside_a_marker_is_reported():
    """A marker adds elements, not levels. Stated as a restriction rather
    than left undefined -- the engine has no meaning for it today."""
    _, diagnostics = read("""
        - section:a:
            - marker:content:
                - subsection:b:
                    - head: x
    """)

    report = diagnostics.report()
    assert 'adds elements' in report
    assert 'rather than levels' in report


def test_a_fill_outside_a_marker_is_not_an_add():
    tree, _ = read("""
        - section:a:
            - head: Serving
    """)

    assert tree[0].children[0].marker is None


# -------------------------------------------------------------- traversal

def test_walk_yields_every_entry_in_document_order():
    """Order is significant: both back ends iterate the task list in order."""
    tree, diagnostics = read("""
        - section:a:
            - head: one
            - subsection:b:
                - head: two
                - marker:content:
                    - image:generic: {file: x.png}
        - section:c:
            - head: three
    """)

    assert not diagnostics, diagnostics.report()
    seen = [e.address.puretag for e in walk(tree)]
    assert seen == ['section:a', 'head', 'subsection:b', 'head',
                    'marker:content', 'image:generic', 'section:c', 'head']


def test_an_unknown_documenttype_walks_to_nothing_rather_than_guessing():
    """Already reported by the settings schema; picking a ladder anyway would
    bury that one diagnostic under a page of consequences."""
    diagnostics = Diagnostics()
    document = ('_scriptum_:\n  version: 4\n  documenttype: pdf\n'
                '_content_:\n  - section:a:\n      - head: x\n')
    source = YamlSource.from_text(document.encode('utf-8'), 'doc.yaml',
                                  diagnostics)
    header = read_root(source, diagnostics)
    before = len(diagnostics)

    assert read_content(header.content_node, source, header.settings,
                        diagnostics) == []
    assert len(diagnostics) == before
