"""``findTemplate`` on a name that exists twice: section:template wins, loudly.

`8c3c210` widened the bare-name lookup -- what an ``add`` at a marker carries
-- to every block flagged ``template``; the shipped templates keep blueprint
names unique, so the collision rules ran on trust: the template section
outranks an in-content blueprint, and any multi-hit is warned about (names
being documented as unique).

Since the ladder rule was extended to in-content blocks (*Flagged is never
content, uniformly*, DOCX board, 2026-08-26), a flagged block is a blueprint
everywhere: instance 1 of ``table:dup`` is a clone standing exactly where
the blueprint stood, an unused blueprint -- the collision loser included --
is pruned instead of shipping with its sample text, and an add-only use no
longer splits: the fill skips the flagged namesake and lands in the clone
the add placed at the marker, so the old two-halves warning is gone along
with the behaviour it warned about.

Templates are built in-test, the way ``test_docx_clone_order.py`` builds its
own; like there, each carries a ``section:template`` -- ``typesetting``
deletes that section by name and does not expect a document without one. The
winner is read off the finished document: a CSV fill lands below the sample
row, whose second cell carries each blueprint's fingerprint.
"""

from pathlib import Path
import os
import sys

import pytest

docx = pytest.importorskip('docx')

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = THIS_DIR.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT))

from _setup_docx_basic import *          # noqa: F401,F403

HEADER = ('_scriptum_:\n'
          '  version: 4\n'
          '  documenttype: docx\n'
          '  datadir: ./data\n'
          '_content_:\n')

#: Instance 1 in place, instance 2 added at the marker by bare name.
BODY = ('  - section:mix:\n'
        '      - table:dup: {file: mini1.csv}\n'
        '      - marker:content:\n'
        '          - table:dup: {file: mini2.csv}\n')

#: The colliding name used ONLY through the marker: the add is instance ::1.
ADD_ONLY_BODY = ('  - section:mix:\n'
                 '      - marker:content:\n'
                 '          - table:dup: {file: mini2.csv}\n')


def blueprint(document, fingerprint, *, flagged):
    """A ``table:dup`` blueprint block whose second cell says *fingerprint*.

    Two rows, like every shipped blueprint table: the first is the sample
    row the fingerprint rides in, the second is where a CSV fill lands."""
    flag = ' template' if flagged else ''
    document.add_paragraph(f'<table:dup{flag}>')
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 1).text = fingerprint
    document.add_paragraph('</table:dup>')


def collision_template(*, in_template_section):
    """``table:dup`` twice: in ``section:mix`` (*FromContent*), and either in
    ``section:template`` (*FromTemplateSection*) or flagged in a second
    content section (*FromSecond*, with an empty template section after)."""
    document = docx.Document()
    document.add_paragraph('<section:mix>MIX')
    document.add_paragraph('<marker:content/>')
    blueprint(document, 'FromContent', flagged=True)
    document.add_section()
    # A section ends with its break paragraph, and that paragraph must carry
    # the closing tag -- nothing may sit between the two.
    document.paragraphs[-1].text = '</section:mix>'
    if in_template_section:
        document.add_paragraph('<section:template>')
        blueprint(document, 'FromTemplateSection', flagged=False)
        document.add_paragraph('</section:template>')
    else:
        document.add_paragraph('<section:extra>EXTRA')
        blueprint(document, 'FromSecond', flagged=True)
        document.add_section()
        document.paragraphs[-1].text = '</section:extra>'
        document.add_paragraph('<section:template>')
        document.add_paragraph('</section:template>')
    return document


def generate(tmp_path, template, body=BODY):
    """Build the collision document and return its tables."""
    import Scriptum

    template.save(tmp_path / 'built.docx')
    (tmp_path / 'data').mkdir(exist_ok=True)
    (tmp_path / 'data' / 'mini1.csv').write_text('ZZinplace\n', encoding='utf-8')
    (tmp_path / 'data' / 'mini2.csv').write_text('ZZadded\n', encoding='utf-8')
    (tmp_path / 'case.yaml').write_text(HEADER + body, encoding='utf-8')

    os.chdir(tmp_path)
    rdf = Scriptum.ReportDataFile('case.yaml')
    document = Scriptum.ManagedDocx('built.docx', rdf)
    document.typesetting(rdf)
    document.save('out.docx')

    return docx.Document('out.docx').tables


def fingerprints(tables):
    return [table.cell(0, 1).text for table in tables]


def cells(table):
    return [cell.text for row in table.rows for cell in row.cells]


