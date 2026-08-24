"""Guard the tag grammar in ``Scriptum/tag/tag.py``.

Why this file exists
--------------------
The branch meant to reject a tag with too many ``:``-separated segments was
written as a comparison (``self.tagtype == 'invalid:ns_name'``) rather than an
assignment, so it did nothing at all. A four-segment tag was accepted as a
valid ``simple`` tag with ``ns``, ``name`` and ``child`` all left as ``None``,
and then quietly matched nothing in the document.

Nothing detected that: an over-long tag produces no error and no output, which
looks exactly like a tag the author simply never filled. The only way it
surfaces is a missing paragraph in a finished report.

It matters more than it used to. The address form the YAML document format
canonicalises to has **four** positional slots (``namespace:name:child:id``),
and the whole point of keeping the id in a tag *argument* -- ``<head id=2/>``
-- rather than in the tag name is that the canonical form never has to be
written into a document. If a four-segment tag were silently accepted, that
design would fail in precisely the way it exists to prevent.

``tag`` is a leaf package that imports nothing, so these tests need no fixture,
no data files and no parser state -- the same reason ``test_layering.py`` in
this tree carries no ``_setup_*`` helper.
"""

from __future__ import annotations

import pytest

from Scriptum.tag.tag import Tag, createTag, getTag


# --------------------------------------------------------------- the fix

@pytest.mark.parametrize('tagtext', [
    'a:b:c:d',
    'a:b:c:d:e',
    'subsection:instruction::2',      # the canonical four-slot form
    'table:default:description:1',
])
def test_more_than_three_segments_is_rejected(tagtext):
    """The branch is an assignment, not a comparison.

    Reverting it makes every assertion below fail: the tag comes back as a
    valid ``simple`` tag carrying a puretag it cannot match with.
    """
    tag = Tag(f'<{tagtext}/>')

    assert 'invalid' in tag.tagtype
    assert tag.tagtype == 'invalid:ns_name'
    # an invalid tag must not keep an address, or it can still be looked up
    assert tag.puretag == ''
    assert tag.args == []


def test_rejected_over_long_tag_is_still_found_by_the_scanner():
    """Rejected, not invisible.

    ``getTag`` must still return it, so the caller can report it. A tag that
    vanished from the scan would be indistinguishable from one that was never
    written.
    """
    tags = getTag('text before <a:b:c:d/> text after')

    assert len(tags) == 1
    assert tags[0].tagtype == 'invalid:ns_name'


# ------------------------------------------------- the grammar it guards

def test_one_segment_sets_namespace_and_name_to_the_same_word():
    tag = createTag('head')

    assert tag.tagtype == 'simple'
    assert (tag.ns, tag.name, tag.child) == ('head', 'head', None)
    assert tag.puretag == 'head'


def test_two_segments_split_into_namespace_and_name():
    tag = createTag('image:generic')

    assert (tag.ns, tag.name, tag.child) == ('image', 'generic', None)


def test_three_segments_split_into_namespace_name_and_child():
    tag = createTag('table:default:description')

    assert (tag.ns, tag.name, tag.child) == ('table', 'default', 'description')


def test_a_tag_is_lowercased_but_only_the_address():
    tag = Tag('<Image:Generic Width=4cm/>')

    assert tag.puretag == 'image:generic'
    assert tag.args == {'width': '4cm'}


# --------------------------------------------- the id-as-argument design

def test_the_instance_id_rides_as_an_argument():
    """``<head id=2/>`` scans and parses with no change to the grammar.

    This is what lets a cloned element keep its authored name, which is what
    keeps ``global`` -- which matches on ``puretag`` alone -- reaching every
    clone instead of skipping all of them.
    """
    tag = createTag('head id=2')

    assert tag.tagtype == 'simple'
    assert tag.puretag == 'head'
    assert tag.args == {'id': '2'}


def test_the_id_argument_survives_a_namespaced_name():
    tag = Tag('<subsection:instruction id=2>')

    assert tag.tagtype == 'open'
    assert tag.puretag == 'subsection:instruction'
    assert tag.args == {'id': '2'}


def test_a_colon_in_an_argument_is_rejected():
    """Which is why the id is an integer and never an address."""
    tag = createTag('head id=a:b')

    assert tag.tagtype == 'invalid:not_allowed'
    assert tag.puretag == ''


