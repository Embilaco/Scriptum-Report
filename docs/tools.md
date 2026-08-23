# Tools and Validation helpers

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

## Convert video files and generate poster_frame_images

Use `scripts/convert_video.py` to convert video files to PowerPoint-friendly MP4 files.

```
python scripts/convert_video.py video_file.xxx
```

The script relies on `ffmpeg` and is able to convert 
 `avi`, `mkv`, `mov`, `mpg`, `mpeg`, `wmv`, `flv`, `webm`, `m4v`, `gif`, `qt`, `3gp`

It creates a "poster_frame_image" which is required when adding a video using `python-pptx`:

```
add_movie(movie_file: str | IO[bytes], left: Length, top: Length, width: Length, height: Length, poster_frame_image: str | IO[bytes] | None = None, mime_type: str = 'video/unknown')
```

and written in a report document as:

```yaml
- video:general: {file: harmonic.mp4, image:poster: {file: harmonic.jpg}}
```
