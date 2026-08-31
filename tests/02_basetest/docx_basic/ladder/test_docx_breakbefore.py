"""``breakbefore``: which instances get a page break, pinned as it stands.

The argument puts a page break in front of a block. **Today it fires for
every instance, the first one included** — a blueprint's first instance is a
clone like all the others, and the break is added in
``StructuredElement.copy()``, which runs for that clone too.

Why this module exists
----------------------
Until it was written the suite had **no** behavioural coverage of
``breakbefore`` at all: `tests/02_basetest/tag/test_tag.py` pins that the
argument parses and that numbering a clone keeps it, and nothing anywhere
asserted that a page break reaches a document. So the rule below was carried
by one line in a decision page and by three shipped templates that nobody
measured.

The half that is under review is the first instance. *Templates, anchors,
copy/apply/add* (DOCX board) records that firing on ``::1`` was chosen on
purpose — "the author's *each of these starts on a new page* includes the
first" — and the directive *Next: the section:template requirement, and a
test for breakbefore* asks for that to be revisited. **This module pins the
present behaviour, not a preference.** If the rule is changed,
``test_the_first_instance_gets_one_too`` and the essay measurement below are
what will fail, and their diff is the change's blast radius.

What a reversal would move
--------------------------
Three shipped templates flag blocks ``breakbefore``:
``docx_basic/simple``, ``04_examples/wordreport`` (``tool``, ``preparation``,
``testplan``) and ``04_examples/essay`` (``content``). The essay is the
telling one and is measured here: its template carries **two manual page
breaks** in front of its blueprint, from before the rule was uniform, so its
first content section is preceded by three breaks and every later one by a
single break. Exempting ``::1`` would make those two manual breaks
load-bearing again rather than redundant.

The one path that never breaks
------------------------------
A *simple* tag cloned at a marker — ``<text:plain/>`` and its kind — goes
through ``DocParagraphElement.copy()``, which has no page-break step at all;
only the block classes inherit ``StructuredElement.copy()``. That asymmetry
is out of scope here: it is the same whichever way ``::1`` is decided.
"""

from pathlib import Path
import shutil
import sys

import pytest

docx = pytest.importorskip('docx')
from docx.oxml.ns import qn                                    # noqa: E402

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = THIS_DIR.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT))

from _setup_docx_basic import *          # noqa: F401,F403  (brings reset_state, os)
from common_case import CaseConfig, run_docx_case              # noqa: E402

#: `04_examples/essay`, reached from here because what it demonstrates is a
#: property of *this* rule, not of that case: the essay test would have no
#: reason to explain the number it sees.
EXAMPLES = CASE_ROOT.parent.parent / '04_examples'

HEADER = ('_scriptum_:\n'
          '  version: 4\n'
          '  documenttype: docx\n'
          '  datadir: .\n'
          '_content_:\n')


def template(*, flag=' breakbefore', nested_flag=' breakbefore'):
    """``section:main`` holding ``alpha``, which holds ``one``.

    Both blueprints, each flagged independently so a test can put the
    argument on one level and not the other. Ordinary prose around every
    block, so a break's *position* is visible and not only its count.
    """
    document = docx.Document()
    for line in ('<section:main>MAIN',
                 'before alpha',
                 f'<subsection:alpha template{flag}>ALPHA <head/>',
                 'alpha: before one',
                 f'<subsubsection:one template{nested_flag}>ONE <item/>',
                 'one body',
                 '</subsubsection:one>',
                 'alpha: after one',
                 '</subsection:alpha>',
                 'after alpha'):
        document.add_paragraph(line)
    document.add_section()
    # A section ends with its break paragraph, and that paragraph must carry
    # the closing tag -- nothing may sit between the two.
    document.paragraphs[-1].text = 'main: end</section:main>'
    document.add_paragraph('<section:template>')
    document.add_paragraph('</section:template>')
    return document


def generate(tmp_path, body, built=None):
    """Build *body* against the template and return the finished path."""
    import Scriptum

    (built or template()).save(tmp_path / 'built.docx')
    (tmp_path / 'case.yaml').write_text(
        HEADER + '  - section:main:\n' + body, encoding='utf-8')

    os.chdir(tmp_path)
    rdf = Scriptum.ReportDataFile('case.yaml')
    assert not rdf.errors, rdf.errors
    managed = Scriptum.ManagedDocx('built.docx', rdf)
    managed.typesetting(rdf)
    managed.save('out.docx')
    return tmp_path / 'out.docx'


def broken(path):
    """The document as ``(breaks before it, text)`` per non-empty paragraph.

    A page break is written into a paragraph of its own, so what matters is
    how many such paragraphs stand between one piece of text and the next --
    which is exactly what the essay measurement below has to count.
    """
    lines, pending = [], 0
    for paragraph in docx.Document(path).paragraphs:
        if any(b.get(qn('w:type')) == 'page'
               for b in paragraph._p.iter(qn('w:br'))):
            pending += 1
        if paragraph.text.strip():
            lines.append((pending, paragraph.text.strip()))
            pending = 0
    return lines


def entries(name, *heads, level='subsection', indent=6):
    tag = {'subsection': 'head', 'subsubsection': 'item'}[level]
    pad = ' ' * indent
    return ''.join(f'{pad}- {level}:{name}:\n{pad}    - {tag}: {head}\n'
                   for head in heads)


