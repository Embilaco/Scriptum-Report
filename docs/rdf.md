# Report Data File

RDF (Report Data File) is a text file format that allows to connect content with the layout. It is the fuel for the driver Scriptum, how to add and place the content into the templates.

The tags described before are internally split and converted to "addresses" for the elements that will be further used.

## General rules

There are some rules to be aware:
 - empty lines and lines starting with a hash (#) will be ignored
 - empty characters at the beginning and the end of the line will be ignored
 - lines starting with a star * (`*version` for example) contain global settings, see below

Further: 
 - in general (but not always) lines are build as `address=value`
 - each line is or requires an address to a XML tag described before
 - values contain the content finally added to the place where the XML tag is just a placeholder
 - everything that serves as an address is not case sensitive, while the values (after the = sign) the case is preserved
 - lines starting with a character are absolute addresses (`section:title` for example)
 - lines starting with a period `.` (`.report:what` for example) are relative addresses added to the previous absolute address (for example `section:title.report:what` is the tag `<report:what/>` inside the section `<section:title>`
 - lines starting with a at-sign `@` (`@marker.content` for example) will take the next lines of content starting with a `+`(see next item) and place them where the tag `<marker:content/>` was found.
 - lines starting with a plus `+` (`+image:generic=` for example) are used to place elements from the template `<image:generic>` into the current position defined by `@` before
 - lines starting with `&` (`&include` for now only) reads one or many other RDF-files recoursively as if they were exactly included at this position
   - `&include@marker:foo+=loopfiles:some*.rdf` combines the inclusion, but adds (`+`) everything that comes inside the files at (`@`) the marker defined by `marker:foo`. It should be noted that a subsequent marker inside those files resets the marker and probably cause unexpected results.
   - `&include=file:title.rdf` simply add the content of file `title.rdf` as if it is written here
   - `&include+=file:title.rdf` does the same but expects a preceeding marker `@somewhat` 
 - values are described in more detail below, however they may contain quite complex content which is hopefully sufficient for all requirements. 

Although many combination are possible and many were already tested, this model may have some gaps and unexpected results. If you cannot fix it by redesign, feel free to send me a note. If there is anything missing, please feel free to contact me as well.
 

## Settings
Line starts always with `*` and has to be used in the `master` rdf-file, multiple definitions may cause unexpected results 

Supported:
 - `*version`, usually just 3
 - `*documenttype`, mandatory, either `docx` or `pptx`  
 - `*documenttitle`, a general document title, defaults to `'Autoreport'`
 - `*dateformat`, when there is a date required, see https://docs.python.org/3/library/datetime.html
 - `*datetimeformat`, when there is a date and time required, see https://docs.python.org/3/library/datetime.html
 - `*datadir`, instead of having all the input in the current directory use this relative (or absolute - not recommended) address
 - `*nvseparator`, how to split name-value data in files, defaults to `:`, valid for all files
 - `*csvseparator`, how to split columns in csv-files, defaults to `;`, valid for all files
 - `*floatformat`, how floats are converted to a string, defaults to `7.4f` 

## global

The address `global`is special. It just means: enter the content of the following lines everywhere in the model independent from the full address. Thus, no template or other target can be named `global`.


<div class="alert alert-info"><h4>Note</h4><p>
    This is usually done <b>after</b> everything else has been filled.
</p></div>

## Content

Currently supported content

 - Text
 - Tables
 - Pictures
 - Videos (for now and the future: only in Powerpoint)
 - Parameterfiles
 - Date and time objects

### Text
    
`text:foo='a foo text'`
add text as is into the document

`text:foo=file:somefoofile.txt`
add text read from file into the document

### Table

`+table:default=file:tools.csv+description='foo'`
adds table from template named `table:default` and fill it from file. Whenever `description` is possible from the template and added here, it may take the given string or, using `+description=@row1` will read it from the csv-file, first line.

`*csvseparator` changes the character used in the csv to devide between columns

### Picture

`+image:generic=file:sxmbootseal-contours.png+description='Contours of stresses in the seal.'`
adds an image using template `image:generic`, add file given, and adds description if possible. Further parameters like `scale`, `height`, and `width` can be given.

### Video

`+video:generic=file:harmonic.mp4+image:poster=file:harmonic.jpg+description='an animated thing'`
add video using address, add file given, adds a poster image and a description. Valid for `*documenttype=pptx` only.

### Parameterfile

`.datesim=parfile:SomeParameters.nv:Modified`
add a date read from a parameterfile `name:value` given the name of the file and the name of the parameter (case sensitive).

`*nvseparator` changes the character used beteeen `name`and `value`

### Date and Time

`.created=date:now:'%d. %b %Y -- %H:%M:%S'`
add a date and time of type "now" to the address given in the format given
