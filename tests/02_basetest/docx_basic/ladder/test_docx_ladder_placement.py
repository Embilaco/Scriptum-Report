"""The ladder case: which block a repeat lands behind, and where the gap is.

``test_docx_clone_order.py`` in the ``text`` case beside this one pins *which*
block a clone follows and what is left of a blueprint afterwards. This case
pins *where the gap behind an instance is* -- the half no template without
prose between its blocks can show, because the two candidate landing places
coincide there.

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
``StructuredElement.followInstance``; every test below fails without it.

The fixture
-----------
``template.docx`` is a clean ladder -- ``section:main`` > ``subsection:alpha``
> ``subsubsection:one`` > ``sub3section:deep``, plus a second subsection
``beta`` beside ``alpha`` -- with every block flagged ``template`` and an
ordinary paragraph in **every** gap: before a block, between two blocks, after
a block, and on both sides of each nested child. Each block also carries a
``<text:description/>`` and a ``<marker:content/>``, so a fill can never be
mistaken for a clone. ``ladder.yaml`` is the canonical document, one repeat at
every depth; the focused tests below write their own small documents against
the same template.

The one shape the template cannot express -- a block *without* the ``template``
argument -- gets a template built in the test, as ``test_docx_clone_order.py``
does for its own odd shape.
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

TEMPLATE = 'template.docx'
DOCUMENT = 'ladder.yaml'

HEADER = ('_scriptum_:\n'
          '  version: 4\n'
          '  documenttype: docx\n'
          '  datadir: ./data\n'
          '_content_:\n')

#: The tag each ladder level writes for its heading.
HEAD_TAG = {'subsection': 'head', 'subsubsection': 'item', 'sub3section': 'subitem'}

#: What one instance of each block says when its head and its description are
#: filled, its marker is not fed and its child is not used: the template's own
#: prose around the fills, which is exactly what a misplaced clone disturbs.
#: ``{}`` takes the head, which the helpers below use as the description too.
QUIET = {
    'alpha': ['ALPHA {}', 'alpha: {}', 'alpha: marker',
              'alpha: before one', 'alpha: after one', 'alpha: end'],
    'beta': ['BETA {}', 'beta: {}', 'beta: marker', 'beta: end'],
    'one': ['ONE {}', 'one: {}', 'one: marker',
            'one: before deep', 'one: after deep', 'one: end'],
    'deep': ['DEEP {}', 'deep: {}', 'deep: marker', 'deep: end'],
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
    the case directory, or a ``docx.Document`` built in the test.
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

def test_the_ladder_document_reads_as_the_template_orders_it(tmp_path):
    """``ladder.yaml`` in full: a repeat at depth 1, 2 and 3 at once.

    Read as a whole rather than by index, because placement is the one thing
    a partial reading hides: each pair of instances stands together, and every
    line the template holds *after* a repeated block -- ``one: after deep``,
    ``alpha: after one``, ``main: between alpha and beta`` -- comes after both
    members of the pair, at every depth.
    """
    assert generate(tmp_path, document=DOCUMENT) == [
        'MAIN SECTION',
        'main: before alpha',

        'ALPHA Alpha one',
        'alpha: the first alpha',
        'alpha: marker',
        'added at the alpha one marker',
        'alpha: before one',

        'ONE One a',
        'one: the first one',
        'one: marker',
        'added at the one a marker',
        'one: before deep',

        'DEEP Deep a',
        'deep: the first deep',
        'deep: marker',
        'added at the deep a marker',
        'deep: end',

        'DEEP Deep b',
        'deep: the second deep',
        'deep: marker',
        'deep: end',

        'one: after deep',
        'one: end',

        'ONE One b',
        'one: the second one',
        'one: marker',
        'one: before deep',
        'one: after deep',
        'one: end',

        'alpha: after one',
        'alpha: end',

        'ALPHA Alpha two',
        'alpha: the second alpha',
        'alpha: marker',
        'alpha: before one',
        'alpha: after one',
        'alpha: end',

        'main: between alpha and beta',

        'BETA Beta one',
        'beta: the only beta',
        'beta: marker',
        'beta: end',

        'main: after beta',
        'main: marker',
        'added at the main marker',
    ]


def test_the_outline_follows_the_ladder(tmp_path):
    """Every clone keeps the heading style of the blueprint it came from, at
    every depth and for every instance -- something the text comparison above
    cannot see."""
    generate(tmp_path, document=DOCUMENT)
    outline = [(p.style.name, p.text) for p in docx.Document('out.docx').paragraphs
               if p.style.name.startswith('Heading')]

    assert outline == [
        ('Heading 1', 'MAIN SECTION'),
        ('Heading 2', 'ALPHA Alpha one'),
        ('Heading 3', 'ONE One a'),
        ('Heading 4', 'DEEP Deep a'),
        ('Heading 4', 'DEEP Deep b'),
        ('Heading 3', 'ONE One b'),
        ('Heading 2', 'ALPHA Alpha two'),
        ('Heading 2', 'BETA Beta one'),
    ]


# ------------------------------------------------- a repeat behind its own

def test_a_repeat_lands_behind_the_instance_it_repeats(tmp_path):
    """Two instances of ``alpha`` stand together, and the line the template
    holds between the two subsections follows both.

    The line that used to be threaded between them.
    """
    said = generate(tmp_path, entries('alpha', 'A1', 'A2'))

    assert said == ['MAIN SECTION', 'main: before alpha',
                    *says('alpha', 'A1'),
                    *says('alpha', 'A2'),
                    'main: between alpha and beta',
                    # beta unused: pruned, the prose around it stays
                    'main: after beta', 'main: marker']


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

    assert said == ['MAIN SECTION', 'main: before alpha',
                    # alpha unused: pruned, the prose around it stays
                    'main: between alpha and beta',
                    *says('beta', 'B1'),
                    *says('beta', 'B2'),
                    'main: after beta', 'main: marker']


def test_two_repeated_blocks_each_keep_their_own_run(tmp_path):
    """Each block's instances gather at that block's own place, and the two
    runs stay in the template's order however the data interleaves them."""
    body = (entries('beta', 'B1')
            + entries('alpha', 'A1')
            + entries('beta', 'B2')
            + entries('alpha', 'A2'))
    said = generate(tmp_path, body)

    assert said == ['MAIN SECTION', 'main: before alpha',
                    *says('alpha', 'A1'),
                    *says('alpha', 'A2'),
                    'main: between alpha and beta',
                    *says('beta', 'B1'),
                    *says('beta', 'B2'),
                    'main: after beta', 'main: marker']


