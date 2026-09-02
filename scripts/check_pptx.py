#!/usr/bin/env python3
"""Validate Scriptum PPTX templates."""

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


def _load_managed_pptx() -> type[object] | None:
    spec = importlib.util.find_spec("Scriptum._pptx.reportPptx")
    if spec is None:
        print(
            "ERROR: Unable to import Scriptum PowerPoint support. Ensure python-pptx is installed.",
            file=sys.stderr,
        )
        return None

    module = importlib.import_module("Scriptum._pptx.reportPptx")
    managed_pptx = getattr(module, "ManagedPptx", None)
    if managed_pptx is None:
        print("ERROR: ManagedPptx is not available from Scriptum._pptx.reportPptx.", file=sys.stderr)
        return None

    return managed_pptx


def _validate_pptx(paths: Iterable[Path], debug: bool) -> int:
    managed_pptx = _load_managed_pptx()
    if managed_pptx is None:
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
                presentation = managed_pptx(str(path), debug=True)
            else:
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    presentation = managed_pptx(str(path), debug=False)
        except Exception as exc:  # pragma: no cover - runtime guard
            print(f"{path}: failed to open presentation: {exc}")
            exit_code = max(exit_code, 2)
            continue

        if debug and buffer is not None:
            captured = buffer.getvalue()
            if captured:
                print(captured, end="")

        errors = getattr(presentation, "errors", [])
        warnings = getattr(presentation, "warnings", [])

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
        description="Validate Scriptum PPTX templates.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="PPTX file(s) to validate.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show verbose output from Scriptum internals.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_arguments(argv if argv is not None else sys.argv[1:])
    return _validate_pptx(args.paths, args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
