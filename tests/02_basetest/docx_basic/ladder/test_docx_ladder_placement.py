"""The ladder case: which block a repeat lands behind, and where the gap is.

``test_docx_clone_order.py`` in the ``text`` case beside this one pins *which*
block a clone follows and what is left of a blueprint afterwards. This case
pins *where the gap behind an instance is* -- the half no template without
prose between its blocks can show, because the two candidate landing places
coincide there -- and, since the template goes the whole way down, that the
rule holds at every rung.

The rule
--------
A further instance of a block goes **immediately behind the instance before
it**. Everything the template holds between two blocks -- a lead-in line, a
heading, a whole unused blueprint -- is fixed text belonging *after* all the
instances, and a repeat may not be threaded through it.

What used to happen instead: the clone went before the next *unclaimed
sibling block* (``subAnchors[0]``), which is on the far side of that prose.
Both halves of the damage were visible in the ``text`` case at the time:
with ``subsection:secondsuba`` used twice, *Between the subsections* came out
between instance 1 and instance 2 -- and a repeat of the **last** blueprint of
a section had no unclaimed sibling left at all, fell through to the section's
closing paragraph, and landed past the section's own trailing prose. Fixed by
``StructuredElement.followInstance``.

A block is addressed where the template holds it
-----------------------------------------------
An address must exist in the template **at that place**. ``template.docx``
holds ``sub3section:level3-1`` under ``subsection:alpha``; naming it under
``subsection:beta`` reaches nothing -- the entry and everything under it are
dropped, with warnings. ``ladder.yaml`` does exactly that on purpose and
``test_a_block_named_where_the_template_does_not_hold_it_is_dropped`` pins the
whole set of warnings, so the day the diagnosis changes it is a decision and
not a surprise. The one way to place content a section does not already
contain is a **marker**, whose entries are looked up by name across the whole
document -- see *Content* in ``docs/rdf.md``.

Repeating requires the flag
---------------------------
A block can be repeated **only** if its tag carries the ``template`` argument
(narrowed 2026-08-30). Without it a block is filled where it stands and a
second instance of it is refused, by one message naming the block and the
argument to add. That is the one shape this template cannot express -- every
block in it is flagged -- so the last three tests build their own, as
``test_docx_clone_order.py`` does for its own odd shape.

The fixture
-----------
``template.docx`` is a clean ladder, every rung of it::

    section:main
        subsection:alpha
            subsubsection:one
                sub3section:level3-1
                    sub4section:level4-1
                        sub5section:level5
                    sub4section:level4-2
        subsection:beta
            subsubsection:two
                sub3section:level3-2

Every block is flagged ``template``, carries a ``<text:description/>`` and a
``<marker:content/>``, and has an ordinary paragraph in **every** gap: before
a block, between two blocks, after a block, and on both sides of each nested
child. ``ladder.yaml`` is the canonical document -- a repeat at three depths,
the deep rungs walked once, and the misplaced ``level3-1`` above; the focused
tests write their own small documents against the same template.

``expected/ladder.json`` is compared **without** :func:`normalise`. This case
has no dates in it, and its block names carry digits that must not be
collapsed: under the usual normalising, ``level3-1``, ``level3-2``,
``level4-1`` and ``level4-2`` all read ``level#-#`` and thirteen lines fall
together into seven, so a clone landing in the wrong level's slot would
compare equal. See ``common_case.reference``.
"""

from pathlib import Path
import shutil
import sys

import pytest

docx = pytest.importorskip('docx')

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = THIS_DIR.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT))

from _setup_docx_basic import *          # noqa: F401,F403  (brings reset_state, os)
from common_case import said, reference, difference, portable, fold

TEMPLATE = 'template.docx'
DOCUMENT = 'ladder.yaml'
REFERENCE = THIS_DIR / 'expected' / 'ladder.json'

HEADER = ('_scriptum_:\n'
          '  version: 4\n'
          '  documenttype: docx\n'
          '  datadir: .\n'
          '_content_:\n')

#: The tag each ladder level writes for its heading. The three deepest rungs
#: all write ``<subitem/>`` in this template.
HEAD_TAG = {'subsection': 'head', 'subsubsection': 'item', 'sub3section': 'subitem',
            'sub4section': 'subitem', 'sub5section': 'subitem'}

#: What the section itself says around its children, when its own marker is
#: not fed.
MAIN_OPEN = ['MAIN SECTION', 'main: before alpha']
MAIN_MIDDLE = ['main: between alpha and beta']
MAIN_CLOSE = ['main: after beta', 'main: marker', 'main: end']

