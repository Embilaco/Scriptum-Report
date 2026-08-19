# basic setup for all tests in that folder

COVERAGE = 'RDF'

import importlib.util
from pathlib import Path
import sys, os
import types
#import shutil

# Define the full path of the module
module_path = Path(__file__).resolve().parent.parent.parent / 'baseTestRoot.py'

# Load the module from the given path
spec = importlib.util.spec_from_file_location('baseTestRoot', str(module_path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Add the module to sys.modules
sys.modules['baseTestRoot'] = module

from tests.baseTestRoot import *

THIS_DIR = Path(__file__).resolve().parent

import Scriptum.rdf.reportDataFile as rdf_module # pyright: ignore[reportMissingImports]
from Scriptum.rdf.settings import SETTINGS # pyright: ignore[reportMissingImports]

# Replace logging with a stub to avoid issues during tests
class DummyLog:
    def __init__(self, task, comment=False):
        self.fullLine = str(task)
    def __repr__(self):
        return self.fullLine

rdf_module.LogTask = DummyLog

rdf_module._test_debug = True

def parse_with_root(path: Path):
    """Parse helper for rdf files without documenttype line."""
    settings = SETTINGS()
    settings.version = 100
    settings.documenttype = "pptx"
    orig_update = ReportDataFile.updateRoot
    ReportDataFile.updateRoot = lambda self, i, line: setattr(self, "_currentroot", line.lower().split("."))
    try:
        rdf = ReportDataFile(str(path), _root=["section"], _settings=settings)
    finally:
        ReportDataFile.updateRoot = orig_update
    return rdf

def determine_document_type(path: Path) -> str | None:
    for line in path.read_text().splitlines():
        if line.lower().startswith("*documenttype="):
            return line.split("=", 1)[1].strip().lower()
    return None

def parse_standalone_rdf(path: Path):
    doc_type = determine_document_type(path)
    cwd = os.getcwd()
    original_update = ReportDataFile.updateRoot
    try:
        os.chdir(path.parent)
        if doc_type:
            return ReportDataFile(path.name)

        settings = SETTINGS()
        settings.version = 100
        settings.documenttype = "pptx"
        settings.datadir = str(DATA_SOURCE)

        ReportDataFile.updateRoot = lambda self, i, line: setattr(self, "_currentroot", line.lower().split("."))
        return ReportDataFile(path.name, _root=["section"], _settings=settings)
    finally:
        os.chdir(cwd)
        ReportDataFile.updateRoot = original_update

