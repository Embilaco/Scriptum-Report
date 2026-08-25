"""Nothing tracked carries an absolute path of the machine it was made on.

The rule (directive of 2026-08-25, after the 2.0.0 sdist shipped a stray
``tests/test_debug.py`` with an absolute path inside): nothing stored in the
repository or shipped in an artifact may name this machine's directories.
The known repeat offender is a Jupyter notebook's stored output -- the first
cell of every CheckReport prints ``sys.executable``, so *re-running* a
scrubbed notebook brings the paths right back. Hence two checks, one
mechanism apiece:

* no tracked text file matches a machine-root pattern (``E:\\users``,
  ``C:\\Users\\...\\AppData``, ``/home/...``);
* no tracked notebook stores outputs or execution counts at all -- the
  stronger rule that keeps future leaks out of places the path pattern
  cannot anticipate. ``scripts/strip_notebook_outputs.py`` restores it
  after a notebook session.

Both walk ``git ls-files``, so an untracked local scratch file (the sdist
culprit was one) cannot fail the suite -- MANIFEST.in keeps those out of
artifacts, and what is not tracked is not this test's business.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]

#: Extensions that are binary by construction; a zipped docx cannot leak a
#: readable path, and scanning megabytes of media buys nothing.
BINARY = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.docx', '.dotx',
          '.pptx', '.potx', '.xlsx', '.pdf', '.mp4', '.avi', '.mov', '.zip',
          '.gz', '.whl'}

#: A drive letter followed by a machine root, or a POSIX home. Built from
#: parts so this file does not match itself.
ROOTS = '|'.join(['users', 'home', 'temp', 'appdata', 'programdata',
                  'program files'])
MACHINE_PATH = re.compile(r'(?i)\b[a-z]:[\\/]+(?:%s)\b' % ROOTS)
POSIX_HOME = re.compile(r'(?:^|[\s\'"=(])/(?:home|Users)/\w')


def tracked(pattern='*'):
    listed = subprocess.run(['git', 'ls-files', pattern], cwd=REPO_ROOT,
                            capture_output=True, text=True)
    if listed.returncode != 0:
        pytest.skip('not a git checkout, nothing to enforce here')
    return [REPO_ROOT / line for line in listed.stdout.splitlines() if line]


def test_no_tracked_text_file_names_this_machines_directories():
    offenders = []
    for path in tracked():
        if path.suffix.lower() in BINARY or path == THIS_FILE:
            continue
        text = path.read_text(encoding='utf-8', errors='replace')
        for lineno, line in enumerate(text.splitlines(), start=1):
            if MACHINE_PATH.search(line) or POSIX_HOME.search(line):
                offenders.append(
                    f'{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()[:100]}')
    assert not offenders, (
        'absolute machine paths in tracked files:\n  ' + '\n  '.join(offenders)
        + '\n\nFor a notebook, run scripts/strip_notebook_outputs.py; '
          'for anything else, make the path relative or derive it at run time.')


def test_tracked_notebooks_store_no_outputs():
    offenders = []
    for path in tracked('*.ipynb'):
        notebook = json.loads(path.read_text(encoding='utf-8'))
        for index, cell in enumerate(notebook.get('cells', [])):
            if cell.get('cell_type') != 'code':
                continue
            if cell.get('outputs') or cell.get('execution_count') is not None:
                offenders.append(f'{path.relative_to(REPO_ROOT)} (cell {index})')
                break
    assert not offenders, (
        'tracked notebooks with stored outputs:\n  ' + '\n  '.join(offenders)
        + '\n\nRun scripts/strip_notebook_outputs.py before committing.')
