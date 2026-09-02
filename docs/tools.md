# Tools and Validation helpers

This page covers the scripts Scriptum **ships** — the six named in
`pyproject.toml` under `script-files`, which a `pip install` puts within
reach. Anything else in `scripts/` of the source tree is a development tool,
belongs to the repository rather than to the distribution, and is described
where it is used rather than here.

## Definition of templates

Use the dedicated helpers in `scripts/` to verify that templates and report
documents follow Scriptum's conventions before running the generators:

```
python scripts/check_docx.py path/to/template.docx
python scripts/check_pptx.py path/to/template.pptx
python scripts/check_rdf.py path/to/report.yaml
```

Pass `--debug` to any checker to display the verbose output if additional
context is required. `check_rdf.py` reads a report document the way Scriptum
will and prints every problem it refuses -- file, line, column and the path
through the document -- or, for a valid document, the files it names and which
of them are missing. The DOCX and PPTX scripts rely on `python-docx` and
`python-pptx`; install them as described in `AGENTS.md` when validating DOCX or
PPTX files.

## Convert an existing `.rdf` base to YAML

`scripts/rdf2yaml.py` turns the retired `.rdf` text format into `.yaml` report
documents -- a starting point to be finished by hand, not a bullet-proof
translation:

```
python scripts/rdf2yaml.py report.rdf [more.rdf ...] [--out DIR] [--force] [--no-follow] [--no-check]
```

Each `.rdf` named is a root document and is written as a `.yaml` beside it (or
under `--out`). Files an `&include` names are followed and converted as
fragments relative to where the include sits; `loopfiles:` globs keep their
wildcard. What was ambiguous in the old format -- an absolute address that
re-enters a path with several instances, a fragment that addresses a level
above its include or another section, a setting set twice, a marker an include
silently cleared, a namespace not on the ladder -- is decided the way the old
parser or the hand-translated corpus decided it and marked with a `# CHECK:`
comment in the output, so the places to look at are the places with a comment.
The result is then read the way Scriptum reads it and the diagnostics printed;
fix what it refuses (see [rdf.md](./rdf.md)), and the document is done. The
project's own `.rdf` corpus went with the parser; the two historical fixtures
that survive, embedded in `tests/02_basetest/convert/test_rdf2yaml.py`, convert
to their hand translations exactly, and the decisions the translation could not
make mechanically are pinned in `tests/02_basetest/yaml_loader/test_yaml_corpus.py`.

## Convert video files and generate poster_frame_images

Use `scripts/convert_video.py` to convert video files to PowerPoint-friendly MP4 files.

```
python scripts/convert_video.py [-o DIR] [-f] video_file.xxx [more ...]
```

`scripts/convert_video.sh` does the same thing and takes the same options; it
is the original Bash implementation, kept for machines where a shell is
closer to hand than a Python. Either may be used, and both ship.

- `-o`, `--output DIR` — write the results to `DIR` instead of beside each
  input. The directory is created if it does not exist.
- `-f`, `--force` — redo what is already there. Without it an existing MP4,
  poster frame or metadata file is left alone and reported as skipped.

A path may be a directory, in which case the supported files inside it are
found recursively.

The scripts rely on `ffmpeg` **and `ffprobe`** — the second reads the
dimensions — and are able to convert
 `avi`, `mkv`, `mov`, `mpg`, `mpeg`, `wmv`, `flv`, `webm`, `m4v`, `gif`, `qt`, `3gp`

`mp4` is accepted as well, but is **not converted**: the format is already the
one being produced, and re-encoding it into itself would cost quality for
nothing. What an MP4 is passed in for is the other two products — the poster
frame and the metadata — which a video may not have yet, and those are made
as for any other input.

Each input yields three files named after it: `<name>.mp4`, the poster frame
`<name>_poster.jpg`, and `<name>.metadata.json` carrying the source, the two
file names and the video's width and height.

The poster frame is required when adding a video using `python-pptx`:

```
add_movie(movie_file: str | IO[bytes], left: Length, top: Length, width: Length, height: Length, poster_frame_image: str | IO[bytes] | None = None, mime_type: str = 'video/unknown')
```

and written in a report document as:

```yaml
- video:general: {file: harmonic.mp4, image:poster: {file: harmonic.jpg}}
```
