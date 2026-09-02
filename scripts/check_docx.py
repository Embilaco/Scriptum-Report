#!/usr/bin/env python3
"""Validate Scriptum DOCX templates."""

import argparse
import importlib
import importlib.util
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_PARENT = PROJECT_ROOT.parent
for candidate in (REPO_PARENT, PROJECT_ROOT):
    path_str = str(candidate)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def _print_errors(path: Path, errors: Sequence[str], intro: str) -> None:
    print(f"{path}: {intro}")
    for entry in errors:
        print(f"    - {entry}")


def _load_managed_docx() -> type[object] | None:
    spec = importlib.util.find_spec("Scriptum._docx.reportDocx")
    if spec is None:
        print(
            "ERROR: Unable to import Scriptum Word support. Ensure python-docx is installed.",
            file=sys.stderr,
        )
        return None

    module = importlib.import_module("Scriptum._docx.reportDocx")
    managed_docx = getattr(module, "ManagedDocx", None)
    if managed_docx is None:
        print("ERROR: ManagedDocx is not available from Scriptum._docx.reportDocx.", file=sys.stderr)
        return None

    return managed_docx


def _validate_docx(paths: Iterable[Path], debug: bool) -> int:
    managed_docx = _load_managed_docx()
    if managed_docx is None:
        return 2

    exit_code = 0
    for path in paths:
        if not path.exists():
            print(f"{path}: file not found")
            exit_code = max(exit_code, 2)
            continue

        buffer: io.StringIO | None = None
        try:
            if debug:
                doc = managed_docx(str(path), debug=True)
            else:
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    doc = managed_docx(str(path), debug=False)
        except Exception as exc:  # pragma: no cover - runtime guard
            print(f"{path}: failed to open template: {exc}")
            exit_code = max(exit_code, 2)
            continue

        if debug and buffer is not None:
            captured = buffer.getvalue()
            if captured:
                print(captured, end="")

        errors = getattr(doc, "errors", [])
        warnings = getattr(doc, "warnings", [])

        if errors:
            _print_errors(path, errors, "invalid Scriptum template")
            exit_code = max(exit_code, 1)
        else:
            print(f"{path}: valid Scriptum template definition")
            if warnings:
                _print_errors(path, warnings, "warnings detected")

    return exit_code


def _parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Scriptum DOCX templates.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="DOCX file(s) to validate.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show verbose output from Scriptum internals.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_arguments(argv if argv is not None else sys.argv[1:])
    return _validate_docx(args.paths, args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
