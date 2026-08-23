"""Pytest version of the former CreateDOCforEssay notebook."""

from pathlib import Path
import sys

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = Path(__file__).resolve().parent.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT)) 

from _setup_docx_basic import *
from common_case import CaseConfig, run_docx_case

def test_document_is_created(tmp_path):
    print(f'\nWorking in {tmp_path}')
    config = CaseConfig(
        name="report",
        case_dir=THIS_DIR,
        document_name="word_images.yaml",
        template_doc_name="template_image.docx",
        output_name="final_report.docx",
        include_patterns=["*.yaml", "template_image.docx"],
        data_source_dir=DATA_SOURCE,
        finish=False,
        createpdf=False,
    )

    #print(tmp_path, os.curdir, os.getcwd())

    result_path = run_docx_case(config, tmp_path)

    assert result_path.exists(), "Expected final_report.docx to be generated"
    assert result_path.stat().st_size > 0, "Generated document should not be empty"
