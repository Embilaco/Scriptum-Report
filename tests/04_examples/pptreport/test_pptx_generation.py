"""Pytest version of the former CreateDOCforEssay notebook."""

from pathlib import Path
import sys

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = Path(__file__).resolve().parent.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT)) 

from _setup_examples import *

module_path = Path(__file__).resolve().parent.parent.parent / '02_basetest' / 'common_case.py'

# Load the module from the given path
spec = importlib.util.spec_from_file_location('common_case', str(module_path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

CaseConfig = module.CaseConfig
run_pptx_case = module.run_pptx_case

def test_essay_document_is_created(tmp_path):
    print(f'\nWorking in {tmp_path}')
    config = CaseConfig(
        name="essay",
        case_dir=THIS_DIR,
        rdf_name="powerpoint_input.rdf",
        template_doc_name="template.pptx",
        output_name="final_report.pptx",
        include_patterns=["*.rdf", "template.pptx"],
        data_source_dir=DATA_SOURCE,
        finish=False,
        createpdf=True,
    )

    #print(tmp_path, os.curdir, os.getcwd())

    result_path = run_pptx_case(config, tmp_path)

    assert result_path.exists(), "Expected result_word.pptx to be generated"
    assert result_path.stat().st_size > 0, "Generated document should not be empty"
