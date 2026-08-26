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
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path

# import os, ipdb

# def debug_hook(exc_type, exc_value, traceback):
#     if exc_type is KeyboardInterrupt:
#         sys.__excepthook__(exc_type, exc_value, traceback)
#         return
#     print(f"Uncaught exception: {exc_type.__name__}: {exc_value}")
#     ipdb.post_mortem(traceback)

# if True or os.environ.get('DEBUG'): sys.excepthook = debug_hook

# The number itself lives in version.py, a leaf the back ends may read --
# they stamp it into document properties and must not import this package.
from .version import version, __version__

licenses = [ 'SPDX-Identifier: PolyForm-Noncommercial-1.0.0', 'SPDX-Identifier: LicenseRef-SCRIPTUM-Commercial' ]

_PACKAGE_ROOT = Path(__file__).resolve().parent
_PROJECT_ROOT = _PACKAGE_ROOT.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.append(str(_PROJECT_ROOT))

# all the enduser requires is this:
from .rdf.reportDataFile import ReportDataFile

__all__ = ['ReportDataFile', 'ManagedDocx', 'ManagedPptx',
           'version', '__version__', 'licenses']

# The back ends load lazily (PEP 562): importing Scriptum touches neither
# python-docx nor python-pptx, so the core -- reading report documents --
# works with either library absent or broken. The first access to
# ManagedDocx/ManagedPptx imports its back end; with the library missing
# that access raises a ModuleNotFoundError naming the package to install.
_BACKENDS = {
    'ManagedDocx': ('python-docx', '._docx.reportDocx'),
    'ManagedPptx': ('python-pptx', '._pptx.reportPptx'),
}


def __getattr__(name):
    if name in _BACKENDS:
        distribution, source = _BACKENDS[name]
        try:
            attribute = getattr(import_module(source, __name__), name)
        except Exception as error:
            raise ModuleNotFoundError(
                f'{name} needs {distribution}, which did not load '
                f'(pip install {distribution}): {error}') from error
        globals()[name] = attribute
        return attribute
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def __dir__():
    return sorted(set(globals()) | set(_BACKENDS))


# A tool with no back end at all makes no sense: without both libraries it
# can read report documents but generate nothing, and someone should hear
# about that once, at import, not per attribute. A probe that raises counts
# as unavailable -- broken metadata is as unusable as absence.
def _importable(module):
    try:
        return find_spec(module) is not None
    except Exception:
        return False


if not _importable('docx') and not _importable('pptx'):
    print('WARNING: neither python-docx nor python-pptx is installed -- '
          'Scriptum can read report documents but cannot generate anything. '
          'Install python-docx and/or python-pptx.')

__path__ = [str(_PACKAGE_ROOT)]

del _PACKAGE_ROOT
del _PROJECT_ROOT
del Path
del sys
# import_module stays: __getattr__ needs it whenever a back end first loads
del find_spec
del _importable
