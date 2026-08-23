# The report document

The *report data file* is a YAML document (`.yaml`) that connects content with
a template. It is the fuel for the driver Scriptum: what to put where. The
template owns how the report looks; the document owns what it says.

The tags described in [tags.md](./tags.md) are the **addresses** the document
writes against: `section:title` in the document is the `<section:title>` tag in
the template, `head` is `<head/>`.

> Scriptum used to read a hand-written line format with the extension `.rdf`.
> That format is gone; `ReportDataFile` reads `.yaml` only and refuses anything
> else with a message. Every construct of the old format has an equivalent
> below, written as YAML structure instead of prefix characters.

## The whole format on one screen

```yaml
_scriptum_:
  version: 4
  documenttype: docx
  datadir: ./data

_global_:                              # a mapping: no dashes, no repeats
  report:id: ID 4711
  report:status: Draft

_content_:
  - section:title:
      - report:product_name: A pudding
      - image:mainmodel: {file: pudding.jpg}
      - date:creation: {date: now}

  - section:instruction_bc:
      - text:description: These are the cooking instructions

      - subsection:instruction:
          - head: Instruction 1
          - marker:content:
              - image:generic: {file: instruction1.png, description: instruction one}

      - subsection:instruction:            # second instance -> a clone
          - head: Serving
          - marker:content:
              - _include_: 'fragments/serving-*.yaml'
```

Three ideas carry everything:

- **One entry, one address.** Every item in a content sequence is a mapping
  with exactly one key, and that key is an address — `namespace:name`, spelled
  the way the template spells its tag.
- **The value's kind says what the entry is.** A *sequence* is a body (a
  section, or the list of things to add at a marker); a *scalar* or a *mapping*
  is a fill; *nothing* (`- section:x:` with no value) is a container with an
  empty body.
- **Repetition is what the sequence is for.** Writing the same address twice in
  one parent means two instances — the second `subsection:instruction` above is
  a second, cloned subsection. Nothing is renamed; instances are numbered in
  the order they are written.

## General rules

- Keys — addresses, reserved keys, modifier names — are **case-insensitive**;
  values keep their case.
- An address is made of segments separated by `:`; each segment starts with a
  letter and contains only letters, digits, `_` and `-`. No address begins with
  `_`, which is what keeps the reserved keys (`_scriptum_`, `_global_`,
  `_content_`, `_include_`) out of every author's way.
- The document is **executed top to bottom**. A container comes before its own
  children, and moving an entry can change the output even when the entry
  itself did not change (PowerPoint in particular carries a "current slide"
  through the list).
- Indentation is structure, as in every YAML file. Two spaces per level is the
  convention used here; be consistent within a file.
- A document with mistakes is refused **as a whole**, with every problem
  listed — file, line, column and the path through the document — rather than
  the first one only.

## Settings — `_scriptum_`

A mapping in the root document, and only there. Unknown keys are an error.

| Key | Value | Notes |
|---|---|---|
| `version` | integer | `4` for this format; lower is refused |
| `documenttype` | `docx` or `pptx` | required; it selects the section ladder below |
| `datadir` | path | where `file:` values are looked up; must exist; **relative to the document** |
| `dateformat` | strftime pattern | default `'%x'`, used by `{date: today}` |
| `datetimeformat` | strftime pattern | default `'%c'`, used by `{date: now}` and by timestamps |
| `nvseparator` | one character | between name and value in parameter files, default `:` |
| `csvseparator` | one character | between CSV columns, default `;` |
| `floatformat` | Python format spec | how a float is written, default `7.4f` |
| `documenttitle` | text | default `Autoreport` |

See <https://docs.python.org/3/library/datetime.html> for the strftime
patterns; an empty pattern, or one `strftime` rejects, is refused. There is
deliberately no `timeformat`: times come from `datetimeformat` or from a
`format` on the value.

The two defaults, `'%x'` and `'%c'`, are the C-library's locale forms. In a
plain Python process that is the C locale — `08/23/26` and
`Sun Aug 23 14:05:09 2026` — but they change the moment the host process
calls `locale.setlocale` (a notebook, a GUI, a service): the same document
then renders `23/08/2026 14:05:09`. If a report must read the same
everywhere, set `dateformat` and `datetimeformat` explicitly; an ISO pattern
such as `'%Y-%m-%d'` / `'%Y-%m-%d %H:%M:%S'` cannot be misread.

## Content — `_content_`

A sequence of entries. How deep an entry sits decides what it must be called:

- **Word (`docx`)** has a mandatory ladder, `section` → `subsection` →
  `subsubsection` → `sub3section` → `sub4section` → `sub5section`. An entry at
  the top level must be a `section:…`, one inside it a `subsection:…`, and so
  on. A gap cannot be written: to nest at depth two you have to write the
  depth-one parent.
