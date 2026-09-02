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
> below, written as YAML structure instead of prefix characters — and
> `scripts/rdf2yaml.py` converts an existing `.rdf` base into a starting
> point, marking what needs a human with `# CHECK:` comments (see
> [tools.md](./tools.md)).

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
| `dateformat` | strftime pattern | default `'%Y-%m-%d'`, used by `{date: today}` |
| `datetimeformat` | strftime pattern | default `'%Y-%m-%d %H:%M:%S'`, used by `{date: now}`, by timestamps and by timestamps in parameter files |
| `nvseparator` | one character | between name and value in parameter files, default `:` |
| `csvseparator` | one character | between CSV columns, default `;` |
| `floatformat` | Python format spec | how a float is written, default `7.4f` |
| `documenttitle` | text | default `Autoreport` |

See <https://docs.python.org/3/library/datetime.html> for the strftime
patterns; an empty pattern, or one `strftime` rejects, is refused. There is
deliberately no `timeformat`: times come from `datetimeformat` or from a
`format` on the value.

**Why the defaults are ISO 8601.** A document that says nothing about formats
renders `2026-08-23` and `2026-08-23 14:05:09` — the same in every process,
on every machine, unambiguous between day and month, and sortable. Until
2026-08-23 the defaults were the C library's locale forms `'%x'` and `'%c'`:
in a plain Python process those are the C locale (`08/23/26`,
`Sun Aug 23 14:05:09 2026`, US order and English weekday), but they change
the moment the host process calls `locale.setlocale` — a notebook, a GUI, a
service — so the same document rendered `23/08/2026 14:05:09` there. A
report's dates should not depend on who launched the process.

What you can do instead, per document or per value:

- set `dateformat` / `datetimeformat` in `_scriptum_` to whatever house style
  the report wants — `'%d. %b %Y'`, or `'%x'` / `'%c'` if the locale's own
  forms are wanted knowingly;
- give one value its own `format`: `{date: now, format: '%H:%M'}`;
- for a literal date that must appear exactly as written, write it as text —
  `date:published: 01. August 2020` is a string, not a date.

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
instance fills the block the template already contains.

**Naming the same address twice in the same parent requires the template tag
to carry the `template` argument.** Such a block is a *blueprint*: it is never
content, every instance of it is a clone -- the first included, standing
exactly where the blueprint stands -- and the blueprint itself is removed at
the end, used or not. A block without the argument can be filled but not
repeated; a second instance of one is refused with a message naming the block
and the argument to add. Each further instance is placed directly behind the
one before it, so anything the template holds between two blocks stays behind
all of them. PowerPoint copies always.

**An address is positional: the block has to be in the template at that
place.** The document nests the way the template nests, and every entry is
looked up inside the parent that was named — so a `sub3section:step` written
under `subsection:beta` finds nothing when the template holds
`<sub3section:step>` under `subsection:alpha` instead. Nothing is searched for
document-wide here. The entry, and everything under it, is dropped, and the
run says so — one line naming the block, the parent that does not hold it and
the parent that does:

```
WARNING: Nothing to apply at <the address you wrote> - 'subsection:beta' holds no
'sub3section:step'; it stands under <where it really is>, and an address is positional
```

followed by one `cannot find parent structure` for each task that depended on
the entry: every fill inside it, and any marker `add`. So every element you
mean to address needs a blueprint of its own, standing under the parent the
document will name it under, and carrying a name that is unique in the
document — the marker lookup below has nothing but the name to go on.

**A marker is the one way to place content that is nowhere in the template
already.** Unlike a container address, a marker entry is looked up by *name*
across the whole document, so it reaches a blueprint wherever one stands; and
a blueprint that belongs to no section of its own lives in
`<section:template>`, the section at the end of a template that holds nothing
but blueprints. That is what it is for — see *Markers and adding content*
below.

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
address names — `image:generic`, `table:generic` — and places it *before* the
markers paragraph.
The block may live in `<section:template>` or carry the `template` argument
anywhere in the document; if the same name exists in both places, the template
section wins and the run warns about the ambiguity. A fill *outside* a marker
never creates anything: it targets something the template already contains.
Markers may repeat and may interleave with fills.
Anything added at a marker takes its formatting from the block in the
template, not from the marker — the template owns how a thing looks, and the
block is where that was decided.

