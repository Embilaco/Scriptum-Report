# Scriptum - A Python Report Generator

by Thomas Emmel, temmel007@gmail.com

## Preface

this document is "work in progress"
 - Such a package is always *not* perfect
 - Documentation grows with its usage and its users
 - conclusion: feedback is required

## Content

 1. Overview
 2. The templates
 3. The report documents
 4. Run and finish
 

## 1. Overview

First of all, and to be crystal clear, this package is not meant for creation of single documents, but to simplify when you have to create all kind of reports over and over again, while keeping some kind of basic layout and formatting, changing only the content!

Scriptum is not build from scratch, it works only with the python packages python-docx and python-pptx written by many and authored by [Steve Canny](https://github.com/scanny), see sources on GitHub:
 - python-pptx: https://github.com/scanny/python-pptx, https://python-pptx.readthedocs.io/en/latest/
 - python-docx: https://github.com/python-openxml/python-docx, https://python-docx.readthedocs.io/en/latest/

Both packages facilitate the XML-syntax given by Microsoft (https://docs.microsoft.com/en-us/dotnet/api/microsoft.office.core) for these document formats, thus they are quite open and flexible, even if not everything is obvious and simple.

It is - as long as documents are created, opened or changed - independent from the underlying system. Thus it runs on any OS as long as the Python packages are available. However, certain things in Microsoft documents require the tools themselves, for instance a TableOfContents object cannot be updated from Python, it requires a running Word (c). Thus the final touch requires the tools themselves; it uses the win32com.client API from the optional `pywin32` package (`pip install Scriptum-Report[windows]`), and there has been no testing of how to do this in the context of Office 365.

Scriptum tries to mimic the LaTeX principles to separate content and mark-up. It further takes the concept of a "style" represented by a template and transfers everything, repeatable and automatable to Microsoft Office.

## 2. The templates

A Scriptum "template" is PPTX- or a DOCX-file that contains some fixed content, for instance a company logo, headers, footers and variable content in a most flexible way, "master slides", "sections" and so on. It may contain some colors and even more, although the package currently relies mostly on the styles used by Microsoft and contains lot of room for further improvements.

Microsoft Office files are themselves based on a XML-Spec (https://en.wikipedia.org/wiki/Office_Open_XML), which is used in the background in python-docx and python-pptx. Scriptum adds another layer of "pseudo XML-like syntax" to it by structuring the documents, the slides and sections into pieces following a strict XML definition. However, neither Word, nor PowerPoint are quite usable XML-editors and thus some derivations from the [XML specs](https://www.w3.org/TR/xml/) was necessary:
 - XML tags can be defined as usual, using a open `<tag>` + close `</tag>` syntax, or a self-closed `<tag/>` syntax
 - Tags are **case insensitive** and some restrictions are required due to limitations in the Microsoft Office documents, the exact definition is described in [tags.md](./tags.md)
 - A wrong tagging in the context of a wrong XML syntax will either be detected by Scriptum or it causes an error during execution. Thus, it is always wise to test and check before running productive.

### 2.1 Word templates

Word can structure documents in so-called "sections" (Layout -> Breaks -> Section Breaks) which are used in the templates and "connected" to the XML `<section:name>`+`</section:name>`. A Word template needs no particular section. `<section:template>` is where blueprints that belong to no section of its own live — everything that can be added at a `<marker:foo/>` — and typesetting removes it at the end of the run; a template without one builds normally and says so once, since a blueprint flagged `template` anywhere in the content works just as well. The content sections may be named anything and there may be any number of them, `<section:title>` being a convention of the shipped templates rather than a rule. Any tag between a closing section and the next opening is ignored. All text in that space between may appear or not in the final document.

The `<section:template>` contains several templates for tables, figures and paragraphs that can be reused at most locations in the document. The `<section:title>` contains - o wonder - the title and things in that context like a table of contents if required. 

Every other `<section:xxx>` stays where it is and as it is.

Nesting elements like `<subsection:...>` can be reused inside the parent element as long as there is a `template` argument in the nesting element. It will be just handled as a template and reused when requested. Every element the report document addresses needs such a blueprint of its own, standing under the parent the document names it under and carrying a name that is unique in the document: an address is positional, so a `<sub3section:step>` that sits under `<subsection:alpha>` cannot be addressed under `<subsection:beta>` — that entry is dropped with a warning. Content that exists in no section at all can only be placed through a `<marker:foo/>`, from a blueprint in the `<section:template>` at the end of the template.

A `breakbefore` argument puts a page break in front of the element, before every instance of it **except the first** — that one starts where the blueprint stands and needs no break to get there. A block flagged this way and used once therefore gets no page break; put one in the template itself, in front of the blueprint, if the first is to start on a fresh page as well.

A `<marker:foo/>` tag is used to place the content into different nested levels. 

Headers and Footers contains only simple self-closing tags. At least complex open/closed tags were not tested intensively.

### 2.2 Powerpoint templates

Powerpoint uses itself uses so-called "layouts" (View -> Slide Master) to define new type of slides and layouts. Scriptum just takes these layouts and place them as new slides into the final presentation. `<tag>` + `</tag>` is usually an exception since most elements can be addressed directly with a self-closed `<tag/>`.

A `<marker:foo/>` tag is used to place more content usually on the free area of the slide.

The size of the content depends on the final requirements and it is simple to mess up a slide.

Color management is yet in development as many other features are.

## 3. The report documents

The report data file is a YAML document (`.yaml`) that connects content with the layout. It is the fuel for the driver Scriptum, how to add and place the content into the templates: its structure nests the way the template nests, every entry names a tag of the template as its address, and the value is what goes there.

The tags described before are the "addresses" the document writes against.

This is a huge chapter for itself and thus details can be found in [rdf.md](./rdf.md). (Earlier versions read a hand-written line format with the extension `.rdf`; it is gone, and `ReportDataFile` reads `.yaml` only.)

## 4. Run and finish

(prereq: change to the folder where the files below are located and Scriptum is in your environment, see the Install section of the README)

Finally, this is quite simple as:


```python
import Scriptum
rdf = Scriptum.ReportDataFile('report_word.yaml')
mydoc = Scriptum.ManagedDocx('template.docx')
mydoc.typesetting(rdf)
mydoc.save('result_word.docx',finish=True, createpdf=True)
```

    setting the letters:
     ...
    done
    

or 

```python
import Scriptum
rdf = Scriptum.ReportDataFile('report_ppt.yaml')
myppt = Scriptum.ManagedPptx('template.pptx')
myppt.artist(rdf)
myppt.save('result_powerpoint.pptx',finish=True, createpdf=True)
```

    painting the shapes:
     ...
    done
    


The arguments `finish=True` and `createpdf=True` take effect on Windows only, with an installed Word or PowerPoint respectively: the finished file is re-saved by the Office application itself and, with `createpdf=True`, exported as a PDF beside it. Elsewhere they are ignored with a message.

