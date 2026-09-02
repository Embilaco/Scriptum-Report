"""Placeholders inside a text block: what a document may write into one.

A ``text:`` block in ``section:template`` is a piece of prose the template
carries — several paragraphs, kept together — and a document adds it at a
marker. Its **placeholders** are the tags standing inside it, and they are
what a document supplies::

    <text:complex>                          - text:complex:
    We may add more complex texts with          placeholder:one: a first one
    a <placeholder:one/> or a                   placeholder:two: {file: title.txt}
    <placeholder:two/>
    or further text with more targets…
    </text:complex>

They arrive as the fill's **modifiers** and are matched to the tags by the
name the template spells — the mechanism ``DocImageBlockElement`` already
used for its ``description``. Both spellings work: namespaced
(``<placeholder:one/>``) and bare (``<subtitle/>``).

What was decided, 2026-08-31
----------------------------
* **The mapping needs no source key** when the address is a ``text:`` one.
  A text block carries its own text, so there is nothing for ``file:`` or
  ``text:`` to name; the placeholders *are* the value. Every other namespace
  keeps the rule and the diagnostic — for an image a missing source really
  is the mistake it exists to catch.
* **Both naming forms**, because the match is on the tag's puretag and
  costs nothing either way. Namespaced is the safer habit: a bare name
  shares its space with the source keys and the length modifiers.
* **An unmentioned placeholder is blanked**, not warned about. A text block
  is prose, and prose with a visible ``<placeholder:two/>`` in it is worse
  than prose without the slot.

The shipped case (``word_text.yaml`` against ``template.docx``) exercises the
namespaced form end to end, one placeholder plain and one from a file; the
templates built here cover what it cannot express.
"""

from pathlib import Path
import sys

import pytest

docx = pytest.importorskip('docx')

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = THIS_DIR.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT))

from _setup_docx_basic import *          # noqa: F401,F403  (brings reset_state, os)

HEADER = ('_scriptum_:\n'
          '  version: 4\n'
          '  documenttype: docx\n'
          '  datadir: .\n'
          '_content_:\n')


def template(*slots):
    """A section with a marker, and a text block carrying *slots*."""
    document = docx.Document()
    document.add_paragraph('<section:main>MAIN')
    document.add_paragraph('<marker:content/>')
    document.add_section()
    # A section ends with its break paragraph, and that paragraph must carry
    # the closing tag -- nothing may sit between the two.
    document.paragraphs[-1].text = '</section:main>'
    document.add_paragraph('<section:template>')
    document.add_paragraph('<text:block>')
    document.add_paragraph('opening line')
    for slot in slots:
        document.add_paragraph(f'a {slot} here')
    document.add_paragraph('closing line')
    document.add_paragraph('</text:block>')
    document.add_paragraph('</section:template>')
    return document


def generate(tmp_path, entry, *slots):
    """Add ``text:block`` at the marker with *entry* under it."""
    import Scriptum

    template(*slots).save(tmp_path / 'built.docx')
    (tmp_path / 'notes.txt').write_text('from a file', encoding='utf-8')
    (tmp_path / 'case.yaml').write_text(
        HEADER + '  - section:main:\n      - marker:content:\n' + entry,
        encoding='utf-8')

    os.chdir(tmp_path)
    rdf = Scriptum.ReportDataFile('case.yaml')
    assert not rdf.errors, rdf.errors
    managed = Scriptum.ManagedDocx('built.docx', rdf)
    managed.typesetting(rdf)
    managed.save('out.docx')

    return [p.text.strip() for p in docx.Document('out.docx').paragraphs
            if p.text.strip()]


# ------------------------------------------------------------ the mechanism

def test_a_placeholder_takes_what_the_document_names_it(tmp_path):
    """Namespaced and bare, side by side, matched by the tag's own name."""
    said = generate(tmp_path,
                    '          - text:block:\n'
                    '              placeholder:one: FIRST\n'
                    '              subtitle: SECOND\n',
                    '<placeholder:one/>', '<subtitle/>')

    assert said == ['MAIN',
                    'opening line',
                    'a FIRST here',
                    'a SECOND here',
                    'closing line']


def test_a_placeholder_can_come_from_a_file(tmp_path):
    """A modifier carrying ``{file: ...}`` renders the file's **content**.

    It used to render nothing: a file value stringifies to '' until it is
    loaded, and the loop that writes a modifier wrote only ``str(value)``.
    What a value says beyond its string form now lives in one place --
    ``renderedText`` -- which both this and a plain fill go through.
    """
    said = generate(tmp_path,
                    '          - text:block:\n'
                    '              placeholder:one: {file: notes.txt}\n',
                    '<placeholder:one/>')

    assert said == ['MAIN', 'opening line', 'a from a file here', 'closing line']


def test_a_missing_file_says_so_in_the_placeholder(tmp_path):
    """The same message a plain fill gives, in the same words, because it is
    the same code saying it."""
    said = generate(tmp_path,
                    '          - text:block:\n'
                    '              placeholder:one: {file: nowhere.txt}\n',
                    '<placeholder:one/>')

    assert any(line.startswith('a file ') and 'not found' in line
               for line in said), said


def test_an_unmentioned_placeholder_is_blanked(tmp_path):
    """Decided: blanked, not warned about. The prose closes over the gap and
    the markup does not ship."""
    said = generate(tmp_path,
                    '          - text:block:\n'
                    '              placeholder:one: ONLY\n',
                    '<placeholder:one/>', '<placeholder:two/>')

    assert said == ['MAIN',
                    'opening line',
                    'a ONLY here',
                    'a  here',           # the slot blanked, no markup left
                    'closing line']
    assert not any('placeholder' in line for line in said)


