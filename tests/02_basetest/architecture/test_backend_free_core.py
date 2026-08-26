"""The core works with either Office library absent -- and says so.

The back ends are optional at run time: ``import Scriptum`` touches neither
python-docx nor python-pptx (both load lazily on first attribute access),
reading a report document works with neither installed, and a missing
library names itself -- with its pip install line -- at the point of use,
never as a bare AttributeError. Only when BOTH libraries are gone does the
import say anything: a tool with no back end at all can read documents but
generate nothing, and that is worth one warning, once, at import.

The everyday suite cannot see any of this: the venvs always carry both
libraries, so an eager ``import docx`` reintroduced anywhere would keep
passing for the developer who wrote it (the same blindness test_layering
documents). Hence two kinds of check:

* **Shape, with ast.** A test module that touches a back end at module
  level -- ``docx``, ``pptx``, or ``Scriptum._docx``/``Scriptum._pptx``,
  whose import drags the library in -- must first declare the need with a
  module-level ``pytest.importorskip`` for that library. That declaration
  is what turns a missing library into cleanly skipped back-end tests
  instead of collection errors, and it is per-library: a Word case must
  not need python-pptx, nor the other way round. Function-level imports
  pass, exactly as in the win32com guard.
* **Behaviour, in subprocesses.** A meta-path finder refuses docx/pptx no
  matter what is installed, and the child process demonstrates the core
  promise end to end: silent import, a parsed document, the named error
  on the missing back end, the working class on the present one.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = TESTS_ROOT.parent

LIBRARIES = ('docx', 'pptx')

#: Import targets that drag a library in: the library itself, or the
#: Scriptum back-end package built on it.
PACKAGE_OF = {'docx': 'docx', 'pptx': 'pptx', '_docx': 'docx', '_pptx': 'pptx'}


def _library_of(module_name: str):
    """Which Office library a dotted import target pulls in, if any."""

    parts = module_name.split('.')
    if parts[0] in LIBRARIES:
        return parts[0]
    if parts[0] == 'Scriptum' and len(parts) > 1:
        return PACKAGE_OF.get(parts[1])
    return None


def unguarded_imports(source: str) -> list:
    """(line, library) of every module-level import a skip does not cover.

    A cover is a module-level ``pytest.importorskip('<library>')`` on an
    earlier line -- collection executes the module top to bottom, so a
    guard below the import would come too late. ``importorskip`` is an
    assignment, not an import statement, which is why the guarded modules
    themselves pass an import-statement scan.
    """

    tree = ast.parse(source)

    nested = set()
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for node in ast.walk(fn):
                nested.add(node)

    guards = {}
    imports = []
    for node in ast.walk(tree):
        if node in nested:
            continue
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'importorskip'
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == 'pytest'
                and node.args and isinstance(node.args[0], ast.Constant)):
            library = str(node.args[0].value).split('.')[0]
            if library in LIBRARIES:
                guards[library] = min(guards.get(library, node.lineno),
                                      node.lineno)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                library = _library_of(alias.name)
                if library:
                    imports.append((node.lineno, library))
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            library = _library_of(node.module)
            if library:
                imports.append((node.lineno, library))

    return sorted((line, library) for line, library in imports
                  if guards.get(library, sys.maxsize) > line)


def test_every_backend_import_in_tests_is_declared():
    """No test module may need an Office library without saying so."""

    problems = []
    for py in sorted(TESTS_ROOT.rglob('*.py')):
        if '__pycache__' in py.parts or '.ipynb_checkpoints' in py.parts:
            continue
        for line, library in unguarded_imports(py.read_text(encoding='utf-8')):
            rel = py.relative_to(TESTS_ROOT)
            problems.append(f"{rel}:{line} imports {library} without a prior "
                            f"pytest.importorskip('{library}')")
    assert not problems, (
        'A module that needs an Office library must declare it, so a venv '
        'without that library skips the module instead of failing '
        'collection:\n  ' + '\n  '.join(problems))


# ---------------------------------------------------------------------------
# The guard needs its own guard, like test_layering's detector.

@pytest.mark.parametrize(
    'source, expected',
    [
        # bare imports, both spellings
        ('import docx', [(1, 'docx')]),
        ('from docx.shared import RGBColor', [(1, 'docx')]),
        # the Scriptum back-end packages drag their library in
        ('from Scriptum._docx.reportDocx import ManagedDocx', [(1, 'docx')]),
        ('import Scriptum._pptx', [(1, 'pptx')]),
        # a guard covers what follows it, not what precedes it
        ("import pytest\ndocx = pytest.importorskip('docx')\nimport docx",
         []),
        ("import docx\nimport pytest\npytest.importorskip('docx')",
         [(1, 'docx')]),
        # guards are per library
        ("import pytest\npytest.importorskip('docx')\nimport pptx",
         [(3, 'pptx')]),
        ("import pytest\npytest.importorskip('pptx')\n"
         'from Scriptum._pptx.base import genericFill', []),
        # function-level imports are free, as with win32com
        ('def f():\n    import docx', []),
        # the lazy root package is exactly what makes this import harmless
        ('import Scriptum', []),
    ],
)
def test_detector_finds_what_it_claims(source, expected):
    """Without this, a broken detector would report a clean test tree."""

    assert unguarded_imports(source) == expected


# ---------------------------------------------------------------------------
# Behaviour, demonstrated where a library really refuses to load.

DOCUMENT = """_scriptum_:
  version: 4
  documenttype: docx
