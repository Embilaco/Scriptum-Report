# Instructions — swapping a venv for a new Python version

Written 2026-08-24, when `.venv313` (Python 3.13.1) was replaced by `.venv314`
(Python 3.14.7). Follow this whenever a Python version is installed or removed
on this machine.

## Background

- Python installs live in `<somewhere>\Python3XX` (currently `Python310` and
  `Python314`).
- Every worktree (`dev\Scriptum-Report-main` = main, `dev\Scriptum-Report-dev`,
  `dev\Scriptum-Report-dev-yaml`) carries its **own** venvs, named `.venv3XX`
  after the minor version. They are gitignored (`.venv*`) and never follow git.
- A venv **stops working entirely** once its base install is uninstalled:
  the venv's `python.exe` is a launcher that resolves `home = <somewhere>\Python3XX`
  from `pyvenv.cfg`. So capture `pip freeze` from the old venv *while the old
  Python is still installed* — afterwards the package list can only be
  reconstructed from the `*.dist-info` folder names in `.venv3XX\Lib\site-packages`.

## Creating the new venv (per worktree, from the worktree root)

```
<somewhere>\Python3XX\python.exe -m venv .venv3XX
.venv3XX\Scripts\python.exe -m pip install --upgrade pip
.venv3XX\Scripts\python.exe -m pip install -e ".[dev]"
```

`.[dev]` pulls the runtime deps (python-docx, python-pptx, Pillow, PyYAML) plus
the dev extras (pytest, pywin32, python-dateutil) from `pyproject.toml`.
pywin32 needs no post-install step — the test suite is the proof.

## Verifying

1. **Binding** — from a *neutral* cwd (never from inside a worktree: the cwd
   lands on `sys.path` and masks a wrong install):

   ```
   cd C:\
   <full-path-to-worktree>\.venv3XX\Scripts\python.exe -c "import Scriptum; print(Scriptum.__file__)"
   ```

   Must print the `Scriptum\__init__.py` of *that* worktree.
2. **Packages** — compare `pip freeze` with the previous venv's list; everything
   except `pip` itself should match.
3. **Suite** — `cd tests`, then `..\.venv3XX\Scripts\python.exe -m pytest -q`,
   for every venv the worktree has. Green on 2026-08-24: 575 passed, on both
   3.10.5 and 3.14.7.

## Removing the old venv

Delete the folder (e.g. `.venv313`) — it is gitignored and fully regenerable.
Only after the new venv passed the three checks above.

## VSCode

Interpreter (plain `.py` work):

- `Ctrl+Shift+P` → **Python: Select Interpreter** → refresh (🔄) → pick the
  worktree's `.venv3XX\Scripts\python.exe`.
- A deleted venv lingering in that list disappears after
  **Python: Clear Cache and Reload Window**.

Notebook kernels:

- Kernel picker (top right of the notebook) → **Select Another Kernel… →
  Python Environments…** → the new `.venv3XX`. On first use VSCode offers to
  install `ipykernel` into the venv — accept, or preinstall it yourself:
  `.venv3XX\Scripts\python.exe -m pip install ipykernel`.
- Explicitly registered kernels live in `%APPDATA%\jupyter\kernels\<name>\kernel.json`
  (e.g. `scriptum-dev-yaml`, which pointed at the dev-yaml `.venv313`).
  Removing one = deleting its folder (that is all `jupyter kernelspec remove <name>`
  does). Registering the replacement:

  ```
  .venv3XX\Scripts\python.exe -m pip install ipykernel
  .venv3XX\Scripts\python.exe -m ipykernel install --user --name scriptum-dev-3XX --display-name "Scriptum dev (3.XX)"
  ```

- The `CheckReport.ipynb` notebooks verify in their first code cell that
  `Scriptum` imports from their own worktree; the advice they print points
  here, so a venv swap needs no edits in them.

## Checklist for the next change

- [ ] New venv in every worktree that needs it, `pip install -e ".[dev]"`
- [ ] Binding + freeze + suite verified per worktree and venv
- [ ] Old venv folders deleted
- [ ] VSCode interpreter reselected; kernelspec under `%APPDATA%\jupyter\kernels` replaced
- [ ] Each notebook reopened once on the new kernel (its first cell checks it)
- [ ] Claude memory (`dev-environment-layout`) and any docs naming the venv updated
