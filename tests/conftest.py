"""Make the per-directory test helpers importable from anywhere in the suite.

Why this file exists
--------------------
Every test directory used to carry a helper named ``_local_test_setup.py`` and
each test did ``from _local_test_setup import *``.

None of the test directories can be Python packages -- ``02_basetest`` starts
with a digit and ``pptx-basic`` contains a hyphen, so neither is a valid
identifier. Without packages, pytest imports every test module as a top-level
module and all seven helpers competed for the single name
``_local_test_setup``. Only the first one imported ever reached
``sys.modules``; every later ``from _local_test_setup import *`` silently bound
*that* module instead of the sibling one, so directory-specific names such as
``THIS_DIR`` and ``SETTINGS`` were simply missing.

The symptom was order-dependent: a directory passed when run on its own and
failed as part of the full suite.

The helpers now have unique names (``_setup_rdf``, ``_setup_values``, ...), so
they can no longer shadow one another. This file adds each helper's directory
to ``sys.path`` so a test can import its helper regardless of how deeply it is
nested -- several live a level or two below the helper they use.

The repository root is added as well, so ``import Scriptum`` and
``from tests.baseTestRoot import *`` resolve without depending on the current
working directory.
"""

import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TESTS_ROOT.parent


def _prepend(path: Path) -> None:
    entry = str(path)
    if entry not in sys.path:
        sys.path.insert(0, entry)


_prepend(REPO_ROOT)

for _helper in sorted(TESTS_ROOT.rglob("_setup_*.py")):
    _prepend(_helper.parent)