def no_template_section():
    """``section:mix`` with a flagged blueprint and **no** ``section:template``.

    Every other template in the tree carries one, which is how the section
    came to look required when nothing about it is.
    """
    document = docx.Document()
    document.add_paragraph('<section:mix>MIX')
    document.add_paragraph('<marker:content/>')
    blueprint(document, 'FromContent', flagged=True)
    document.add_section()
    # A section ends with its break paragraph, and that paragraph must carry
    # the closing tag -- nothing may sit between the two.
    document.paragraphs[-1].text = '</section:mix>'
    return document


def test_a_template_without_a_template_section_builds_and_says_so(tmp_path, capsys):
    """``<section:template>`` is **not** required (decided 2026-08-31).

    ``typesetting`` removes that section by name at the end of every run, and
    the removal used to be ``byName`` followed straight by ``.delete()`` -- so
    a template without one died on ``AttributeError: 'NoneType' object has no
    attribute 'delete'``, at the very end of a run that had otherwise
    succeeded and with nothing naming the cause. A template whose document
    adds nothing at a marker has no use for the section, and a blueprint may
    be flagged anywhere in the content instead.

    A warning rather than silence: forgetting the section in a template whose
    document *does* add at markers is a real mistake, and the run would
    otherwise report only each add failing on its own.
    """
    tables = generate(tmp_path, no_template_section())
    out = capsys.readouterr().out

    assert fingerprints(tables) == ['FromContent', 'FromContent'],         'the in-content blueprint still serves both the marker add and its own spot'
    assert 'ZZadded' in cells(tables[0])
    assert 'ZZinplace' in cells(tables[1])

    missing = [line for line in out.splitlines() if 'no section' in line]
    assert len(missing) == 1, out
    assert "'template'" in missing[0], 'it names the section'
    assert 'unaffected' in missing[0],         'and says the flagged blueprints elsewhere still work -- which they did above'
    assert 'AttributeError' not in out and 'Traceback' not in out


def test_the_template_section_wins_the_collision(tmp_path, capsys):
    """The add clones the ``section:template`` blueprint, not the in-content
    one -- and says so: a multi-hit is warned about even when the ranking
    settles it. Instance 1 is a clone of the in-content blueprint, standing
    exactly where the blueprint stood -- same fingerprint, same spot, the
    blueprint itself pruned; the template section is removed as always."""
    tables = generate(tmp_path, collision_template(in_template_section=True))
    out = capsys.readouterr().out

    assert fingerprints(tables) == ['FromTemplateSection', 'FromContent'], \
        'the clone at the marker first, then the clone in the blueprint spot'
    assert 'ZZadded' in cells(tables[0]), 'the marker add got its own CSV'
    assert 'ZZinplace' in cells(tables[1]), 'instance 1 filled where the blueprint stood'
    assert "template 'table:dup' is ambiguous" in out
    assert 'section:template' in out.split('is ambiguous', 1)[1].splitlines()[0], \
        'the warning lists the hits, the template section first'


def test_without_a_template_section_hit_the_first_flagged_block_wins(tmp_path, capsys):
    """Both blueprints live in content sections: the first in document order
    is cloned to the marker, the ambiguity is still warned about -- and the
    unused loser is pruned, not shipped."""
    tables = generate(tmp_path, collision_template(in_template_section=False))
    out = capsys.readouterr().out

    assert fingerprints(tables) == ['FromContent', 'FromContent'], \
        'the clone at the marker, the clone in the blueprint spot -- no loser'
    assert 'ZZadded' in cells(tables[0])
    assert 'ZZinplace' in cells(tables[1])
    assert "template 'table:dup' is ambiguous" in out


def test_an_add_only_use_of_the_colliding_name_fills_the_clone(tmp_path, capsys):
    """The old two-halves split is gone: the name's only use is the marker
    add, so its address is instance ::1 -- the lookup clones the collision
    winner to the marker, and the fill, skipping the flagged namesake,
    lands in exactly that clone. The unused in-content blueprint is pruned;
    nothing is left to warn about (the ``0a518d0`` warning went with the
    behaviour -- *Flagged is never content, uniformly*, DOCX board)."""
    tables = generate(tmp_path, collision_template(in_template_section=True),
                      body=ADD_ONLY_BODY)
    out = capsys.readouterr().out

    assert fingerprints(tables) == ['FromTemplateSection'], \
        'one table: the clone at the marker; the unused blueprint is pruned'
    assert 'ZZadded' in cells(tables[0]), 'the content lands in the clone'
    assert 'the clone stays empty' not in out, \
        'the split warning went with the split'
    assert "template 'table:dup' is ambiguous" in out, \
        'the name collision itself is still worth a warning'