#: What one instance of each block says when its head and its description are
#: filled, its marker is not fed and none of its children are used: the
#: template's own prose around the fills, which is exactly what a misplaced
#: clone disturbs. ``{}`` takes the head, which the helpers below use as the
#: description too.
QUIET = {
    'alpha': ['ALPHA {}', 'alpha: {}', 'alpha: marker',
              'alpha: before one', 'alpha: after one', 'alpha: end'],
    'one': ['ONE {}', 'one: {}', 'one: marker',
            'one: before level3-1', 'one: after level3-1', 'one: end'],
    'level3-1': ['LEVEL3-1 {}', 'Level3-1: {}',
                 'One: before level4-1', 'One: after Level4-1',
                 'Level3-1: marker',
                 'One: before level4-2', 'One: after Level4-2',
                 'Level3-1: end'],
    'level4-1': ['LEVEL4-1 {}', 'Level4-1: {}', 'Level4-1: marker',
                 'One: before level5', 'One: after Level5', 'Level4-1: end'],
    'level5': ['LEVEL5 {}', 'Level5: {}', 'Level5: marker', 'Level5: end'],
    'level4-2': ['LEVEL4-2 {}', 'Level4-2: {}', 'Level4-2: marker',
                 'Level4-2: end'],
    'beta': ['BETA {}', 'beta: {}', 'beta: marker', 'beta: end'],
    'two': ['TWO {}', 'two: {}', 'two: marker',
            'two: before level3-2', 'two: after level3-2', 'two: end'],
    'level3-2': ['LEVEL3-2 {}', 'Level3-2: {}', 'Level3-2: marker',
                 'Level3-2: end'],
}


def says(name, head):
    """What one quiet instance of *name* says, head and description *head*."""
    return [line.format(head) for line in QUIET[name]]


def entries(name, *heads, level='subsection', indent=6):
    """One document entry per head: *name* with that head and description."""
    pad = ' ' * indent
    return ''.join(f'{pad}- {level}:{name}:\n'
                   f'{pad}    - {HEAD_TAG[level]}: {head}\n'
                   f'{pad}    - text:description: {head}\n'
                   for head in heads)


def generate(tmp_path, body=None, template=TEMPLATE, document=None):
    """Build a document and return its non-empty paragraphs, stripped.

    *body* is the content of ``section:main``; pass *document* instead to run
    a ``.yaml`` shipped beside this file. *template* is a name to copy from
    the case directory, or a ``docx.Document`` built in the test. The finished
    file is left at ``tmp_path/'out.docx'`` for a caller that wants more than
    the text.
    """
    import Scriptum

    if isinstance(template, str):
        shutil.copy(THIS_DIR / template, tmp_path)
    else:
        template.save(tmp_path / 'built.docx')
        template = 'built.docx'
    # nothing here fills from a file; the directory only has to exist
    (tmp_path / 'data').mkdir(exist_ok=True)

    if document:
        shutil.copy(THIS_DIR / document, tmp_path)
    else:
        document = 'case.yaml'
        (tmp_path / document).write_text(
            HEADER + '  - section:main:\n' + body, encoding='utf-8')

    os.chdir(tmp_path)
    rdf = Scriptum.ReportDataFile(document)
    assert not rdf.errors, rdf.errors
    managed = Scriptum.ManagedDocx(template, rdf)
    managed.typesetting(rdf)
    managed.save('out.docx')

    return [p.text.strip() for p in docx.Document('out.docx').paragraphs
            if p.text.strip()]


# --------------------------------------------------- the canonical document

def test_the_document_says_what_the_reference_says(tmp_path):
    """``ladder.yaml`` in full, against the stored reference.

    A repeat at three depths at once, the deep rungs walked, and every line
    the template holds *after* a repeated block -- ``one: after level3-1``,
    ``alpha: after one``, ``main: between alpha and beta`` -- behind both
    members of its pair. Compared line for line and **without** collapsing
    digits: see the module docstring for why this case cannot afford that.
    """
    generate(tmp_path, document=DOCUMENT)
    document = tmp_path / 'out.docx'

    got = portable(said(document), document.parent)
    expected = [fold(line) for line in reference(REFERENCE, normalised=False)]

    assert got == expected, difference(expected, got)


