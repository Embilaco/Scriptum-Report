# About tags and tag formats
A tag is a string like this

`<this:tag argument1 argument2>`

which is an opening tag that requires a closing tag:

`</this:tag>`

This

`<simple:tag/>`

is a simple tag since it closes itself

## Quotes

Quotes "" or '' are not used inside tags which is against [XML specs](https://www.w3.org/TR/xml/). However, Word is mangling this text and the quotes here are Unicode characters different to Python quotes. Thus, in contrast to XML specs it is
`<image:generic width=9cm>` instead of `<image:generic width="9cm">`.
Nevertheless, this template follows XML-syntax as far as possible.

## Span

It is *not* possible to have tags span multiple paragraphs! Thus `<` cannot be in one paragraph while the closing `/>` is in the next paragraph.

Tags are not case sensitive: `<a/>` is the same as `<A/>`

## Regex

This is the current regular expression used to find the tags:

`'[a-z]+[a-z0-9_\- :;,=]*'`

which means: we always ever start with a letter. This might evolve, but some limits should kept in mind:

## Namespaces

A tag is this:
`namespace:name` or `name` only, both have to start with a letter and cannot include and non-ascii letters, but may include numbers.
Arguments after a ` ` blank cannot include colons `:` or blanks themselves; the blank divides different arguments. An argument can carry a value with `=`, as in `width=9cm`.

## Other characters

 * Comma `,` or semicolon `;` are useful only in `<comment: bla, bla, bla/>` which is an ignored tag
 * The equal character `=` gives an argument a value. Two kinds are read: `width=` and `height=` on an image — a number with a unit, `mm`, `cm`, `in`/`inch` or `pt`, as in `width=9cm`, and anything else is ignored — and `id=` below. Sizes and offsets can also come from the report document as *modifiers* (`width`, `height`, `top`, `left`, `bottom`, `right` — see [rdf.md](./rdf.md)); those are written in the document, never in the tag.

## Special arguments:

 - `id=N` — the **instance number**. A tag without it is instance 1, which is what lets a pristine template be read without editing it; when a block is cloned, only the *opening* tag of the clone is numbered (`<subsection:foo id=2>`), never the closing one, exactly as XML puts attributes on the opening tag. Numbering rather than renaming is what keeps a `_global_` fill — which matches on the plain `namespace:name` — reaching every clone.

 - `template` (not used in Powerpoint)

The `template` argument flags a block as a *blueprint*: every instance the report document writes is a clone, the first included, and each further instance is placed directly behind the one before it — so whatever the template holds between two blocks stays behind all of them. **A block can only be repeated if it carries the argument**: without it a block is filled where it stands, and a second instance of it is refused with a message naming the block and the argument to add. A blueprint is pruned from the finished document whether it was used or not, and wherever it stands — a `table:`/`image:` block flagged in the content included. A blueprint may live in `<section:template>` or, flagged this way, anywhere — see [rdf.md](./rdf.md) for the lookup rules when a name exists in both places. The argument belongs on the opening tag only.

### Example:

`<a template>
Foo
</a>`


 - `breakbefore` (not used in Powerpoint)

Puts a page break in front of the block — in front of **every instance except the first**. Instance 1 starts wherever the blueprint stands and needs no break to get there; the ones that follow it do. So a block flagged this way but used only once comes out with no page break at all, and if the first one is to start on a fresh page too, the template says so itself with a break of its own in front of the blueprint.

### Example:

`<a template breakbefore>
Foo
</a>`

### Fixed tag naming
These tags are predefined
 - Sections – `section:foo` - used in Word, together with `subsection:...`, `subsubsection:...`, `sub3section:...`, `sub4section:...`, `sub5section:...`. The ladder is mandatory and has no gaps: to nest at depth two the depth-one parent has to be written.
 - Slide - `slide:foo` - used in Powerpoint, but only as the name of the slide template
 - Images – `image:foo`
 - Videos - `video:foo` (Powerpoint only)
 - Tables – `table:foo`
 - Markers – `marker:foo`
 - Comments - `comment`
 - Text - `text:foo` - in general everything might be a text, so `text` is not reserved, but good practice
 - Ignore - `<ignore:foo all below/>` - everything after it in that section is left alone, tags and all. Written for a documentation section that shows tags as text and would otherwise report them as errors; it takes **both** arguments or it does nothing.
