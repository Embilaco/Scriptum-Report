"""A clone must land after the instance it follows, not above it.

The bug this guards was reproduced on two of the shipped templates with the
current ``.rdf`` format, so it is not something the YAML work introduced.

``subAnchors`` holds the opening paragraph of each ladder-type child of a
structure, in document order. ``apply`` claimed one; ``copy`` inserted before
whichever was left at the front. When the document never used a blueprint that
sits *earlier* in the template, that blueprint stayed at the front -- so the
clone was inserted before it, upstream of the block it was supposed to follow.
The unused blueprint is pruned at the end, by which time the clone is already
in the wrong place.

``template_text.docx`` is the right template for this: ``section:second`` holds
``<subsection:seconda template>`` and then ``<subsection:secondb template>``, so
using only ``secondb`` leaves an earlier blueprint unclaimed.

The fix is that claiming a child claims everything ahead of it too -- nothing at
or before it can be a valid insertion point for content that comes after it.
"""

from pathlib import Path
import shutil
import sys

import docx

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = THIS_DIR.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT))

from _setup_docx_basic import *          # noqa: F401,F403  (brings reset_state)

TEMPLATE = 'template_text.docx'
MARKS = ('ZZintro', 'ZZsibling', 'ZZfirst', 'ZZsecond')


def generate(tmp_path, use_sibling):
    """Build a document that repeats ``subsection:secondb``, and read its order."""
    import Scriptum

    shutil.copy(THIS_DIR / TEMPLATE, tmp_path)
    (tmp_path / 'data').mkdir(exist_ok=True)

    sibling = ''
    if use_sibling:
        sibling = ('      - subsection:seconda:\n'
                   '          - head: ZZsibling\n')

    (tmp_path / 'case.yaml').write_text(
        '_scriptum_:\n'
        '  version: 4\n'
        '  documenttype: docx\n'
        '  datadir: ./data\n'
        '_content_:\n'
        '  - section:second:\n'
        '      - text:description: ZZintro\n'
        + sibling +
        '      - subsection:secondb:\n'
        '          - head: ZZfirst\n'
        '      - subsection:secondb:\n'
        '          - head: ZZsecond\n',
        encoding='utf-8')

    os.chdir(tmp_path)
    rdf = Scriptum.ReportDataFile('case.yaml')
    document = Scriptum.ManagedDocx(TEMPLATE, rdf)
    document.typesetting(rdf)
    document.save('out.docx')

    return [p.text.strip() for p in docx.Document('out.docx').paragraphs
            if p.text.strip() in MARKS]


def test_a_clone_follows_its_instance_when_an_earlier_blueprint_is_unused(tmp_path):
    """The regression. Before the fix this came back as intro, second, first."""
    assert generate(tmp_path, use_sibling=False) == \
        ['ZZintro', 'ZZfirst', 'ZZsecond']


def test_a_clone_still_follows_its_instance_when_the_blueprint_is_used(tmp_path):
    """The case that always worked, kept so the fix cannot break it."""
    assert generate(tmp_path, use_sibling=True) == \
        ['ZZintro', 'ZZsibling', 'ZZfirst', 'ZZsecond']


def test_claiming_a_child_claims_everything_ahead_of_it():
    """The rule on its own, without a document.

    A child that is no longer listed is not an error: a document may use blocks
    in an order the template does not hold them in, and the first such use
    already dropped the ones ahead of it.
    """
    from Scriptum._docx.structure import StructuredElement

    holder = StructuredElement.__new__(StructuredElement)
    holder.subAnchors = ['a', 'b', 'c', 'd']

    holder.claimSubAnchor('c')
    assert holder.subAnchors == ['d']

    holder.claimSubAnchor('a')          # already gone, and not an error
    assert holder.subAnchors == ['d']

    holder.claimSubAnchor('d')
    assert holder.subAnchors == []