def test_the_outline_follows_the_ladder(tmp_path):
    """Every clone keeps the heading style of the blueprint it came from, at
    every depth and for every instance -- something the text comparison above
    cannot see. The three deepest rungs share Heading 4 in this template, so
    the styles stop discriminating there and the *text* carries the depth."""
    generate(tmp_path, document=DOCUMENT)
    outline = [(p.style.name, p.text) for p in docx.Document('out.docx').paragraphs
               if p.style.name.startswith('Heading')]

    assert outline == [
        ('Heading 1', 'MAIN SECTION'),
        ('Heading 2', 'ALPHA Alpha one'),
        ('Heading 3', 'ONE One a'),
        ('Heading 4', 'LEVEL3-1 level3-1 a'),
        ('Heading 4', 'LEVEL3-1 level3-1 b'),
        ('Heading 4', 'LEVEL4-1 level4-1 first'),
        ('Heading 4', 'LEVEL5 level5 b'),
        ('Heading 4', 'LEVEL4-2 level4-2 first'),
        ('Heading 3', 'ONE One b'),
        ('Heading 2', 'ALPHA Alpha two'),
        ('Heading 2', 'BETA Beta one'),
        ('Heading 3', 'TWO Two a'),
        ('Heading 4', 'LEVEL3-2 level3-2 in beta'),
    ]


# ------------------------------------------------- a repeat behind its own

def test_a_repeat_lands_behind_the_instance_it_repeats(tmp_path):
    """Two instances of ``alpha`` stand together, and the line the template
    holds between the two subsections follows both.

    The line that used to be threaded between them.
    """
    said = generate(tmp_path, entries('alpha', 'A1', 'A2'))

    assert said == [*MAIN_OPEN,
                    *says('alpha', 'A1'),
                    *says('alpha', 'A2'),
                    *MAIN_MIDDLE,
                    # beta unused: pruned, the prose around it stays
                    *MAIN_CLOSE]


def test_the_prose_after_a_repeated_block_stays_behind_every_instance(tmp_path):
    """Four instances, not two: the prose does not creep forward with them."""
    said = generate(tmp_path, entries('alpha', 'A1', 'A2', 'A3', 'A4'))

    assert [line for line in said if line.startswith('ALPHA')] == \
        ['ALPHA A1', 'ALPHA A2', 'ALPHA A3', 'ALPHA A4']
    assert said.index('main: between alpha and beta') > said.index('ALPHA A4')
    assert said.count('alpha: after one') == 4, 'each instance keeps its own prose'


def test_a_repeat_of_the_last_block_stops_before_the_sections_own_prose(tmp_path):
    """The half with no unclaimed sibling left to fall through to.

    ``beta`` is the last block of ``section:main``, so nothing follows it in
    ``subAnchors``; the old rule reached for the section's closing paragraph
    and put the repeat past ``main: after beta`` and the section marker both.
    """
    said = generate(tmp_path, entries('beta', 'B1', 'B2'))

    assert said == [*MAIN_OPEN,
                    # alpha unused: pruned, the prose around it stays
                    *MAIN_MIDDLE,
                    *says('beta', 'B1'),
                    *says('beta', 'B2'),
                    *MAIN_CLOSE]


def test_two_repeated_blocks_each_keep_their_own_run(tmp_path):
    """Each block's instances gather at that block's own place, and the two
    runs stay in the template's order however the data interleaves them."""
    body = (entries('beta', 'B1')
            + entries('alpha', 'A1')
            + entries('beta', 'B2')
            + entries('alpha', 'A2'))
    said = generate(tmp_path, body)

    assert said == [*MAIN_OPEN,
                    *says('alpha', 'A1'),
                    *says('alpha', 'A2'),
                    *MAIN_MIDDLE,
                    *says('beta', 'B1'),
                    *says('beta', 'B2'),
                    *MAIN_CLOSE]


# --------------------------------------------------------- down the ladder

#: (the level to repeat, the heading its blueprint writes, the line of the
#: level ABOVE that must stay behind both instances). Every rung of the
#: docx ladder that ``template.docx`` carries.
DEPTHS = [
    ('subsection', 'ALPHA', 'main: between alpha and beta'),
    ('subsubsection', 'ONE', 'alpha: after one'),
    ('sub3section', 'LEVEL3-1', 'one: after level3-1'),
    ('sub4section', 'LEVEL4-1', 'One: after Level4-1'),
    ('sub5section', 'LEVEL5', 'One: after Level5'),
]

#: The chain down to each rung: (level, block, indent). An entry at depth *n*
#: sits four spaces deeper than its parent, the section body starting at six.
CHAIN = [('subsection', 'alpha', 6),
         ('subsubsection', 'one', 10),
         ('sub3section', 'level3-1', 14),
         ('sub4section', 'level4-1', 18),
         ('sub5section', 'level5', 22)]