_content_:
  - section:title:
      - text:product_name: Hello core
"""

#: Runs in a child interpreter: block the argv[2] libraries, then walk the
#: whole promise. Blocking raises from find_spec, which reaches an importing
#: caller as the ModuleNotFoundError a missing library would raise -- and
#: reaches Scriptum's own availability probe as the broken-install case,
#: which must count as unavailable, not crash the import.
PROBE = """\
import sys

blocked = set(sys.argv[2].split(','))


class BlockedFinder:
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] in blocked:
            raise ModuleNotFoundError(
                f'No module named {name!r} (blocked for this test)',
                name=name)


sys.meta_path.insert(0, BlockedFinder())

import Scriptum
print('IMPORTED')
print('DIR', 'ManagedDocx' in dir(Scriptum), 'ManagedPptx' in dir(Scriptum))

rdf = Scriptum.ReportDataFile(sys.argv[1])
print('TASKS', len(rdf.tasks), 'ERRORS', len(rdf.errors))

for name in ('ManagedDocx', 'ManagedPptx'):
    try:
        getattr(Scriptum, name)
    except ModuleNotFoundError as error:
        print('RAISED', name, error)
    else:
        print('LOADED', name)
"""

LAZY_PROBE = """\
import sys
import Scriptum
print('LEAKED', [m for m in ('docx', 'pptx') if m in sys.modules])
"""


def _run(script: Path, *args: str) -> str:
    env = dict(os.environ)
    env['PYTHONPATH'] = str(REPO_ROOT) + (
        os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    run = subprocess.run([sys.executable, str(script), *args],
                         capture_output=True, text=True, env=env,
                         cwd=str(REPO_ROOT), timeout=120)
    assert run.returncode == 0, run.stderr or run.stdout
    return run.stdout


def test_import_scriptum_loads_no_back_end(tmp_path):
    """The libraries stay out of sys.modules until an attribute asks."""

    probe = tmp_path / 'lazy.py'
    probe.write_text(LAZY_PROBE, encoding='utf-8')
    assert 'LEAKED []' in _run(probe)


@pytest.mark.parametrize('blocked', ['docx', 'pptx', 'docx,pptx'])
def test_core_reads_and_missing_back_end_names_itself(blocked, tmp_path):
    """With a library gone the rest works; with both gone the import says so."""

    document = tmp_path / 'core.yaml'
    document.write_text(DOCUMENT, encoding='utf-8')
    probe = tmp_path / 'probe.py'
    probe.write_text(PROBE, encoding='utf-8')

    out = _run(probe, str(document), blocked)
    gone = set(blocked.split(','))

    if gone == {'docx', 'pptx'}:
        # no back end at all: the tool complains once, at import
        assert 'WARNING: neither python-docx nor python-pptx' in out
        assert out.index('WARNING') < out.index('IMPORTED')
    else:
        # one back end left: nothing to say
        assert out.startswith('IMPORTED')

    # both names stay visible, and the core read the document regardless
    assert 'DIR True True' in out
    assert 'TASKS 2 ERRORS 0' in out

    for name, library, distribution in (('ManagedDocx', 'docx', 'python-docx'),
                                        ('ManagedPptx', 'pptx', 'python-pptx')):
        if library in gone:
            raised = [line for line in out.splitlines()
                      if line.startswith(f'RAISED {name}')]
            assert raised and f'pip install {distribution}' in raised[0]
        else:
            assert f'LOADED {name}' in out