- **PowerPoint (`pptx`)** has one level, the slide, addressed by its **layout
  name** — a bare `TitleSlide:` or `slide:TitleSlide:` both work. Every mention
  of a layout is a new slide.

A **container** (a section or a slide) has a sequence as its value. Its first
instance fills the block the template already contains; further instances of
the same address in the same parent are clones of it. A block whose template
tag carries the `template` argument is a *blueprint* and is cloned for every
instance, the first included. PowerPoint copies always.

A **fill** has a scalar or a mapping as its value — see *Values* below.

### Markers and adding content

A marker is an entry in the `marker` namespace whose value is the sequence of
things to add at the `<marker:name/>` tag of the template:

```yaml
- subsection:instruction:
    - head: Instruction 1
    - marker:content:
        - image:generic: {file: instruction1.png, description: instruction one}
        - table:generic: {file: tools.csv, description: {from: row1}}
```

Each entry inside a marker creates a new element from the template block its
address names — `image:generic`, `table:generic` — and places it at the marker.
A fill *outside* a marker never creates anything: it targets something the
template already contains. Markers may repeat and may interleave with fills.

### Includes

```yaml
- _include_: sections/intro.yaml
- _include_: 'fragments/part-*.yaml'
```

`_include_` is legal wherever an entry is: in `_content_`, in a section body,
inside a marker. The fragment's entries are spliced **where the entry sits**,
so the including document decides where they land and at which level — a
fragment is a bare sequence of entries, carries no settings and no `_global_`,
and can therefore be included in more than one place, or twice in the same
place (each copy becomes its own numbered instance).

- A path is relative to the **file doing the including**, not to the working
  directory.
- Glob matches are sorted, so a run is reproducible.
- A missing file, an empty glob, and a file that is still open further up the
  include chain (a cycle) are errors; including depth is capped at 10.

Includes exist for **reuse**: a chapter such as *experimental results* that
recurs across reports with the same structure and different content is written
once and pulled in wherever it is needed.

## Global content — `_global_`

A mapping in the root document. Each address in it is filled **everywhere** in
the document where the tag occurs — headers, footers and body alike, every
clone included — and it is applied **after** everything else. It is a mapping
rather than a sequence because each address there is filled once, everywhere;
there is nothing for a repeat to mean.

```yaml
_global_:
  report:id: ID 4711
  report:status: Draft
  date:creation: {date: now, format: '%d. %b %Y'}
```

## Values

A fill's value is either a **scalar** or a **mapping with one source key**.

### Scalars

```yaml
- head: Serving              # the string
- report:version: 1.0        # the float, written with floatformat
- value:count: 42            # the int
- rf2: ''                    # the empty string
```

A scalar is typed by YAML, not by quoting — `Serving` and `'Serving'` are the
same string. Quoting is still the recommended house style for prose (see
*Quoting* below), and it is **required** when the text contains characters YAML
reads as structure.

`true`/`false` are refused as values (quote the word if you mean it), and a
colour target (`color`, or any `color:…` address) reads its value as a colour:
a name (`red`, `steelblue`), six hex digits with or without `#` (`ff0000` —
unquoted `#ff0000` is a YAML comment), or `rgb(255, 0, 0)`. An unrecognised
colour is an error rather than silently black.

### Mappings: where the bytes come from, and how

Exactly **one source key**, its companions, and any number of modifiers:

| Source key | Meaning | Companions |
|---|---|---|
| `file` | a file under `datadir` | — |
| `parfile` | one parameter from a `name:value` file | `parameter` (required) |
| `text` | an explicit string | — |
| `date` | a date or time | `format` (a strftime pattern) |
| `numbering` | a counter | `format` (required), `start` |
| `from` | a value read out of the table itself, e.g. `row1` | — |

**What the namespace of the address says, the source key does not repeat.** A
`file:` under `image:` is an image, under `text:` a text file, under `table:` a
CSV, under `video:` a movie. The address says *what* the bytes are, the mapping
says *where* they come from.

### Text

```yaml
- text:foo: a foo text                 # text as is
- text:foo: {file: somefoofile.txt}    # text read from a file
- text:foo: |                          # several lines, breaks kept
    First line.
    Second line.
```

`"double quotes"` process `\n` escapes; single quotes and plain scalars do
not; a block scalar (`|` keeps line breaks, `>` folds them) is best for
genuinely multi-line text.

### Tables

```yaml
- table:default: {file: tools.csv, description: 'foo'}
- table:default: {file: tools.csv, description: {from: row1}}
```

The table is filled from the CSV (`csvseparator` sets the column separator).
A `description` is written wherever the template's table has a
`<table:default:description/>` child tag; `{from: row1}` takes it from the
first row of the CSV instead.

### Pictures

```yaml
- image:generic: {file: seal-contours.png, description: Contours of stresses in the seal., width: 9cm}
```

Places an image from the template's `image:generic` block, with its
description if the block has one. `scale`, `width` and `height` set the size;
`top`, `left`, `bottom`, `right` offset a PowerPoint template clone inside its
marker.

