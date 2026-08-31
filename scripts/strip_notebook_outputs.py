#!/usr/bin/env python3
"""Strip stored outputs and execution counts from tracked Jupyter notebooks.

The policy (2026-08-25): tracked notebooks carry **no stored outputs**. A
notebook's value here is what it *runs* -- the CheckReport comparisons, the
inspect tools -- and its stored output is whatever machine last executed it:
including absolute interpreter, workspace and temp paths, which have no place
in the repository or on GitHub (the 2.0.0 sdist leak was the same rule broken
in a different file). Re-running a notebook refreshes its outputs and the
paths with them, so scrubbing once would not stay scrubbed; stripping before
committing is the rule instead, and
``tests/02_basetest/architecture/test_repo_hygiene.py`` enforces it.

Usage::

    python scripts/strip_notebook_outputs.py           # every tracked .ipynb
    python scripts/strip_notebook_outputs.py a.ipynb   # just these

Only files that change are rewritten, and each rewritten file is named. The
JSON layout (indent 1, like Jupyter writes it) is preserved so a strip does
not drown the real diff.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def tracked_notebooks():
    listed = subprocess.run(['git', 'ls-files', '*.ipynb'], cwd=REPO_ROOT,
                            capture_output=True, text=True, check=True)
    return [REPO_ROOT / line for line in listed.stdout.splitlines() if line]


def strip(path: Path) -> bool:
    """Empty every cell's outputs and execution_count. True if it changed."""
    notebook = json.loads(path.read_text(encoding='utf-8'))

    changed = False
    for cell in notebook.get('cells', []):
        if cell.get('cell_type') != 'code':
            continue
        if cell.get('outputs'):
            cell['outputs'] = []
            changed = True
        if cell.get('execution_count') is not None:
            cell['execution_count'] = None
            changed = True

    if changed:
        path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False)
                        + '\n', encoding='utf-8')
    return changed


def main(argv):
    paths = [Path(arg).resolve() for arg in argv] or tracked_notebooks()
    stripped = [path for path in paths if strip(path)]
    for path in stripped:
        try:
            print('stripped', path.relative_to(REPO_ROOT))
        except ValueError:
            print('stripped', path)
    if not stripped:
        print('nothing to strip')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
