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

 * Comma `,` or semicolon `;` are useful only in `<comment: bla, bla, bla/>` which is a ignored tag
 * The equal character `=` gives an argument a value: `width=`/`height=` on images, `name=` in the config-table tags.

## Special arguments:

 - `template` (not used in Powerpoint)

The `template` argument flags a block as a *blueprint*: every instance the report document writes is a clone, the first included, and further instances follow the last one used. A section-ladder blueprint is pruned from the finished document; a `table:`/`image:` block flagged in the content ships unchanged if unused. A blueprint may live in `<section:template>` or, flagged this way, anywhere — see [rdf.md](./rdf.md) for the lookup rules when a name exists in both places. The argument belongs on the opening tag only.

### Example:

`<a template>
Foo
</a>` 


 - `breakbefore` (not used in Powerpoint)

when the element is copied a template it creates a pagebreak before that element

### Example:

`<a template breakbefore>
Foo
</a>`

### Fixed tag naming
These tags are predefined
 - Sections – `section:foo` - used in Word, together with `subsection:..`, `subsubsection:...`, `sub3section:...`, `sub4section:...`,`sub5section`. 
 - Slide - `slide:foo` - used in Powerpoint, but only as the name of the slide template
 - Images – `image:foo`
 - Videos - `video:foo` (Powerpoint only)
 - Tables – `table:foo`
 - Markers – `marker:foo`