def test_an_argument_with_two_equals_signs_is_rejected():
    tag = createTag('head id=2=3')

    assert tag.tagtype == 'invalid:args_wrong'
    assert tag.puretag == ''


# ------------------------------------------------------- tag type basics

@pytest.mark.parametrize('rawtag, expected', [
    ('<head>', 'open'),
    ('</head>', 'close'),
    ('<head/>', 'simple'),
    ('</head/>', 'invalid'),
    ('< >', 'invalid:empty'),
])
def test_tag_type_is_decided_by_the_slashes(rawtag, expected):
    assert Tag(rawtag).tagtype == expected


def test_an_argument_without_a_value_is_kept_as_none():
    """``breakbefore`` and ``template`` are written bare."""
    tag = createTag('subsection:instruction breakbefore')

    assert tag.args == {'breakbefore': None}


# ------------------------------------------------- instances and addresses

def test_a_tag_with_no_id_is_instance_one():
    """What lets a pristine template be read without editing it: every block
    in one is the first of its kind."""
    assert createTag('head').instance == 1
    assert createTag('subsection:instruction template').instance == 1


def test_the_id_argument_is_the_instance():
    assert createTag('head id=2').instance == 2
    assert createTag('image:generic id=7').instance == 7


def test_a_mistyped_id_reads_as_one_rather_than_raising():
    """This is a document somebody typed into Word. A wrong number should not
    stop the run before the diagnostics that would explain it."""
    assert createTag('head id=two').instance == 1
    assert createTag('head id').instance == 1


@pytest.mark.parametrize('written, canonical', [
    ('head', ':head::1'),
    ('head id=2', ':head::2'),
    ('subsection:instruction', 'subsection:instruction::1'),
    ('table:default:description', 'table:default:description:1'),
    ('subsection:instruction template breakbefore', 'subsection:instruction::1'),
])
def test_the_canonical_address_of_a_tag(written, canonical):
    assert createTag(written).canonical == canonical


def test_a_single_segment_tag_leaves_the_namespace_slot_empty():
    """``<head/>`` sets namespace and name to the same word, which duplicates
    the value and makes "is there a namespace?" unanswerable. The slots keep
    them apart, so it is ``:head::1`` and never ``head:head::1``."""
    tag = createTag('head')

    assert (tag.ns, tag.name) == ('head', 'head')
    assert tag.canonical.startswith(':head:')


def test_setting_an_instance_leaves_the_puretag_alone():
    """The whole point of the id being an argument.

    ``global`` matches on ``puretag``, so renaming a clone made every clone
    invisible to it. An argument leaves the name where the template wrote it.
    """
    tag = createTag('subsection:instruction template breakbefore')

    tag.setInstance(3)

    assert tag.puretag == 'subsection:instruction'
    assert tag.canonical == 'subsection:instruction::3'
    assert 'id=3' in tag.tagtext
    assert 'breakbefore' in tag.tagtext, 'other arguments survive'


def test_numbering_makes_an_instance_which_is_never_a_blueprint():
    """``template`` marks a blueprint, and a numbered tag is a clone of one.

    The argument is dropped with the numbering, so a clone cannot be taken
    for a blueprint by anything that decides by that argument -- and cannot
    be pruned with the blueprints at the end, content and all.
    """
    tag = createTag('subsection:instruction template breakbefore')

    tag.setInstance(2)

    assert 'template' not in tag.args
    assert 'template' not in tag.tagtext.split()
    assert 'breakbefore' in tag.args, 'only template goes'
    assert tag.withInstance(3).split() == \
        ['subsection:instruction', 'breakbefore', 'id=3']


def test_a_numbered_tag_rescans_to_the_same_address():
    """The rewritten text goes back into the document and is scanned again, so
    the round trip has to hold."""
    tag = createTag('subsection:instruction template')
    tag.setInstance(4)

    rescanned = getTag(f'<{tag.tagtext}>')[0]

    assert rescanned.canonical == 'subsection:instruction::4'
    assert rescanned.instance == 4


def test_renumbering_replaces_the_id_rather_than_appending_one():
    tag = createTag('head id=2')
    tag.setInstance(5)

    assert tag.tagtext.count('id=') == 1
    assert tag.canonical == ':head::5'
