#!/usr/bin/env python3
# coding: utf-8
#
#   ___   ___  ____  ____  ____  ____  __  __  __  __ 
#  / __) / __)(  _ \(_  _)(  _ \(_  _)(  )(  )(  \/  )
#  \__ \( (__  )   / _)(_  )___/  )(   )(__)(  )    ( 
#  (___/ \___)(_)\_)(____)(__)   (__) (______)(_/\/\_)
#
#

# Origin:
#   from latin Scriptum "written", participle perfect to scribere "write"

# collect classes and functions to create reports
# based on a template and the python-docx and python-pptx packages
#
# for details on 
# python-docx see https://python-docx.readthedocs.io
# python-pptx see https://python-pptx.readthedocs.io
# openxml by Microsoft see http://officeopenxml.com/ 
#
# by  temmel007@gmail.com
# 2020-2026

# License, see licenses and LICENSE.md
#

import sys
from pathlib import Path

# import os, ipdb

# def debug_hook(exc_type, exc_value, traceback):
#     if exc_type is KeyboardInterrupt:
#         sys.__excepthook__(exc_type, exc_value, traceback)
#         return
#     print(f"Uncaught exception: {exc_type.__name__}: {exc_value}")
#     ipdb.post_mortem(traceback)

# if True or os.environ.get('DEBUG'): sys.excepthook = debug_hook

__version__ = "2.0.0"
version = __version__

licenses = [ 'SPDX-Identifier: PolyForm-Noncommercial-1.0.0', 'SPDX-Identifier: LicenseRef-SCRIPTUM-Commercial' ]

_PACKAGE_ROOT = Path(__file__).resolve().parent
_PROJECT_ROOT = _PACKAGE_ROOT.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.append(str(_PROJECT_ROOT))

# all the enduser requires is this:
from .rdf.reportDataFile import ReportDataFile

__all__ = ['ReportDataFile', 'version', '__version__', 'licenses']

# and this
try:  
    from ._docx.reportDocx import ManagedDocx  # type: ignore
except Exception as e:  
    print(f'Skip docx generation, package import failed: \n    {e}')
else:
    __all__.append('ManagedDocx')

# and this
try:  
    from ._pptx.reportPptx import ManagedPptx  # type: ignore
except Exception as e:  
    print(f'Skip pptx generation, package import failed \n    {e}')
else:
    __all__.append('ManagedPptx')

# do we need to react when we cannot import both of them?

__path__ = [str(_PACKAGE_ROOT)]

del _PACKAGE_ROOT
del _PROJECT_ROOT
del Path
del sys