### Videos

```yaml
- video:generic: {file: harmonic.mp4, image:poster: {file: harmonic.jpg}, description: an animated thing}
```

PowerPoint only. The poster image is mandatory — the video's size is taken
from it, because the video file itself is never opened.

### Parameter files

```yaml
- datesim: {parfile: SomeParameters.nv, parameter: Modified}
```

Reads one parameter out of a `name:value` file (`nvseparator` sets the
separator). Lookup keys are lowercased and stripped of spaces on both sides,
so `Wall Clock Time` and `wallclocktime` are the same key. A missing
parameter or file puts a message into the document instead of stopping the
run.

### Date and time

```yaml
- created: {date: now, format: '%d. %b %Y -- %H:%M:%S'}
- today: {date: today}                       # rendered with dateformat
- stamp: {date: 1231231230}                  # a Unix timestamp, datetimeformat
- fixed: {date: 2022-12-15 14:24:59, format: '%Y-%m-%d %H:%M'}
```

`date` takes *what to evaluate* and `format` the strftime pattern:

- `now` — the current date and time; `today` — the current date. Any case.
- a number — a Unix timestamp; 13 digits or more are taken as milliseconds.
- a date string. Write it **ISO 8601** (`2022-12-15`, `2022-12-15 14:24:59`),
  which needs no quotes and cannot be misread; any other form is read by
  `python-dateutil`, which takes an ambiguous `05/06/22` **month first**, and
  without `dateutil` installed only ISO and a few US-ordered forms are
  recognised at all.

Without `format`, `now` and a timestamp use `datetimeformat`, `today` uses
`dateformat`. A date is evaluated **when the document is read**, in naive
local time — no time zone is ever attached.

What is refused, with a message pointing at the line: a spec that is not a
date (no silent `01. Jan 1970`), a strftime pattern written in the `date`
slot (`{date: '%d. %b %Y'}` — the pattern goes in `format`), an empty or
non-text `format`, and a `format` that `strftime` rejects (Windows rejects an
unknown directive; glibc prints it literally, so that check only bites
there). Timestamps before 1970 are not portable either — Windows refuses them.

A target *named* in the `date` namespace is not special: `date:published: 01.
August 2020` is the text you wrote, verbatim. Only the source key `date`
evaluates anything.

### Numbering

```yaml
- number:fig: {numbering: 1, format: 'Figure %s', start: 1}
```

A counter walked one value per use. `numbering` is the kind — `1` (arabic),
`a`/`A` (letters), `i`/`I` (roman) or `F` (free, `start` being the
`;`-separated values themselves) — `format` a pattern with one `%s`, `start`
the first value. Numbering is only partially wired into the back ends.

### Modifiers

Every key of a value mapping that is neither the source key nor one of its
companions is a **modifier** — `description`, `width`, `height`, `scale`,
`top`, `left`, `bottom`, `right`, `image:poster`, and free-form ones the
template's child tags name. A modifier's value takes the same forms as a main
value (`description: {from: row1}`), but no modifiers of its own.

**Lengths** — `width`, `height`, `top`, `left`, `bottom`, `right` — need a
unit: `cm`, `mm`, `in` (or `inch`), `pt`. `width: 4` is an error, not four of
something implied. A unit suffix on any other value is just text.

## Quoting

YAML gives a few characters structural meaning inside an unquoted value. Put
the value in `'single quotes'` whenever it

- contains a colon followed by a space, or ends with a colon — `'From
  Typewriting to Variable Fonts:'`; unquoted, the text becomes a *key*;
- starts with `- ` (a list item), `? ` (a complex key), `#` (a comment), `&`
  (an anchor — the word is silently dropped), `*` (an alias), `!` (a tag),
  `|` or `>` (a block scalar), `%`, `@`, or a backtick;
- starts with `[` or `{` (a flow sequence or mapping), or contains a comma
  inside a flow mapping — `{color: 'rgb(255,0,0)'}` needs the quotes because
  the commas would split it;
- contains a tab;
- contains a quote: inside single quotes a single quote is written twice,
  `'it''s'`.

Every one of these is **refused with a message that names it** and shows the
value quoted, at the line it is on — except one. ` #` after a value starts a
comment, which is legal and common (`- head: 'Title'  # the main one`), so
`- title: Results #1` silently becomes `Results` and nothing can tell that
from a comment. Quote it: `'Results #1'`. (`Results#1`, without the space, is
fine.)

Leading-zero numbers are integers in YAML (`007` is `7`) — quote a part number
or an extension. House style: quote prose anyway; it makes the boundary of a
value visible and matches the Python the rest of the project is written in.

## Checking a document

`scripts/check_rdf.py report.yaml` reads a document the way Scriptum will and
prints what it refuses, with positions. `ReportDataFile.showFiles()` lists the
files a document names and which of them are missing, before any document
work begins.