# --------------------------------------------------------- down the ladder

#: (the level to repeat, the heading its blueprint writes, the line of the
#: level ABOVE that must stay behind both instances)
DEPTHS = [
    ('subsection', 'ALPHA', 'main: between alpha and beta'),
    ('subsubsection', 'ONE', 'alpha: after one'),
    ('sub3section', 'DEEP', 'one: after deep'),
]


@pytest.mark.parametrize('level, heading, behind', DEPTHS)
def test_the_rule_holds_at_every_ladder_depth(tmp_path, level, heading, behind):
    """A repeat at depth 1, 2 and 3 lands behind its own instance, and the
    prose that closes the level above stays behind both.

    Each level is repeated while the levels above it are used once, so a
    misplaced clone at one depth cannot hide behind a misplaced clone at
    another.
    """
    if level == 'subsection':
        body = entries('alpha', 'A1', 'A2')
    elif level == 'subsubsection':
        body = (entries('alpha', 'A1')
                + entries('one', 'N1', 'N2', level='subsubsection', indent=10))
    else:
        body = (entries('alpha', 'A1')
                + entries('one', 'N1', level='subsubsection', indent=10)
                + entries('deep', 'D1', 'D2', level='sub3section', indent=14))

    said = generate(tmp_path, body)

    marks = [line for line in said if line.startswith(heading + ' ')]
    assert len(marks) == 2, said
    first, second = (said.index(mark) for mark in marks)
    assert first < second < said.index(behind), said


def test_a_nested_repeat_does_not_disturb_the_level_above(tmp_path):
    """``one`` twice inside a single ``alpha``: the pair sits inside ``alpha``,
    between ``alpha``'s own prose, and ``alpha`` still closes after both."""
    body = (entries('alpha', 'A1')
            + entries('one', 'N1', 'N2', level='subsubsection', indent=10))
    said = generate(tmp_path, body)

    assert said == ['MAIN SECTION', 'main: before alpha',
                    'ALPHA A1', 'alpha: A1', 'alpha: marker',
                    'alpha: before one',
                    *says('one', 'N1'),
                    *says('one', 'N2'),
                    'alpha: after one', 'alpha: end',
                    'main: between alpha and beta',
                    'main: after beta', 'main: marker']


# ---------------------------------------------------------- the known gap

def unflagged_template():
    """``subsection:plain`` without the ``template`` argument, prose around it.

    No shipped template has a repeatable unflagged ladder block, and the rule
    as documented says there should be one -- so the shape is built here.
    """
    document = docx.Document()
    for line in ('<section:main>MAIN SECTION',
                 'main: before plain',
                 '<subsection:plain>PLAIN <head/>',
                 'plain: body',
                 '</subsection:plain>',
                 'main: after plain'):
        document.add_paragraph(line)
    document.add_section()
    # A section ends with its break paragraph, and that paragraph must carry
    # the closing tag -- nothing may sit between the two.
    document.paragraphs[-1].text = 'main: end</section:main>'
    document.add_paragraph('<section:template>')
    document.add_paragraph('</section:template>')
    return document


@pytest.mark.xfail(strict=True,
                   reason='an unflagged block cannot be repeated at all: '
                          'findTemplate looks only at flagged blocks')
def test_an_unflagged_block_can_be_repeated_too(tmp_path):
    """The documented rule says a block without ``template`` is content whose
    first instance is the block itself and whose later instances clone it. The
    second half does not happen: ``Sections.findTemplate`` searches the
    templates list, which holds the template section and the flagged blocks
    only, so the copy finds nothing, warns ``No such template in document``,
    and the instance is dropped before any placement rule is reached.

    Strict on purpose: the day the lookup is widened this fails for passing,
    and where that clone lands wants pinning here beside the rest.
    """
    said = generate(tmp_path,
                    '      - subsection:plain:\n          - head: P1\n'
                    '      - subsection:plain:\n          - head: P2\n',
                    template=unflagged_template())

    assert said == ['MAIN SECTION', 'main: before plain',
                    'PLAIN P1', 'plain: body',
                    'PLAIN P2', 'plain: body',
                    'main: after plain', 'main: end']