@pytest.mark.parametrize('level, heading, behind', DEPTHS)
def test_the_rule_holds_at_every_ladder_depth(tmp_path, level, heading, behind):
    """A repeat at depth 1 to 5 lands behind its own instance, and the prose
    that closes the level above stays behind both.

    Each rung is repeated while every rung above it is walked once, so a
    misplaced clone at one depth cannot hide behind a misplaced clone at
    another.
    """
    body = ''
    for chainLevel, chainName, indent in CHAIN:
        if chainLevel == level:
            body += entries(chainName, 'X1', 'X2', level=level, indent=indent)
            break
        body += entries(chainName, 'once', level=chainLevel, indent=indent)

    said = generate(tmp_path, body)

    marks = [line for line in said if line.startswith(heading + ' ')]
    assert marks == [f'{heading} X1', f'{heading} X2'], said
    first, second = (said.index(mark) for mark in marks)
    assert first < second < said.index(behind), said


def test_a_nested_repeat_does_not_disturb_the_level_above(tmp_path):
    """``one`` twice inside a single ``alpha``: the pair sits inside ``alpha``,
    between ``alpha``'s own prose, and ``alpha`` still closes after both."""
    body = (entries('alpha', 'A1')
            + entries('one', 'N1', 'N2', level='subsubsection', indent=10))
    said = generate(tmp_path, body)

    assert said == [*MAIN_OPEN,
                    'ALPHA A1', 'alpha: A1', 'alpha: marker',
                    'alpha: before one',
                    *says('one', 'N1'),
                    *says('one', 'N2'),
                    'alpha: after one', 'alpha: end',
                    *MAIN_MIDDLE,
                    *MAIN_CLOSE]


# ------------------------------- a block named where the template has none

#: ``ladder.yaml`` names ``sub3section:level3-1`` under ``subsection:beta``,
#: where the template holds no such block -- it stands under
#: ``subsection:alpha``. Every line the run says about that, in order. Three
#: fills sit inside the entry (``subitem``, ``text:description`` and the
#: marker), and each of them reports its missing parent separately.
MISPLACED = 'section:main::1.subsection:beta::1.subsubsection:two::1.sub3section:level3-1::1'
EXPECTED_WARNINGS = [
    "WARNING: No exact match: ['section:main::1', 'subsection:beta::1', "
    "'subsubsection:two::1', 'sub3section:level3-1::1']",
    f'WARNING: Nothing to apply at {MISPLACED}',
    f'WARNING: No such parent structure: {MISPLACED}',
    f'WARNING: cannot find parent structure {MISPLACED}',
    f'WARNING: cannot find parent structure {MISPLACED}',
    f'WARNING: cannot find parent structure {MISPLACED}',
]


def test_a_block_named_where_the_template_does_not_hold_it_is_dropped(tmp_path, capsys):
    """A container address must exist in the template **at that place**.

    ``ladder.yaml`` asks for ``sub3section:level3-1`` inside
    ``subsection:beta`` > ``subsubsection:two``. The template holds a
    ``level3-1``, but under ``subsection:alpha`` -- and a blueprint standing
    under another parent is not reachable from here, because a container
    address is positional: ``findExact`` walks the parent that was named. So
    the entry, and every fill under it, is dropped.

    This is on purpose in the fixture and the warnings are the expected
    output, pinned in full so that a change to the diagnosis is a decision
    rather than a surprise. Six lines for one mistake is more than it needs
    -- the three ``cannot find parent structure`` are one per fill inside the
    entry that was never made -- and shortening them would be a fair thing to
    do; this test is what would tell you that you had.

    The one way to place content a section does not already contain is a
    **marker**: entries inside ``marker:name`` are looked up by name across
    the whole document, so a blueprint in ``<section:template>`` -- or one
    flagged anywhere -- reaches any marker. See *Content* in ``docs/rdf.md``.
    """
    said = generate(tmp_path, document=DOCUMENT)
    out = capsys.readouterr().out

    complaints = [line.strip() for line in out.splitlines()
                  if 'WARNING' in line or 'ERROR' in line]
    assert complaints == EXPECTED_WARNINGS, complaints

    # nothing of the misplaced entry reached the document, its fills included
    assert 'LEVEL3-1 level3-1 in beta' not in said
    assert 'Level3-1: the level3-1 in beta works as well, surprise!' not in said
    assert 'added at the level3-1 beta marker' not in said

    # and the block it was named beside is untouched: beta's own level3-2
    # stands, with its prose and its marker fill
    assert said[said.index('two: before level3-2'):said.index('two: after level3-2')] == [
        'two: before level3-2',
        'LEVEL3-2 level3-2 in beta',
        'Level3-2: the level3-2 in beta',
        'Level3-2: marker',
        'added at the level3-2 beta marker',
        'Level3-2: end',
    ]

    # the same block named where the template DOES hold it is placed twice
    assert [line for line in said if line.startswith('LEVEL3-1 ')] == \
        ['LEVEL3-1 level3-1 a', 'LEVEL3-1 level3-1 b']


