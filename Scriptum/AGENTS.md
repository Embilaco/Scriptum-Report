# Package Overview

The Scriptum package: a report generator driving python-docx and python-pptx
from a YAML report document (the *rdf*, report data file).

## Layout

- `rdf/` — reads the report document: `reportDataFile.py` (the entry),
  `loader/` (the YAML reader), `tasks/`, `values/`, `namespaces.py` (the
  section ladders). See `rdf/README.md`.
- `_docx/` — the Word back end; `reportDocx.py` is the entry. See
  `_docx/README.md`.
- `_pptx/` — the PowerPoint back end; `reportPptx.py` is the entry. See
  `_pptx/README.md`.
- `tag/` — the `<namespace:name arg=value/>` tag grammar (`docs/tags.md`).
- `element/` — the shared element layer both back ends use.

## Rules that make wrong code look right

- **Dependency direction**: `rdf`, `tag` and `element` are leaves — nothing
  in them may import a back end.
  `tests/02_basetest/architecture/test_layering.py` enforces it from the
  source; breaking it drags an Office library into every parse.
- **File-backed values read UTF-8** (text, parameter and CSV files) — never
  the platform default; the same document must render the same on every
  machine.
- **`finish=True` / `createpdf=True`** run only on Windows through win32com
  (`pywin32` is the optional `[windows]` extra, imported behind
  `os.name == 'nt'`); everywhere else they are a printed no-op. PowerPoint's
  COM differs from Word's — `Presentation.Close()` takes no `SaveChanges`.
- The `Config:`/`Template:` pptx layout machinery is experimental and
  untested; do not build on it without a decision.

## Documentation

`docs/Intro.md` (concept), `docs/rdf.md` (the report document format),
`docs/tags.md` (the tag grammar), `docs/tools.md` (the shipped scripts).
User-visible changes get a terse line in the `CHANGELOG` unreleased block.