def test_the_closing_tag_does_not_ship(tmp_path, capsys):
    """``</text:block>`` used to survive as literal text at the end of every
    added block: ``copy()`` dropped the inner tags, so nothing was left to
    pair the close with, and ``clean()`` was a ``pass``."""
    said = generate(tmp_path,
                    '          - text:block:\n'
                    '              placeholder:one: X\n',
                    '<placeholder:one/>')

    assert not any('<' in line or '>' in line for line in said), said
    assert 'WARNING' not in capsys.readouterr().out


def test_a_value_written_at_the_block_says_it_goes_nowhere(tmp_path, capsys):
    """`- text:block: some words` has nowhere to put the words.

    The paragraphs are the template's; only the placeholders inside them are
    the document's to fill. The loader cannot catch this -- it never sees the
    template, so it cannot know the address is a block rather than a plain
    `<text:green/>`, where the very same line is right -- so the back end
    says it, and names the placeholders the block actually has.

    Silence was the alternative and the wrong one: dropping what an author
    wrote is the failure mode this format exists to end, and the mistake is
    nearly always that a placeholder was meant.
    """
    said = generate(tmp_path, '          - text:block: some words\n',
                    '<placeholder:one/>')
    out = capsys.readouterr().out

    complaint = [line for line in out.splitlines() if 'written nowhere' in line]
    assert len(complaint) == 1, out
    assert complaint[0].startswith('WARNING:'), 'a slip, and there was a slot'
    assert "'text:block'" in complaint[0], 'it names the block'
    assert "'some words'" in complaint[0], 'and quotes what was dropped'
    assert 'placeholder:one' in complaint[0], 'and lists where it could have gone'

    # the block still arrives, and its slot is blanked as any unfilled one is
    assert said == ['MAIN', 'opening line', 'a  here', 'closing line']


def test_a_block_with_no_placeholders_reports_it_as_INFO(tmp_path, capsys):
    """The same words going nowhere, but nothing the author could have done.

    A block with no placeholders is prose the template owns entire, and
    writing a value at it is the **only** way to add it at a marker: an
    entry needs a value, and neither `- text:block:` nor `- text:block: {}`
    is accepted (docs/rdf.md, current limitation). So the value going
    nowhere is expected rather than a mistake, and the run says so at INFO
    -- where the block *has* slots and one of them was meant, it is still a
    WARNING naming them.

    ``text:prefilled`` in the shipped ``word_text.yaml`` is this case end to
    end.
    """
    said = generate(tmp_path, '          - text:block: some words\n')
    out = capsys.readouterr().out

    note = [line for line in out.splitlines() if 'written nowhere' in line]
    assert len(note) == 1, out
    assert note[0].startswith('INFO:'), note[0]
    assert "'text:block'" in note[0], 'it still names the block'
    assert "'some words'" in note[0], 'and still quotes what was dropped'
    assert 'WARNING' not in note[0]

    # and the block arrives whole, which is the point of writing it that way
    assert said == ['MAIN', 'opening line', 'closing line']


def test_a_source_key_at_the_block_says_the_same(tmp_path, capsys):
    """Not only a scalar: `{file: ...}` written at the block is the same
    mistake, and the message quotes an excerpt of what would have landed."""
    said = generate(tmp_path, '          - text:block: {file: notes.txt}\n',
                    '<placeholder:one/>')
    out = capsys.readouterr().out

    assert any('written nowhere' in line and 'from a file' in line
               for line in out.splitlines()), out


def test_the_right_shape_says_nothing(tmp_path, capsys):
    """The control: placeholders only, and the run is quiet."""
    generate(tmp_path,
             '          - text:block:\n              placeholder:one: X\n',
             '<placeholder:one/>')

    assert 'WARNING' not in capsys.readouterr().out


# ------------------------------------------------------------- the grammar

def test_a_text_block_needs_no_source_key(tmp_path):
    """The one relaxation: a ``text:`` address may be all modifiers, because
    the block already carries its text and there is nothing to source."""
    said = generate(tmp_path,
                    '          - text:block:\n'
                    '              placeholder:one: NO SOURCE NEEDED\n',
                    '<placeholder:one/>')

    assert 'a NO SOURCE NEEDED here' in said


def test_every_other_namespace_still_needs_one(tmp_path):
    """The diagnostic stays exact where it earns its keep: an image with no
    file is the mistake this message exists to catch, and it still says so."""
    import Scriptum
    from Scriptum.rdf.loader import DocumentError

    template().save(tmp_path / 'built.docx')
    (tmp_path / 'case.yaml').write_text(
        HEADER + '  - section:main:\n      - marker:content:\n'
        '          - image:generic: {width: 9cm}\n', encoding='utf-8')
    os.chdir(tmp_path)

    with pytest.raises(DocumentError) as caught:
        Scriptum.ReportDataFile('case.yaml')

    assert 'a value needs one source key' in str(caught.value)


def test_a_text_address_with_neither_source_nor_modifier_still_refuses(tmp_path):
    """An empty mapping says nothing at all, and the relaxation does not make
    it mean something."""
    import Scriptum
    from Scriptum.rdf.loader import DocumentError

    template().save(tmp_path / 'built.docx')
    (tmp_path / 'case.yaml').write_text(
        HEADER + '  - section:main:\n      - marker:content:\n'
        '          - text:block: {}\n', encoding='utf-8')
    os.chdir(tmp_path)

    with pytest.raises(DocumentError):
        Scriptum.ReportDataFile('case.yaml')
