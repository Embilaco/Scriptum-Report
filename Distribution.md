# Distribution — building Scriptum-Report and putting it on PyPI

Written 2026-08-24, releasing 2.0.0. The whole procedure in order; the build
itself is two commands, everything around it is what makes the upload boring.

## 0. One-time prerequisites

- A PyPI account with a project-scoped **API token** for `Scriptum-Report`
  (PyPI → Account settings → API tokens). The token starts with `pypi-`; at
  upload time the user name is the literal `__token__` and the token is the
  password.
- The build tools, into a venv of the worktree you release from:

  ```
  python -m pip install -e ".[release]"
  ```

  brings `build` and `twine` (declared in `pyproject.toml`).

## 1. Prepare the release

- `pyproject.toml`: bump `version`.
- `Scriptum/__init__.py`: bump `__version__` too — the back ends stamp
  `Scriptum {version}` into every document's author property, and the two
  numbers must agree.
- `CHANGELOG`: date the `unreleased` lines with the version
  (`2.0.0 - 2026/08/24 - ...`).
- Full suite green with **every** venv the worktree carries:
  `cd tests`, then `../.venv3XX/Scripts/python.exe -m pytest -q` for each.
- Commit; merge `dev` into `main` with `--no-ff` (in the *main worktree* —
  a branch checked out in one worktree cannot be checked out in another);
  suite green on main as well.
- Tag on main: `git tag -a v2.0.0 -m "2.0.0"`; push branches and the tag
  (`git push origin main dev v2.0.0`).

## 2. Build

From the root of the worktree that holds the release commit:

```
python -m build
```

That is the whole build. It runs in an **isolated environment** — it fetches
its own current `setuptools`, which the PEP 639 license expression in
`pyproject.toml` needs — and writes both artifacts into `dist/`:

- `scriptum_report-<version>.tar.gz` — the source distribution
- `scriptum_report-<version>-py3-none-any.whl` — the wheel, the modern
  successor of the egg (nothing builds `.egg` files any more; PyPI wants
  wheels)

`dist/` and `*.egg-info/` are gitignored, so artifacts from earlier releases
may still sit there. Either empty `dist/` first or always address files by
explicit version below.

**What ships where**: the *wheel* carries the `Scriptum` package plus the
`script-files` of `pyproject.toml`, nothing else. The *sdist* additionally
carries `docs/`, `CHANGELOG`, the licenses and the standard metadata — and
**never** `tests/`: `MANIFEST.in` prunes it, because setuptools reads the
working tree rather than git and its legacy rules once swept a gitignored
local `tests/test_debug.py` (with an absolute path inside) into the tarball.
After changing what ships, always list the built artifacts before uploading:

```
python - <<'PY'
import tarfile; print(*tarfile.open('dist/scriptum_report-<version>.tar.gz').getnames(), sep='\n')
PY
```

## 3. Check before uploading

```
python -m twine check dist/scriptum_report-<version>*
```

validates the metadata and the long description PyPI renders (the README).
The two-minute smoke that the wheel really carries the package:

```
python -m venv %TEMP%\wheelcheck
%TEMP%\wheelcheck\Scripts\python.exe -m pip install dist/scriptum_report-<version>-py3-none-any.whl
%TEMP%\wheelcheck\Scripts\python.exe -c "import Scriptum; print(Scriptum.version)"
```

The bare check prints nothing but the version line, on every platform:
`win32com` is imported at finish time (not at module import), so the back
ends load without the `[windows]` extra and only a `finish=True` /
`createpdf=True` run reports the missing pywin32. (Until 2.0.0 the import
sat at module top and this check printed two
`Skip ... No module named 'win32com'` lines on a bare Windows install --
if those return, the lazy import regressed.)

## 4. Upload

```
python -m twine upload dist/scriptum_report-<version>*
```

- user name: `__token__`
- password: the API token (`pypi-...`)

Upload by **explicit version**, never `dist/*`, when old artifacts are in the
folder: PyPI refuses re-uploads of already-released versions, and one stray
old file aborts the whole batch. To rehearse against the test index first:

```
python -m twine upload --repository testpypi dist/scriptum_report-<version>*
```

## 5. After

- From any clean venv, `pip install --upgrade Scriptum-Report` and
  `python -c "import Scriptum; print(Scriptum.version)"` confirm the release
  resolves.
- The PyPI project page renders `README.md`; its relative links (LICENSES/,
  docs/) point into the GitHub tree and do not resolve on the PyPI page
  itself — known and accepted.
- A version, once uploaded, is immutable: a mistake means a new version
  (`2.0.0.post1` or `2.0.1`), never a re-upload.
