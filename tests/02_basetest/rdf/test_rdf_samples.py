import os
#import sys
#import types
from pathlib import Path

from _setup_rdf import *


STANDALONE_RDFS = {
    "rdf_multiSection.rdf",   
    'rdf_big_pptx.rdf', 
    'rdf_report_simple.rdf'
}

CONTEXT_DEPENDENT_RDFS = {
    'rdf_big_docx.rdf': "Covered as part of report_input includes in test_report_input_with_includes", 
    "rdf_big_tool01.rdf": "checked from within the base above",
    'rdf_big_preparation02.rdf': "checked from within the base above", 
    "rdf_big_preparation01.rdf": "Included via loopfiles in test_report_input_with_includes",
    'rdf_big_preparation01sub.rdf': "checked from within the base above", 
    "rdf_big_instructions01.rdf": "Covered as part of report_input includes in test_report_input_with_includes",
    "rdf_big_instructions02.rdf": "Covered as part of report_input includes in test_report_input_with_includes",
    "rdf_repeatSection.rdf": "Specific behaviour asserted in test_repeat_section_generates_unique_addresses",
    "rdf_resource.rdf": "Requires manual datadir preparation beyond automated fixture scope",
    "rdf_testMarker.rdf": "Marker handling and datadir interaction tested in test_marker_behavior",
    }

@pytest.mark.parametrize("path_name", sorted(STANDALONE_RDFS))
def test_sample_rdfs(path_name: str):
    path = THIS_DIR / path_name
    rdf = parse_standalone_rdf(path)
    assert rdf.errors == []
    
def test_all_rdf_files_are_accounted_for():
    all_files = {p.name for p in THIS_DIR.glob("*.rdf")}
    accounted = STANDALONE_RDFS | set(CONTEXT_DEPENDENT_RDFS)
    missing = sorted(all_files - accounted)
    extra = sorted(accounted - all_files)
    assert not missing, f"Add coverage classification for new RDF samples: {missing}"
    assert not extra, f"Remove stale RDF classifications: {extra}"
