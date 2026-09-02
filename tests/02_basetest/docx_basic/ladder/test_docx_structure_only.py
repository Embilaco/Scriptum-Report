"""``ManagedDocx.structure()``: the ladder expanded, nothing filled.

A run that answers *what did it think I meant?* — every instance the report
document asks for, created and placed, with each clone carrying the instance
number the document addresses it by, and then nothing else touched. No value
written, no tag cleaned, no blueprint pruned, no document properties stamped.
The file is a diagnostic and is not a report.

Why it needs a test of its own
------------------------------
Everything it produces is **invisible to a case reference**. The value here
is the tags: ``<subsection:alpha id=2>`` is what a reader is looking for, and
a finished document has no tags left in it at all, so no ``expected/*.json``
can see any of this. That puts it in the same class as the page break of
``test_docx_breakbefore.py`` — a property the differential comparison is
structurally unable to notice, which is exactly the kind that rots quietly.

The ladder case is the fixture because it has the most to show: five rungs,
two branches, a marker at every level, a blueprint used in one clone of its
parent and not in another, and a block named where the template does not hold
it. A structure document of it shows all of that at once.

Word only: ``ManagedPptx`` has no counterpart, since a slide is created
inside the fill pass, so switching the fill off there gives an empty deck.
"""

from pathlib import Path
import re
import shutil
import sys

import pytest

docx = pytest.importorskip('docx')

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = THIS_DIR.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT))

from _setup_docx_basic import *          # noqa: F401,F403  (brings reset_state, os)

TEMPLATE = 'template.docx'
DOCUMENT = 'ladder.yaml'

#: An opening block tag with what it says about itself: the instance number a
#: clone was numbered with, or the ``template`` argument a blueprint kept.
BLOCK = re.compile(r'<((?:sub\w*)?section:[\w-]+)(?:\s+(template|id=\d+))?\s*>')


def build(tmp_path):
    """``ladder.yaml`` against ``template.docx``, structure only."""
    import Scriptum

    shutil.copy(THIS_DIR / TEMPLATE, tmp_path)
    shutil.copy(THIS_DIR / DOCUMENT, tmp_path)

    os.chdir(tmp_path)
    rdf = Scriptum.ReportDataFile(DOCUMENT)
    managed = Scriptum.ManagedDocx(TEMPLATE, rdf)
    managed.structure(rdf)
    managed.save('structure.docx')
    return tmp_path / 'structure.docx'


def blocks(path, wanted=None):
    """``(name, 'id=N' | 'template' | None)`` for every opening block tag."""
    found = []
    for paragraph in docx.Document(path).paragraphs:
        found += BLOCK.findall(paragraph.text)
    return [(name, how or None) for name, how in found
            if wanted is None or name == wanted]


def texts(path):
    return [p.text.strip() for p in docx.Document(path).paragraphs if p.text.strip()]


# ------------------------------------------------- the instances, numbered

def test_every_instance_carries_the_number_it_is_addressed_by(tmp_path):
    """The document's own reading of the ladder, in document order.

    ``ladder.yaml`` asks for alpha twice, ``one`` twice inside the first
    alpha, ``level3-1`` twice inside the first ``one``, and the deep rungs
    once each inside the second ``level3-1``; then beta once with its own
    branch. This is that, written out — and it is the thing hardest to
    picture from the document alone.
    """
    numbered = [(name, how) for name, how in blocks(build(tmp_path))
                if how and how.startswith('id=')]

    assert numbered == [
        ('subsection:alpha', 'id=1'),
        ('subsubsection:one', 'id=1'),
        ('sub3section:level3-1', 'id=1'),
        ('sub3section:level3-1', 'id=2'),
        ('sub4section:level4-1', 'id=1'),
        ('sub5section:level5', 'id=1'),
        ('sub4section:level4-2', 'id=1'),
        ('subsubsection:one', 'id=2'),
        ('subsection:alpha', 'id=2'),
        ('subsection:beta', 'id=1'),
        ('subsubsection:two', 'id=1'),
        ('sub3section:level3-2', 'id=1'),
    ]


def test_the_blueprints_are_still_standing(tmp_path):
    """Nothing is pruned, so every blueprint is still there and still says
    ``template`` — which is how an *unused* one is visible as unused, and
    where: the copy of ``level4-1`` inside ``level3-1 id=1`` never got an
    instance, while the copy inside ``id=2`` did."""
    document = build(tmp_path)

    assert ('subsection:alpha', 'template') in blocks(document)
    assert ('sub5section:level5', 'template') in blocks(document)

    level4 = blocks(document, 'sub4section:level4-1')
    assert ('sub4section:level4-1', 'id=1') in level4, 'the one that was used'
    assert level4.count(('sub4section:level4-1', 'template')) > 1, \
        'and the copies that were not, one per clone that did not use it'


def test_nothing_is_filled_and_no_tag_is_cleaned(tmp_path):
    """Every fill tag is still readable as the address it is, and none of the
    document's values reached the page."""
    said = texts(build(tmp_path))

    assert any('<text:description/>' in line for line in said), \
        'the fill tags are what makes the file worth reading'
    assert not any('the first alpha' in line for line in said), \
        'and no value was written'
    assert '<section:template>' in said, 'the template section stays too'


def test_a_marker_add_is_already_in_its_place(tmp_path):
    """Adds are part of the structure stage, so a marker entry is placed --
    in front of the ``<marker:content/>`` it belongs to -- and numbered,
    without being filled."""
    said = texts(build(tmp_path))
    placed = [i for i, line in enumerate(said) if '<text:plain id=1/>' in line]

    assert placed, said[:20]
    for i in placed:
        assert '<marker:content/>' in said[i + 1], \
            f'an add stands in front of its marker: {said[i:i + 2]}'
    assert not any('added at the alpha one marker' in line for line in said), \
        'placed, not filled'


def test_an_addressing_mistake_is_reported_here_too(tmp_path, capsys):
    """The structure run is the whole add-and-copy stage, so it is also where
    a misplaced address is caught -- which is most of the reason to reach for
    it. ``ladder.yaml`` names ``sub3section:level3-1`` under
    ``subsection:beta``, where the template holds no such block."""
    build(tmp_path)
    out = capsys.readouterr().out

    assert 'Nothing to apply at' in out
    assert "'subsubsection:two' holds no 'sub3section:level3-1'" in out
    assert 'SKIP: fill the content' in out, 'and nothing was filled'
