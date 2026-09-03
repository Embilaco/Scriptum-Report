## SCRIPTUM a report generator

by temmel007@gmail.com, 2020-2026

This is a PYTHON implementation of a report generator to create PPTX, DOCX from content and templates, inspired by the LaTeX principle of splitting content from style

<pre>   ___   ___  ____  ____  ____  ____  __  __  __  __
  / __) / __)(  _ \(_  _)(  _ \(_  _)(  )(  )(  \/  )
  \__ \( (__  )   / _)(_  )___/  )(   )(__)(  )    (
  (___/ \___)(_)\_)(____)(__)   (__) (______)(_/\/\_)
</pre>

### Origin:
   from latin *Scriptum* "written", participle perfect to *scribere* "write"

collect classes and functions to create reports
based on a template and the python-docx and python-pptx packages

for details on
 * python-docx see https://python-docx.readthedocs.io
 * python-pptx see https://python-pptx.readthedocs.io
 * openxml by Microsoft see http://officeopenxml.com/

### Source

see https://github.com/Embilaco/Scriptum-Report

### Install

pip install Scriptum-Report

Optional extras: `Scriptum-Report[windows]` installs `pywin32` for the
finishing step (re-save and PDF export through a running Word/PowerPoint,
Windows only); `Scriptum-Report[dates]` installs `python-dateutil` for richer
date parsing.

### License

This project is dual-licensed, and **both licenses are free of charge**:

- **Non-commercial use:** [PolyForm Noncommercial License 1.0.0](LICENSES/PolyForm-Noncommercial-1.0.0.md)
- **Commercial use:** [SCRIPTUM License for Commercial Use](LICENSES/Commercial.md) —
  free, granted to everyone, nothing to buy and no contract to sign. The
  German version, [`Commercial.de.md`](LICENSES/Commercial.de.md), is the
  authoritative one; the English is a translation.

Commercial use costs nothing and the software is provided **as is**. If you
earn with it, you are *asked* — not required — to support the project:
10–20 € per month and user is the suggestion, any amount is welcome, and
paying nothing breaches nothing. See section 6 of the license.

SPDX identifiers:

- Non-commercial: `PolyForm-Noncommercial-1.0.0`
- Commercial: `LicenseRef-SCRIPTUM-Commercial`

If you plan to use this software in a commercial setting,
please see [`LICENSES/Commercial.md`](LICENSES/Commercial.md).

### Further reading

See [`documentation`](docs/Intro.md) or [here](https://github.com/Embilaco/Scriptum-Report/blob/main/docs/Intro.md) and other files in that folder.

For a start, take the examples found on https://github.com/Embilaco/Scriptum-Report
in the folders of `tests`