# ----------------------------------------------------------- the rule today

def test_the_first_instance_gets_one_too(tmp_path):
    """**The half under review.** One instance, one page break, and it stands
    between the prose before the block and the block's own first paragraph --
    not merely somewhere in the document.

    Change the rule and this is the first test that says so.
    """
    assert broken(generate(tmp_path, entries('alpha', 'A1'))) == [
        (0, 'MAIN'),
        (0, 'before alpha'),
        (1, 'ALPHA A1'),          # <- the break in question
        (0, 'alpha: before one'),
        (0, 'alpha: after one'),
        (0, 'after alpha'),
    ]


def test_every_further_instance_gets_one(tmp_path):
    """Three instances, three breaks -- one in front of each."""
    said = broken(generate(tmp_path, entries('alpha', 'A1', 'A2', 'A3')))

    assert [(n, text) for n, text in said if text.startswith('ALPHA')] == \
        [(1, 'ALPHA A1'), (1, 'ALPHA A2'), (1, 'ALPHA A3')]
    assert sum(n for n, _ in said) == 3, 'no break anywhere else'


def test_without_the_argument_nothing_is_added(tmp_path):
    """The control. The same document against a template that does not carry
    the argument has no page breaks at all."""
    said = broken(generate(tmp_path, entries('alpha', 'A1', 'A2'),
                           built=template(flag='', nested_flag='')))

    assert sum(n for n, _ in said) == 0, said


def test_a_break_lands_at_every_depth(tmp_path):
    """Each level's blueprint is flagged separately and breaks for itself, so
    a nested repeat gets one break per instance per level."""
    body = (entries('alpha', 'A1')
            + entries('one', 'N1', 'N2', level='subsubsection', indent=10))
    said = broken(generate(tmp_path, body))

    assert said == [
        (0, 'MAIN'),
        (0, 'before alpha'),
        (1, 'ALPHA A1'),
        (0, 'alpha: before one'),
        (1, 'ONE N1'),
        (0, 'one body'),
        (1, 'ONE N2'),
        (0, 'one body'),
        (0, 'alpha: after one'),
        (0, 'after alpha'),
    ]


def test_the_outer_level_can_break_while_the_inner_does_not(tmp_path):
    """The argument is per block, not inherited: flagging ``alpha`` alone
    leaves ``one`` unbroken however often it repeats."""
    body = (entries('alpha', 'A1')
            + entries('one', 'N1', 'N2', level='subsubsection', indent=10))
    said = broken(generate(tmp_path, body, built=template(nested_flag='')))

    assert [(n, text) for n, text in said if text.startswith(('ALPHA', 'ONE'))] == \
        [(1, 'ALPHA A1'), (0, 'ONE N1'), (0, 'ONE N2')]


def test_an_unused_blueprint_leaves_no_stray_break(tmp_path):
    """A blueprint nobody names is pruned, and the page break goes with it --
    a break is added when a clone is made, never by the blueprint standing
    there. Worth pinning: the break paragraph is a separate paragraph, and a
    pruning pass that missed it would leave a blank page behind."""
    said = broken(generate(tmp_path, '      - text:description: nothing used\n'))

    assert sum(n for n, _ in said) == 0, said
    assert [text for _, text in said] == ['MAIN', 'before alpha', 'after alpha']


# ------------------------------------------- what a reversal would move

def test_the_shipped_essay_stacks_three_breaks_before_its_first_section(tmp_path):
    """The blast radius of exempting ``::1``, measured rather than guessed.

    ``04_examples/essay`` flags ``subsection:content`` and its template also
    carries **two manual page breaks** in front of that blueprint, put there
    before the rule was uniform to get the effect the rule now gives. So the
    first content section is preceded by three breaks and every later one by
    exactly one.

    Exempting the first instance would turn this from ``3, 1, 1, ...`` into
    ``2, 0, 0, ...`` -- the manual pair becoming load-bearing again and every
    later section losing its break. That is the decision in one line, and it
    is why this measurement lives with the rule rather than with the essay.
    """
    essay = EXAMPLES / 'essay'
    if not (essay / 'essay.docx').is_file():
        pytest.skip(f'the essay case is not at {essay}')

    document = run_docx_case(CaseConfig(
        name='essay', case_dir=essay, document_name='essay.yaml',
        template_doc_name='essay.docx', output_name='breaks.docx',
        include_patterns=['essay*.yaml', 'essay.docx'],
        data_source_dir=essay / 'data', finish=False, createpdf=False), tmp_path)

    # which headings belong to subsection:content, read out of the document
    # rather than guessed: the essay's other blocks are Heading 1 too, and
    # picking the broken ones would be assuming the answer
    lines = (essay / 'essay.yaml').read_text(encoding='utf-8').splitlines()
    heads = [after.split('head:', 1)[1].strip().strip('\'"')
             for line, after in zip(lines, lines[1:])
             if line.strip() == '- subsection:content:' and 'head:' in after]
    assert len(heads) > 3, f'expected the essay to repeat its content block: {heads}'

    counted = {text: n for n, text in broken(document)}
    per_section = [counted[head] for head in heads]

    assert per_section[0] == 3, \
        f"two manual breaks in the template plus the rule's own: {per_section}"
    assert set(per_section[1:]) == {1}, \
        f'every later instance gets exactly one: {per_section}'
