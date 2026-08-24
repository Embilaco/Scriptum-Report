"""Guard the dependency direction between Scriptum's packages.

``rdf``, ``tag`` and ``element`` are leaves: they are meant to be usable on
their own, and nothing in them may reach for a back end. The rule exists
because breaking it is cheap, local and silent -- one convenient
``from .._docx import ...`` inside ``rdf`` drags python-docx into every
parse, which is what previously made ``import Scriptum`` fail outright when
only one of the two Office libraries was installed, instead of degrading to
whichever back end was available.

Nothing else detects that regression: the suite still passes, because the
developer who introduces it has both libraries installed.

This inspects the source with :mod:`ast` rather than the running program, so:

* it sees imports nested inside functions and ``if TYPE_CHECKING:`` blocks --
  ``_docx/structure.py`` deliberately defers imports into methods, and a
  "read the top of the file" check would miss every one of them;
* it never executes anything, so it still runs where the Office libraries
  are absent;
* prose is not code. Grepping for "rdf" also matches the word in a
  docstring, which is the false positive that motivated doing this properly.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

#: Package -> the Scriptum packages it may import from. Empty means leaf.
LAYERS = {
    'rdf': frozenset(),
    'tag': frozenset(),
    'element': frozenset({'tag'}),
}

SCRIPTUM_PACKAGES = {'rdf', 'tag', 'element', '_docx', '_pptx'}

#: Reaching the root package is a violation in itself: importing ``Scriptum``
#: runs its ``__init__``, which pulls in the back ends.
ROOT = 'Scriptum'


def _find_source_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / 'Scriptum' / '__init__.py').is_file():
            return parent / 'Scriptum'
    return None


SOURCE_ROOT = _find_source_root()

pytestmark = pytest.mark.skipif(
    SOURCE_ROOT is None,
    reason='Scriptum sources are not next to the tests (installed package?)',
)


def _package_parts(py: Path) -> list:
    """Dotted parts of the package containing this module, rooted at Scriptum.

    An ``__init__.py`` *is* its package; any other module belongs to the
    directory holding it. Relative imports are resolved against this.
    """

    rel = py.relative_to(SOURCE_ROOT.parent)
    parts = list(rel.with_suffix('').parts)
    return parts[:-1]


def _resolve_relative(package_parts: list, level: int, module) -> list:
    """Absolute dotted parts that a relative import resolves to."""

    cut = len(package_parts) - (level - 1)
    base = list(package_parts[:cut]) if cut > 0 else []
    if module:
        base = base + module.split('.')
    return base


def _targets_of(node, package_parts: list) -> set:
    """Scriptum packages an import statement reaches.

    Says nothing about whether reaching them is allowed -- that is the
    caller's decision.
    """

    found = set()

    def _from_names(names):
        for alias in names:
            head = alias.name.split('.')[0]
            found.add(head if head in SCRIPTUM_PACKAGES else ROOT)

    if isinstance(node, ast.ImportFrom) and node.level:
        resolved = _resolve_relative(package_parts, node.level, node.module)
        if not resolved or resolved[0] != ROOT:
            return found                      # left Scriptum entirely
        if len(resolved) > 1:
            found.add(resolved[1])
        else:
            _from_names(node.names)           # `from .. import x`
        return found

    if isinstance(node, ast.ImportFrom):      # level 0 -> absolute
        parts = (node.module or '').split('.')
        if parts[0] != ROOT:
            return found
        if len(parts) > 1:
            found.add(parts[1])
        else:
            _from_names(node.names)
        return found

    if isinstance(node, ast.Import):
        for alias in node.names:
            parts = alias.name.split('.')
            if parts[0] == ROOT:
                found.add(parts[1] if len(parts) > 1 else ROOT)

    return found


def escapes_in_source(source: str, package_parts: list, package: str) -> set:
    """Scriptum packages reached from *source*, excluding *package* itself."""

    reached = set()
    for node in ast.walk(ast.parse(source)):
        reached |= _targets_of(node, package_parts)
    return {target for target in reached if target != package}


def _violations(package: str) -> list:
    allowed = LAYERS[package]
    problems = []
    for py in sorted((SOURCE_ROOT / package).rglob('*.py')):
        if '__pycache__' in py.parts:
            continue
        package_parts = _package_parts(py)
        for node in ast.walk(ast.parse(py.read_text(encoding='utf-8'))):
            for target in _targets_of(node, package_parts):
                if target == package or target in allowed:
                    continue
                rel = py.relative_to(SOURCE_ROOT.parent)
                problems.append(f'{rel}:{node.lineno} reaches {target!r}')
    return problems


@pytest.mark.parametrize('package', sorted(LAYERS))
def test_package_stays_within_its_layer(package):
    """A leaf package must not import a back end, directly or otherwise."""

    problems = _violations(package)
    allowed = ', '.join(sorted(LAYERS[package])) or 'nothing'
    assert not problems, (
        f'Scriptum/{package} may import from {allowed}, but:\n  '
        + '\n  '.join(problems)
        + f'\n\nIf {package} genuinely needs this, move what it needs into '
          f'{package} and let the other package read it from there -- '
          'rdf/namespaces.py is the precedent.'
    )


# ---------------------------------------------------------------------------
# The guard needs its own guard. A detector that quietly matches nothing
# would keep passing while the rule it protects rots away.

@pytest.mark.parametrize(
    'source, package_parts, package, expected',
    [
        # the exact import that used to break graceful degradation
        ('from .._docx import docx_sections', ['Scriptum', 'rdf'], 'rdf', {'_docx'}),
        # same dot count, deeper file: stays inside the package
        ('from ..common import getCorrectFile', ['Scriptum', 'rdf', 'values'], 'rdf', set()),
        # absolute forms -- the blind spot of a purely dot-counting check
        ('from Scriptum._pptx import pptx_sections', ['Scriptum', 'rdf'], 'rdf', {'_pptx'}),
        ('import Scriptum._docx', ['Scriptum', 'rdf'], 'rdf', {'_docx'}),
        # `from .. import name`, where node.module is None
        ('from .. import _docx', ['Scriptum', 'rdf'], 'rdf', {'_docx'}),
        # touching the root package runs its __init__ and pulls in everything
        ('from .. import version', ['Scriptum', 'rdf'], 'rdf', {ROOT}),
        # legitimate intra-package and cross-leaf imports
        ('from .base import Element', ['Scriptum', 'element'], 'element', set()),
        ('from ..tag.tag import Tag', ['Scriptum', 'element'], 'element', {'tag'}),
        # third-party imports are none of this test's business
        ('from docx.oxml.ns import qn', ['Scriptum', '_docx'], '_docx', set()),
        # nesting must not hide anything
        ('def f():\n    from .._pptx import x', ['Scriptum', 'rdf'], 'rdf', {'_pptx'}),
        ('if TYPE_CHECKING:\n    from ..rdf.values import Table',
         ['Scriptum', 'element'], 'element', {'rdf'}),
    ],
)
def test_detector_finds_what_it_claims(source, package_parts, package, expected):
    """Without this, a broken detector would report a clean codebase."""

    assert escapes_in_source(source, package_parts, package) == expected
