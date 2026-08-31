# Project Overview
This is a python application using python-pptx and python-docx to create documents (DOCX, PPTX) from templates. The content comes from a YAML report document — see docs/Intro.md for the concept and docs/rdf.md for the format.

## Build and Test Instructions
- Install for development: `python -m pip install -e ".[dev]"` — brings the runtime dependencies (python-docx, python-pptx, Pillow, PyYAML) plus pytest, pywin32 and python-dateutil.
- Tests are in folder tests; run them from there with every venv the worktree carries: `cd tests`, then `../.venv3XX/Scripts/python.exe -m pytest -q`. Green means all of them.
- Instructions for tests in tests/AGENTS.md
- Instructions for virtual envs and Python version changes in tests/Instructions.md
- Folder Scriptum contains the package (see Scriptum/AGENTS.md), docs the format documentation, scripts the shipped helpers (docs/tools.md).

## Module organization
- `import Scriptum` will import the whole package.
- In case `Scriptum` cannot be imported, prefer the editable install above over adding folders to `sys.path`.

## Working rules
- One logical change per commit, reasoning in the message; stage explicit paths.
- A user-visible change gets a terse line in the CHANGELOG `unreleased` block.
- Nothing tracked carries an absolute path of this machine, and tracked
  notebooks store no outputs — run `python scripts/strip_notebook_outputs.py`
  after a notebook session; `tests/02_basetest/architecture/test_repo_hygiene.py`
  enforces both.
- The architecture is mapped in a Spatial project (MCP connector `spatial-scriptum`, registered per worktree); when the connector is available, prefer its briefing and stale-check over re-deriving structure, and record decisions there.
