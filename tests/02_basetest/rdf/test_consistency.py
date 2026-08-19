#import os
from pathlib import Path
import sys
#import types
#import pytest
from _setup_rdf import *

# # create stubs for optional dependencies
# pptx_stub = types.ModuleType('pptx')
# pptx_util = types.ModuleType('pptx.util')
# pptx_util.Pt = pptx_util.Cm = pptx_util.Mm = pptx_util.Inches = lambda x: x
# pptx_stub.util = pptx_util
# sys.modules['pptx'] = pptx_stub
# sys.modules['pptx.util'] = pptx_util

# docx_stub = types.ModuleType('docx')
# docx_oxml = types.ModuleType('docx.oxml')
# docx_ns = types.ModuleType('docx.oxml.ns')
# docx_ns.qn = lambda x: x
# docx_oxml.ns = docx_ns
# docx_shared = types.ModuleType('docx.shared')
# docx_shared.Inches = docx_shared.Pt = docx_shared.Cm = docx_shared.Mm = lambda x: x
# docx_stub.oxml = docx_oxml
# docx_stub.shared = docx_shared
# sys.modules['docx'] = docx_stub
# sys.modules['docx.oxml'] = docx_oxml
# sys.modules['docx.oxml.ns'] = docx_ns
# sys.modules['docx.shared'] = docx_shared

# def test_duplicate_path_detected(tmp_path: Path):
#     content = """*version=100
# *documenttype=docx
# section:load_bc
# .foo='1'
# .foo='2'
# """
#     f = write(tmp_path, 'dup.rdf', content)
#     rdf = ReportDataFile(str(f))
#     errors = rdf.errors
#     print(errors)
#     assert any('duplicate path' in e.lower() for e in errors)

def test_duplicate_settings_across_includes(tmp_path: Path):
    child = """*version=100
*documenttype=docx
global
.bar='1'
"""
    child_f = write(tmp_path, 'child.rdf', child)
    root = f"""&include=file:{child_f}
*version=99
*documenttype=pptx
global
.foo='1'
"""
    root_f = write(tmp_path, 'root.rdf', root)
    with pytest.raises(Exception) as exc_info:
        ReportDataFile(str(root_f))
    assert 'Global setting *version defined more than once' in str(exc_info.value)
    assert 'Global setting *documenttype defined more than once' in str(exc_info.value)

def test_unique_definitions_pass(tmp_path: Path):
    content = """*version=100
*documenttype=docx
section:load_bc
.foo='1'
.bar='2'
"""
    f = write(tmp_path, 'unique.rdf', content)
    rdf = ReportDataFile(str(f))
    errors = rdf.errors
    assert errors == []

def test_correct_sectioning_docx(tmp_path: Path):
    content = """*version=100
*documenttype=docx
# wrong since ':' missing and section:foo.subsection:bar not there
mysection.load_bc
.foo='1'
.bar='2'
"""
    f = write(tmp_path, 'section.rdf', content)
    rdf = ReportDataFile(str(f),_root=[])
    assert any("section 'mysection', line 4 is not in allowed order:" in e for e in rdf.errors)
    assert any("section 'load_bc', line 4 is not in allowed order:" in e for e in rdf.errors)

def test_correct_sectioning_pptx(tmp_path: Path):
    content = """*version=100
*documenttype=pptx
# partially possible in pptx - is it useful too?
mysection.load_bc
.foo='1'
.bar='2'
"""
    f = write(tmp_path, 'section.rdf', content)
    rdf = ReportDataFile(str(f),_root=[])
    assert any("section naming 'load_bc', line 4 is not in allowed namespace" in e for e in rdf.errors)
