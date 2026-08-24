"""Shared helpers for the rdf package."""

import os
from typing import Tuple


def getCorrectFile(name: str, relative: bool = False, datadir: str = '.') -> Tuple[str, bool]:
    """Find the correct file, optionally considering relative paths."""
    exists = False
    if name == os.path.abspath(name):
        name = os.path.normpath(os.path.join(datadir, name))
        if os.path.exists(name):
            exists = True
    else:
        if relative and os.path.exists(name):
            exists = True
        else:
            name = os.path.normpath(os.path.join(datadir, name))
            exists = os.path.exists(name)
    return name, exists


