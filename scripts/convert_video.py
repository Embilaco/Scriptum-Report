#!/usr/bin/env python3
"""Convert video files to PowerPoint-friendly MP4 files.

This script mirrors the behaviour of the previous Bash implementation by:

* Accepting one or more file and directory paths.
* Recursively locating supported video files.
* Converting them to H.264 MP4 files suitable for PowerPoint.
* Extracting a poster frame.
* Capturing basic metadata (width/height) in a JSON file.

It requires both ``ffmpeg`` and ``ffprobe`` to be installed and available on the
``PATH``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence


SUPPORTED_EXTENSIONS = {
    "avi",
    "mkv",
    "mov",
    "mp4", 
    "mpg",
    "mpeg",
    "wmv",
    "flv",
    "webm",
    "m4v",
    "gif",
    "qt",
    "3gp",
}


FFMPEG_VIDEO_OPTS: Sequence[str] = (
    "-c:v",
    "libx264",
    "-preset",
    "slow",
    "-profile:v",
    "high",
    "-level",
    "4.0",
    "-pix_fmt",
    "yuv420p",
    "-crf",
    "22",
    "-movflags",
    "+faststart",
)


FFMPEG_AUDIO_OPTS: Sequence[str] = (
    "-c:a",
    "aac",
    "-b:a",
    "192k",
)


class DependencyError(RuntimeError):
    """Raised when a required command is missing from the PATH."""


def ensure_dependency(command: str, url: str) -> None:
    """Ensure ``command`` is available, otherwise raise ``DependencyError``."""

    if shutil.which(command) is None:
        raise DependencyError(
            f'ERROR: required command "{command}" not found on PATH.\n'
            f"       Please install {command}: {url}"
        )


def find_supported_files(inputs: Iterable[Path]) -> List[Path]:
    """Return a sorted list of supported files discovered from *inputs*."""

    files: List[Path] = []
    seen: set[Path] = set()

    for path in inputs:
        if path.is_dir():
            candidates = (p for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            candidates = [path]
        else:
            print(f"WARNING: {path} is not a valid file or directory. Skipping.", file=sys.stderr)
            continue

        for candidate in candidates:
            if candidate.suffix.lower().lstrip(".") in SUPPORTED_EXTENSIONS:
                resolved = candidate.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    files.append(candidate)

    files.sort()
    return files


def convert_video(source: Path, target: Path, force: bool) -> None:
    """Convert *source* video to PowerPoint-friendly MP4 saved at *target*."""

    overwrite_flag = "-y" if force else "-n"
    cmd = [
        "ffmpeg",
        overwrite_flag,
        "-i",
        str(source),
        *FFMPEG_VIDEO_OPTS,
        *FFMPEG_AUDIO_OPTS,
        str(target),
    ]
    print(f"Converting {source} -> {target}")
    subprocess.run(cmd, check=True)


def extract_poster_frame(video: Path, destination: Path, force: bool) -> None:
    """Extract a poster frame from *video* into *destination*."""

    overwrite_flag = "-y" if force else "-n"
    cmd = ["ffmpeg", overwrite_flag, "-i", str(video), "-frames:v", "1", str(destination)]
    print(f"Extracting poster frame {destination}")
    subprocess.run(cmd, check=True)


def probe_dimensions(video: Path) -> tuple[int, int] | None:
    """Return the ``(width, height)`` for *video* or ``None`` if unavailable."""

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(video),
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        print(f"WARNING: unable to determine dimensions for {video}", file=sys.stderr)
        return None

    value = result.stdout.strip()
    if "x" not in value:
        print(f"WARNING: unexpected ffprobe output for {video}: {value}", file=sys.stderr)
        return None
    width_str, height_str = value.split("x", 1)
    try:
        return int(width_str), int(height_str)
    except ValueError:
        print(f"WARNING: invalid dimensions from ffprobe for {video}: {value}", file=sys.stderr)
        return None


def write_metadata(
    metadata_path: Path,
    source: Path,
    video: Path,
    poster: Path,
    dimensions: tuple[int, int] | None,
) -> None:
    """Write a JSON metadata file mirroring the Bash implementation."""

    data = {
        "source": source.name,
        "video": video.name,
        "poster_frame": poster.name,
    }
    if dimensions:
        data["width"], data["height"] = dimensions
    with metadata_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    print(f"Metadata written to {metadata_path}")


def process_file(source: Path, output_dir: Path | None, force: bool) -> None:
    target_dir = output_dir or source.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    base_name = source.stem
    mp4_path = target_dir / f"{base_name}.mp4"
    poster_path = target_dir / f"{base_name}_poster.jpg"
    metadata_path = target_dir / f"{base_name}.metadata.json"

    if mp4_path.exists() and not force:
        print(f"Skipping conversion (exists): {mp4_path}")
    else:
        convert_video(source, mp4_path, force)

    if poster_path.exists() and not force:
        print(f"Skipping poster frame (exists): {poster_path}")
    else:
        extract_poster_frame(mp4_path, poster_path, force)

    dimensions = probe_dimensions(mp4_path)
    if dimensions is None:
        return

    write_metadata(metadata_path, source, mp4_path, poster_path, dimensions)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="convert_video.py",
        description=(
            "Convert one or more video files to PowerPoint-friendly MP4 files, "
            "extract a poster frame image, and collect basic metadata (width/height)."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Paths to video files or directories to process.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write converted files to DIR. Defaults to the directory of each input file.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing outputs.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv or sys.argv[1:])

    if not args.paths:
        parser.print_help()
        return 0

    try:
        ensure_dependency("ffmpeg", "https://ffmpeg.org/download.html")
        ensure_dependency("ffprobe", "https://ffmpeg.org/download.html")
    except DependencyError as exc:
        print(exc, file=sys.stderr)
        return 1

    files = find_supported_files(args.paths)
    if not files:
        print("No supported video files found.", file=sys.stderr)
        return 1

    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)

    for file_path in files:
        try:
            process_file(file_path, args.output, args.force)
        except subprocess.CalledProcessError as exc:
            print(f"ERROR: processing {file_path}: {exc}", file=sys.stderr)
            return exc.returncode or 1

    print(f"\nProcessed {len(files)} file(s).")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
