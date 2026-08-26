"""Umlauts, accents and emoji pass through a slide fill unchanged.

The pptx twin of ``docx_basic/simple/test_docx_nonascii_fill.py``: a value
travels document -> loader -> task -> placeholder run, and nothing on the way
may re-encode it. The document title takes the same trip into the deck's core
properties. The block-scalar and UTF-8-series tests below mirror the docx
side line for line: the plain value route through a placeholder, ``|`` and
``>`` block forms, and the text-*file* route through the Material slide's
marker (the template-clone path, where the file is read as UTF-8 on every
platform).
"""

from pathlib import Path
import shutil
import sys

import pytest

pptx = pytest.importorskip('pptx')

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = THIS_DIR.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT))

from _setup_pptx_basic import *          # noqa: F401,F403

DOCUMENT = """_scriptum_:
  version: 4
  documenttype: pptx
  datadir: ./data
  documenttitle: 'Prüfbericht 🚀'
_content_:
  - TitleSlide:
      - title: 'Größenprüfung äöü ß'
      - subtitle: 'Résumé ✓ 100 € — naïve façade'
"""

#: The same series the yaml_loader and the docx twin pin. (No ASCII
#: apostrophes -- the fills wrap these in single quotes.)
UTF8_SERIES = [
    '„Gerade“ und ‚einfache‘ Anführungszeichen',
    '«Guillemets» und ‹einfache›',
    'Gedankenstrich — Halbgeviert – Ellipse …',
    'Accents: àâçéèêëîïôùûüÿ und ÄÖÜ äöü ß',
    'Symbols: © ® µ € £ § ½ ¼ ✓ ° ±',
    'Emoji: 😀 🚀 🔧 📊',
]

BLOCK_LINES = ['Erste Zeile — „gerade“ Anführung ✓',
               'Zweite Zeile ‚einfach‘ … 😀',
               'Dritte Zeile mit €-Zeichen']


def build(tmp_path, monkeypatch, document):
    import Scriptum

    shutil.copy(THIS_DIR / 'template.pptx', tmp_path)
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'series.txt').write_text('\n'.join(UTF8_SERIES),
                                                  encoding='utf-8')
    (tmp_path / 'case.yaml').write_text(document, encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    rdf = Scriptum.ReportDataFile('case.yaml')
    deck = Scriptum.ManagedPptx('template.pptx')
    deck.artist(rdf, directfill=True, globalfill=True,
                cleardust=True, setproperties=True)
    deck.remove_slide(0)
    deck.save('out.pptx', finish=False, createpdf=False)
    return pptx.Presentation('out.pptx')


def said(finished):
    """Whole text frames, breaks intact -- a multi-line fill spans
    paragraphs, which the run-by-run reading of the case tests cuts apart."""
    return [shape.text_frame.text
            for slide in finished.slides
            for shape in slide.shapes if shape.has_text_frame]


def test_nonascii_values_reach_the_deck_verbatim(tmp_path, monkeypatch):
    finished = build(tmp_path, monkeypatch, DOCUMENT)
    texts = said(finished)

    assert any('Größenprüfung äöü ß' in text for text in texts), texts
    assert any('Résumé ✓ 100 € — naïve façade' in text for text in texts), texts
    assert finished.core_properties.title == 'Prüfbericht 🚀'


@pytest.mark.parametrize('line', UTF8_SERIES)
def test_utf8_values_reach_the_deck_verbatim(line, tmp_path, monkeypatch):
    document = (DOCUMENT.rsplit('- subtitle:', 1)[0]
                + f"- subtitle: '{line}'\n")
    texts = said(build(tmp_path, monkeypatch, document))

    assert any(line in text for text in texts), (line, texts)


def test_a_block_scalar_fill_keeps_its_line_breaks(tmp_path, monkeypatch):
    """``|`` through a placeholder: the breaks arrive on the slide."""
    document = (DOCUMENT.rsplit('- subtitle:', 1)[0]
                + '- subtitle: |\n'
                + ''.join(f'          {line}\n' for line in BLOCK_LINES))
    texts = said(build(tmp_path, monkeypatch, document))

    assert any('\n'.join(BLOCK_LINES) in text for text in texts), texts


def test_a_folded_scalar_fill_arrives_as_one_line(tmp_path, monkeypatch):
    document = (DOCUMENT.rsplit('- subtitle:', 1)[0]
                + '- subtitle: >\n'
                + '          wrapped in the document,\n'
                + '          one line on the slide\n')
    texts = said(build(tmp_path, monkeypatch, document))

    assert any('wrapped in the document, one line on the slide' in text
               for text in texts), texts


def test_a_utf8_text_file_reaches_the_deck_line_by_line(tmp_path, monkeypatch):
    """The series through the file route: ``text:insert`` at the Material
    slide's marker clones the template's text block and fills it from the
    file, read as UTF-8 on every platform."""
    document = (DOCUMENT
                + '  - Material:\n'
                + '      - title: Reihe\n'
                + '      - marker:content:\n'
                + "          - text:insert: {file: series.txt, info: '—', more: '…'}\n")
    texts = said(build(tmp_path, monkeypatch, document))

    for line in UTF8_SERIES:
        assert any(line in text for text in texts), (line, texts)
