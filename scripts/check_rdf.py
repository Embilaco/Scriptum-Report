#!/usr/bin/env python3
"""Validate Scriptum report documents (.yaml).

Reads each document the way Scriptum will and prints what it refuses -- every
diagnostic, with file, line, column and the path through the document -- or
the files the document names, so missing inputs are seen before a report is
built.
"""

import argparse
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Iterable, Sequence


# either Scriptum is installed or we take the one that is hopefully relative to this file

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_PARENT = PROJECT_ROOT.parent
for candidate in (REPO_PARENT, PROJECT_ROOT):
    path_str = str(candidate)
    if path_str not in sys.path:
        sys.path.append(path_str)

try:
    import Scriptum
except ImportError:
    print('Cannot evaluate report document, package Scriptum not found!')
    raise SystemExit(1)


def _validate(paths: Iterable[Path], debug: bool) -> int:

    exit_code = 0
    for path in paths:
        if not path.exists():
            print(f"{path}: file not found")
            exit_code = max(exit_code, 2)
            continue

        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                document = Scriptum.ReportDataFile(str(path), debug=debug)
        except Exception as exc:
            # A DocumentError carries every diagnostic; a refused extension or
            # an unreadable file reads the same way.
            print(f"{path}: invalid Scriptum report document")
            print('errors detected:')
            for line in str(exc).splitlines():
                print(f"    {line}")
            exit_code = max(exit_code, 1)
            continue

        if debug:
            captured = buffer.getvalue()
            if captured:
                print(captured, end="")

        print(f"{path}: valid Scriptum report document "
              f"({len(document.tasks)} tasks, documenttype "
              f"{document.settings.documenttype!r})")
        files = io.StringIO()
        with redirect_stdout(files):
            document.showFiles()
        for line in files.getvalue().splitlines():
            print(f"    {line}")

    return exit_code


def _parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Scriptum report documents (.yaml).",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="report document(s) to validate.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show verbose output from Scriptum internals.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_arguments(argv if argv is not None else sys.argv[1:])
    return _validate(args.paths, args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
