"""A bare Windows install -- no pywin32 -- keeps both back ends.

Until 2.0.0 ``reportDocx.py`` and ``reportPptx.py`` imported
``win32com.client`` at module top under ``os.name == 'nt'``, so on Windows
without the ``[windows]`` extra *both* ``ManagedDocx`` and ``ManagedPptx``
vanished at import ("Skip docx generation ...") and a plain
``pip install Scriptum-Report`` got a package that reads documents but
generates nothing. win32com is imported at finish time now: the back ends
load everywhere, and only ``finish=True``/``createpdf=True`` -- the one step
that drives Office -- reports what is missing.

The import-shape half is checked with :mod:`ast`, like ``test_layering``:
the suite always runs with pywin32 installed, so only the source can show
that nothing imports it at module level. The behaviour half poisons
``sys.modules`` so the finish-time import really fails, whatever is
installed, and patches ``os.name`` so both branches run on any platform.
"""

import ast
import os
import sys
from pathlib import Path

import docx
import pptx
import pytest

import Scriptum
from Scriptum._docx.reportDocx import ManagedDocx
from Scriptum._pptx.reportPptx import ManagedPptx

BACK_ENDS = ('_docx/reportDocx.py', '_pptx/reportPptx.py')
SOURCE_ROOT = Path(Scriptum.__file__).resolve().parent


def _win32com_import_lines(tree):
    """Line numbers of every import statement that reaches win32com."""
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split('.')[0] == 'win32com'
                   for alias in node.names):
                lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if (node.module or '').split('.')[0] == 'win32com':
                lines.append(node.lineno)
    return lines


@pytest.mark.parametrize('relpath', BACK_ENDS)
def test_win32com_is_not_a_module_level_import(relpath):
    """The regression guard: win32com only ever appears inside a function."""

    tree = ast.parse((SOURCE_ROOT / relpath.replace('/', os.sep)).read_text(
        encoding='utf-8'))
    offenders = _win32com_import_lines(tree)
    assert offenders, f'{relpath} does not touch win32com at all any more -- '\
        'if finishing moved elsewhere, move this guard with it'

    # module level = reachable without calling anything: not inside a function
    nested = set()
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nested.update(_win32com_import_lines(fn))
    at_module_level = [line for line in offenders if line not in nested]
    assert not at_module_level, (
        f'{relpath} imports win32com at module level (line '
        f'{at_module_level}); that makes a Windows install without pywin32 '
        'lose the whole back end instead of just the finishing step')


def _bare_pptx():
    """A ManagedPptx around an empty deck, without loading a template."""
    managed = ManagedPptx.__new__(ManagedPptx)
    managed.document = pptx.Presentation()
    return managed


def _bare_docx():
    """A ManagedDocx around an empty document, without loading a template."""
    managed = ManagedDocx.__new__(ManagedDocx)
    managed.document = docx.Document()
    managed.document_name = 'template.docx'   # the overwrite guard reads it
    return managed


@pytest.mark.parametrize('bare, output', [(_bare_pptx, 'report.pptx'),
                                          (_bare_docx, 'report.docx')])
def test_finish_without_pywin32_reports_the_extra(bare, output, tmp_path,
                                                  monkeypatch, capsys):
    """``finish=True`` without pywin32: the document is saved, the missing
    ``[windows]`` extra is named, nothing raises."""

    monkeypatch.setattr(os, 'name', 'nt')
    monkeypatch.setitem(sys.modules, 'win32com', None)
    monkeypatch.setitem(sys.modules, 'win32com.client', None)

    target = tmp_path / output
    bare().save(str(target), finish=True)

    out = capsys.readouterr().out
    assert 'pywin32' in out and '[windows]' in out
    assert target.exists() and target.stat().st_size > 0


@pytest.mark.parametrize('bare, output', [(_bare_pptx, 'report.pptx'),
                                          (_bare_docx, 'report.docx')])
def test_finish_off_windows_notes_it_without_trying_the_import(
        bare, output, tmp_path, monkeypatch, capsys):
    """Off Windows the note comes first; win32com is not even attempted --
    the poisoned modules would turn an attempt into the pywin32 message."""

    monkeypatch.setattr(os, 'name', 'posix')
    monkeypatch.setitem(sys.modules, 'win32com', None)
    monkeypatch.setitem(sys.modules, 'win32com.client', None)

    target = tmp_path / output
    bare().save(str(target), finish=True)

    out = capsys.readouterr().out
    assert 'will prevent any finishing work' in out
    assert 'pywin32' not in out
    assert target.exists() and target.stat().st_size > 0
