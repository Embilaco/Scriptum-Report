"""Addresses: the short form an author writes, and its four internal slots.

The point of four *positional* slots is that position decides meaning and
content never has to. All-digit names stay legal, a child added on the Word
side later slots in without disturbing the id, and the template address is
recovered by dropping the last field -- which works only because the id is
always last and always an integer.
"""

from __future__ import annotations

import pytest

from Scriptum.rdf.loader import Address, Diagnostics, YamlSource
from Scriptum.rdf.loader import addresses


def parse(text):
    """Parse *text* as an address, returning (address, diagnostics)."""
    diagnostics = Diagnostics()
    source = YamlSource.from_text(b'k: v\n', 'doc.yaml', diagnostics)
    key_node = source.root.value[0][0]
    return addresses.parse(text, key_node, source, diagnostics), diagnostics


# --------------------------------------------------------------- the slots

@pytest.mark.parametrize('written, slots', [
    ('head', ('', 'head', '')),
    ('subsection:instruction', ('subsection', 'instruction', '')),
    ('table:default:description', ('table', 'default', 'description')),
])
def test_segments_fill_the_slots_left_to_right(written, slots):
    address, diagnostics = parse(written)

    assert not diagnostics, diagnostics.report()
    assert (address.namespace, address.name, address.child) == slots


def test_a_bare_name_leaves_the_namespace_empty():
    """Not ``head:head``.

    A tag written ``<head/>`` sets namespace and name to the same word, which
    duplicates the value and makes "is there a namespace?" unanswerable.
    Keeping the name in its own slot means the slots always mean the same
    thing; the tag's shape is reproduced in puretag and nowhere else.
    """
    address, _ = parse('head')

    assert address.namespace == ''
    assert address.name == 'head'
    assert address.canonical.startswith(':head:')


@pytest.mark.parametrize('written, canonical', [
    ('head', ':head::1'),
    ('subsection:instruction', 'subsection:instruction::1'),
    ('table:default:description', 'table:default:description:1'),
    ('TitleSlide', ':titleslide::1'),
])
def test_the_canonical_form_keeps_every_slot(written, canonical):
    address, _ = parse(written)
    assert address.numbered(1).canonical == canonical


def test_the_template_address_is_the_canonical_one_less_its_last_field():
    """The property the whole positional scheme is built to give."""
    address, _ = parse('subsection:instruction')
    numbered = address.numbered(7)

    assert numbered.canonical == 'subsection:instruction::7'
    assert numbered.canonical.rsplit(':', 1)[0] == numbered.template


@pytest.mark.parametrize('written, puretag', [
    ('head', 'head'),
    ('subsection:instruction', 'subsection:instruction'),
    ('table:default:description', 'table:default:description'),
])
def test_puretag_is_how_the_template_spells_the_tag(written, puretag):
    """What has to match a tag in the .docx or .pptx, so it keeps the short
    form: trailing empty slots dropped, a bare name written bare."""
    address, _ = parse(written)
    assert address.numbered(3).puretag == puretag


def test_an_address_is_lowercased_but_a_value_is_not():
    """Unchanged from the text format for addresses -- and now true of every
    key, which is what retires the bug where modifier names were *not*
    lowercased, so ``Description`` never bound to a ``description`` child."""
    address, diagnostics = parse('Report:Product_Name')

    assert not diagnostics
    assert address.puretag == 'report:product_name'


def test_an_all_digit_name_is_legal():
    """Position decides meaning, so no rule about what a *name* may contain is
    needed. A name that looks like a number is still a name."""
    address, diagnostics = parse('figure:2024')

    assert not diagnostics, diagnostics.report()
    assert address.name == '2024'


def test_an_address_cannot_begin_with_a_digit_even_though_a_name_can():
    """Two rules on the map look contradictory and are not.

    *Address grammar* says an address cannot start with a number; *Elements
    are sequences* says all-digit names stay legal. Both hold, of different
    segments -- and the dividing line is not taste, it is what a document
    template can hold. The tag scanner's pattern opens ``[a-z]+``, so
    ``<figure:2024/>`` is found and ``<2024/>`` is not (measured against
    ``getTag``). An address that cannot be written as a tag could never match
    anything.
    """
    address, diagnostics = parse('2024')

    assert address is None
    report = diagnostics.report()
    assert 'must begin with a letter' in report
    assert 'A later segment may be all digits' in report


# ---------------------------------------------------------- what is refused

def test_a_fourth_segment_is_refused_and_says_why():
    """The canonical form is internal; nobody writes an id."""
    address, diagnostics = parse('subsection:instruction::1')

    assert address is None
    report = diagnostics.report()
    assert 'at most 3' in report
    assert 'assigned by the loader' in report


def test_an_empty_segment_is_refused():
    address, diagnostics = parse('table::description')

    assert address is None
    assert 'empty segment' in diagnostics.report()


@pytest.mark.parametrize('written', [
    'has space', 'dotted.name', 'plus+name', 'equals=name', 'at@name',
    'semi;colon', 'Grüße',
])
def test_a_segment_takes_only_letters_digits_underscore_and_hyphen(written):
    address, diagnostics = parse(written)

    assert address is None
    assert 'not a valid segment' in diagnostics.report()


@pytest.mark.parametrize('written', ['2024', '1st:thing'])
def test_the_first_segment_cannot_start_with_a_digit(written):
    address, diagnostics = parse(written)

    assert address is None
    assert 'must begin with a letter' in diagnostics.report()


@pytest.mark.parametrize('written', ['figure:_x', 'figure:-x', 'figure:x:-y'])
def test_no_segment_opens_with_an_underscore_or_a_hyphen(written):
    address, diagnostics = parse(written)

    assert address is None
    assert 'not opening with' in diagnostics.report()


@pytest.mark.parametrize('written', ['_scriptum_', '_include_', '_anything'])
def test_a_reserved_looking_key_is_refused_as_an_address(written):
    """The underscore convention is what makes reserved keys collision-proof:
    no author name can ever begin with one, so ``_include_`` can never be
    something an author meant as a target."""
    address, diagnostics = parse(written)

    assert address is None
    assert 'reserved' in diagnostics.report()


@pytest.mark.parametrize('written', ['', '   '])
def test_an_empty_address_is_refused(written):
    address, diagnostics = parse(written)

    assert address is None
    assert 'must be text' in diagnostics.report()


# ------------------------------------------------------------------ values

def test_numbered_does_not_mutate_the_original():
    address, _ = parse('subsection:instruction')

    first = address.numbered(1)
    second = address.numbered(2)

    assert address.id is None
    assert (first.id, second.id) == (1, 2)


def test_addresses_compare_and_hash_on_the_canonical_form():
    left = Address('subsection', 'instruction', '', 1)
    right = Address('subsection', 'instruction', '', 1)
    other = Address('subsection', 'instruction', '', 2)

    assert left == right and hash(left) == hash(right)
    assert left != other
    assert len({left, right, other}) == 2


def test_a_marker_is_recognised_by_its_namespace():
    address, _ = parse('marker:content')
    assert address.is_marker

    address, _ = parse('image:generic')
    assert not address.is_marker