**Indentation is the exception a template can ask for.** A blueprint carries
the indent of wherever it was written, and `<section:template>` is nowhere in
particular, so a block added at a marker deep inside a subsection arrives at
the left margin between paragraphs that sit well inside it. A marker that
writes `takeindent` donates its own indentation to whatever is added there:

```
<marker:content takeindent/>
```

Everything added moves by the same amount — the marker's indent less the
block's own first line — so a block that indents internally keeps its shape,
and a table moves with its caption. Nothing else is taken: the style, the
fonts, the colours and the spacing stay the block's own. The flag sits on the
marker because the marker is the donor: one blueprint is added at many markers
of many depths, and only the marker knows which of them it is. Word only — a
PowerPoint paragraph indents by outline `level`, which is not a measurement.

Taking the marker's *style* as well is a separate question and is deliberately
not implemented: a marker paragraph's style would be imposed on every
paragraph of a multi-paragraph block, flattening the one thing a block is for,
and its character formatting belongs to a run nobody ever styled on purpose,
the marker being invisible in the finished document.

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

File-backed values — text files, parameter files, CSVs — are read as **UTF-8**
on every platform. (Until 2026-08-24 text and parameter files were read in the
platform encoding, so the same document rendered umlauts differently per
machine; a legacy ANSI-encoded file with non-ASCII content now fails loudly
instead of appearing to work.)

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

#### Text blocks and their placeholders

A `text:` block in `<section:template>` is several paragraphs the template
keeps together — a standard clause, a disclaimer, a form of words — and a
document adds it at a marker. The block **already carries its text**, so
there is nothing for the document to supply except the gaps left in it. Those
gaps are ordinary tags standing inside the block, and the document names them
one by one:

```
<text:complex>                            - marker:content:
We may add more complex texts with            - text:complex:
a <placeholder:one/> or a                         placeholder:one: a first one
<placeholder:two/>                                placeholder:two: {file: note.txt}
or further text with more targets…
</text:complex>
```

Each entry is a [modifier](#modifiers), matched to a tag by the name the
template spells. It takes any form a value takes, so a placeholder may come
from a file, a parameter file or a date just as a plain fill may.

This is the one address that needs **no source key**: `file:`, `text:` and
the rest name where bytes come from, and a text block has its bytes already.
Every other namespace still requires one — for a picture or a table a missing
source is a real mistake, and the run still says so.

Writing a value **at the block** rather than at a placeholder — `- text:complex:
some words` — puts it nowhere, and the run says that too:

```
WARNING: 'text:complex' is a text block and carries its own text, so 'some words'
is written nowhere - name one of its placeholders instead: placeholder:one, placeholder:two
```

The document alone cannot be checked for this: `- text:green: some words` is
the same line and perfectly right when `<text:green/>` is a plain tag rather
than a block. Only the template says which it is, so only the run can tell
you.

A placeholder the document does not mention is **blanked**: the tag is
removed and the prose closes over the gap. Nothing is reported, because a
block is prose and a half-filled one is still prose; a visible
`<placeholder:two/>` in a finished report is the worse outcome.

Naming is free — `<placeholder:one/>` and a bare `<subtitle/>` are matched
the same way — but a bare name shares its space with the source keys and the
lengths (`file`, `text`, `date`, `parfile`, `numbering`, `from`, `rows`,
`width`, `height`, `top`, `left`, `bottom`, `right`). A template that calls a
slot `<text/>` or `<width/>` will be read as saying something else. Prefer
the namespaced form; see [tags.md](./tags.md).

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

**What a modifier carries.** A modifier whose name is a namespace of its own
— `image:poster`, `table:x`, `color` — carries a value of that kind. Every
other modifier carries **words**: `description: {file: caption.txt}` writes
what the file says, and so does a placeholder in a text block.

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