# ------------------------------- repeating requires the template argument

def built_template(*, flagged, name='plain'):
    """One subsection with prose around it, flagged or not.

    No shipped template has an unflagged ladder block that a document would
    want twice -- the shape only exists to be refused -- so it is built here,
    as ``test_docx_clone_order.py`` builds the shape it needs.
    """
    flag = ' template' if flagged else ''
    document = docx.Document()
    for line in ('<section:main>MAIN SECTION',
                 'main: before plain',
                 f'<subsection:{name}{flag}>PLAIN <head/>',
                 'plain: body',
                 f'</subsection:{name}>',
                 'main: after plain'):
        document.add_paragraph(line)
    document.add_section()
    # A section ends with its break paragraph, and that paragraph must carry
    # the closing tag -- nothing may sit between the two.
    document.paragraphs[-1].text = 'main: end</section:main>'
    document.add_paragraph('<section:template>')
    document.add_paragraph('</section:template>')
    return document


#: The same block named twice -- the whole document these three tests need.
TWICE = ('      - subsection:plain:\n          - head: P1\n'
         '      - subsection:plain:\n          - head: P2\n')


def test_repeating_an_unflagged_block_is_refused_and_says_what_to_add(tmp_path, capsys):
    """**Repeating a block requires the ``template`` argument** (narrowed
    2026-08-30, decision on the DOCX board). A block without it is filled
    where it stands and cannot be repeated: there is no blueprint to clone.

    The contract used to promise the other thing -- *instance 1 is that block,
    later instances clone it* -- while ``Sections.findTemplate`` had only ever
    searched the template section and the flagged blocks, so the promise never
    once held. Narrowed rather than implemented: it is the smaller change, it
    is what the code already did, and it follows *Flagged is never content,
    uniformly*, which moved every other block kind to clone-first.

    What is pinned here is the **diagnosis**, because that is what turns a
    narrowed contract into a usable one. One message, naming the block and the
    argument to add. Before: ``No such template in document``, which sends the
    author looking for a missing name rather than a missing argument -- and
    then one ``cannot find parent structure`` per fill inside the instance
    that was never made.
    """
    said = generate(tmp_path, TWICE, template=built_template(flagged=False))
    out = capsys.readouterr().out

    assert said == ['MAIN SECTION', 'main: before plain',
                    'PLAIN P1', 'plain: body',
                    'main: after plain'], \
        'instance 1 fills the block where it stands; instance 2 is refused'

    refusals = [line for line in out.splitlines() if 'cannot repeat' in line]
    assert len(refusals) == 1, out
    assert "'subsection:plain'" in refusals[0], 'it names the block'
    assert '<subsection:plain template>' in refusals[0], 'it says what to add'
    assert 'No such template' not in out, 'the name is not what is missing'
    assert 'cannot find parent structure' not in out, \
        'the refused instance does not warn again, once per fill inside it'


def test_the_same_block_flagged_repeats_without_a_word(tmp_path, capsys):
    """The other half of the contract, on the same template: add the argument
    and the repeat is placed -- behind its own instance, prose after both."""
    said = generate(tmp_path, TWICE, template=built_template(flagged=True))
    out = capsys.readouterr().out

    assert said == ['MAIN SECTION', 'main: before plain',
                    'PLAIN P1', 'plain: body',
                    'PLAIN P2', 'plain: body',
                    'main: after plain']
    assert 'WARNING' not in out, out


def test_a_name_the_template_does_not_hold_is_still_unknown(tmp_path, capsys):
    """The other side of the branch: the *add the argument* message is for a
    block that is really there. A name the template holds nowhere is a
    different mistake and keeps the words it always had."""
    generate(tmp_path,
             '      - subsection:ghost:\n          - head: G1\n'
             '      - subsection:ghost:\n          - head: G2\n',
             template=built_template(flagged=True))
    out = capsys.readouterr().out

    assert 'No such template in document' in out
    assert 'cannot repeat' not in out
