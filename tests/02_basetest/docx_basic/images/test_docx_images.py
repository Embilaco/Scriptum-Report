"""Pytest version of the former CreateDOCforEssay notebook."""

from pathlib import Path
import shutil
import sys

import docx
from docx.oxml.ns import qn
from docx.shared import Cm

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = Path(__file__).resolve().parent.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT)) 

from _setup_docx_basic import *
from common_case import CaseConfig, run_docx_case


def build(tmp_path, template='template.docx', case_dir=THIS_DIR):
    """The images case, typeset with *template* from *case_dir*."""
    config = CaseConfig(
        name="report",
        case_dir=case_dir,
        document_name="word_images.yaml",
        template_doc_name=template,
        output_name="final_report.docx",
        include_patterns=["*.yaml", template],
        data_source_dir=DATA_SOURCE,
        finish=False,
        createpdf=False,
    )
    return run_docx_case(config, tmp_path)


def pictures(paragraph):
    """(width, height) in cm of every inline picture in *paragraph*."""
    return [(round(int(e.get('cx')) / Cm(1), 2), round(int(e.get('cy')) / Cm(1), 2))
            for e in paragraph._p.iter(qn('wp:extent'))]


def test_document_is_created(tmp_path):
    print(f'\nWorking in {tmp_path}')

    result_path = build(tmp_path)

    assert result_path.exists(), "Expected final_report.docx to be generated"
    assert result_path.stat().st_size > 0, "Generated document should not be empty"


def test_global_image_fills_place_their_pictures(tmp_path):
    """``_global_`` holds ``image:allover`` (8 mm high) and ``image:header``
    (1 cm). The template tags the first in both body sections and in the
    footer, the second in the header, next to direct fills that were always
    fine. Pinned on the drawings, not the text: the global image branch once
    compared the element's canonical address with the puretag it was asked
    for, matched nothing, and every one of these paragraphs stayed empty --
    which a comparison of paragraph texts cannot see.
    """
    document = docx.Document(build(tmp_path))

    allover = [p for p in document.paragraphs if p.text.startswith('ALLOVER')]
    assert len(allover) == 2, 'one ALLOVER paragraph per body section'
    assert [pictures(p) for p in allover] == [[(0.8, 0.8)], [(0.8, 0.8)]]

    first = document.sections[0]
    header, footer = first.header.paragraphs, first.footer.paragraphs
    assert pictures(header[0]) == [(1.0, 1.0)], '<image:header width=1cm/> at 1 cm high'
    assert header[1].text == 'Here comes the header'
    assert pictures(footer[0]) == [(1.0, 1.5)], 'the direct image:footer fill, 1.5 cm high'
    assert footer[1].text.startswith('Here comes the footer')
    assert pictures(footer[1]) == [(0.8, 0.8)], 'image:allover in the footer'

    left_over = [p.text for p in document.paragraphs + header + footer if '<image:' in p.text]
    assert not left_over


def test_a_header_shared_by_linked_sections_gets_its_picture_once(tmp_path):
    """A section whose header and footer are linked to the previous one reads
    the same paragraphs, so a global fill meets each of them once per section.
    The first visit places the picture and consumes the tag; the second finds
    no tag and has to leave the paragraph alone instead of failing on the run
    it did not get.
    """
    case = tmp_path / 'case'
    case.mkdir()
    shutil.copy(THIS_DIR / 'word_images.yaml', case)
    template = docx.Document(THIS_DIR / 'template.docx')
    template.sections[1].header.is_linked_to_previous = True
    template.sections[1].footer.is_linked_to_previous = True
    template.save(case / 'linked.docx')

    document = docx.Document(build(tmp_path, 'linked.docx', case))

    assert all(s.header.is_linked_to_previous for s in document.sections[1:])
    first = document.sections[0]
    assert pictures(first.header.paragraphs[0]) == [(1.0, 1.0)]
    assert pictures(first.footer.paragraphs[1]) == [(0.8, 0.8)]
    allover = [p for p in document.paragraphs if p.text.startswith('ALLOVER')]
    assert [pictures(p) for p in allover] == [[(0.8, 0.8)], [(0.8, 0.8)]]
