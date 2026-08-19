# basic setup for all tests in that folder

COVERAGE = 'VALUES'

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

