# Folder Overview

This is the test folder for the package Scriptum. Run `pytest` from this
directory and everything is collected — there is no pytest configuration;
discovery is entirely the default. `TestOverview.ipynb` explains how the
suite is driven and shows live results; `Instructions.md` is the venv/kernel
procedure for Python version changes. Run the suite with every `.venv3XX`
the worktree carries before committing.

## Layout

- `02_basetest` — the areas, one directory each:
  - `yaml_loader` — the YAML document reader (`Scriptum.rdf.loader`)
  - `values` — the value types (text, date, image, table, colour, length, ...)
  - `parameter` — the parameter-file reader (`.par`/`.nv`)
  - `tag` — the `<tag arg=.../>` parser
  - `docx_basic` — one directory per Word case (document + template +
    `expected/` reference + `CheckReport.ipynb`): `simple`, `text`, `images`,
    `tables`; plus `ladder` — a clean template down every rung of the ladder
    (`section` to `sub5section`) with prose in every gap, which is what makes
    the placement of a repeated block observable, and one block named where
    the template does not hold it, whose warnings are pinned in full
  - `pptx-basic` — the PowerPoint side: `simple` is the case, and
    `internal_structures` pins the shipped template's layout/tag inventory
    and the placement math, beside `inspect-*.ipynb` exploration notebooks
  - `differential` — `test_references.py`, the registry of all cases plus
    cross-case checks
  - `convert` — `scripts/rdf2yaml.py`, the `.rdf` → `.yaml` converter
  - `architecture` — the import-layering rules of the package
  - `rdf` — **no tests**: the hand-translated YAML corpus of the historical
    `.rdf` fixtures; `yaml_loader/test_yaml_corpus.py` loads every one of them
- `04_examples` — full worked examples and starting points for own work
  (`essay`, `wordreport`, `pptreport`), each a complete case with data, tests
  and a `CheckReport.ipynb`
- `data_source` — **no tests**: the shared images, CSVs, videos and parameter
  files the cases link into their workspace as `data/`
- `conftest.py` — puts the repository root and every directory holding a
  `_setup_*.py` on `sys.path`
- `baseTestRoot.py` — shared constants and helpers (`DATA_SOURCE`,
  `ensure_link`, `setupTestEnvironment`, ...)
- `02_basetest/common_case.py` — `CaseConfig`, `run_docx_case`,
  `run_pptx_case` and the read-back helpers every case test compares with

The notebooks beside the tests are manual companions, not collected by
pytest: each `CheckReport.ipynb` spreads its case test out cell by cell so
you can look at every stage.

Third-party material in the fixtures is credited in `NOTICE.md` beside this
file — keep it current when fixtures change hands or sources.
