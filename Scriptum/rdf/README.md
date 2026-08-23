# collect classes and functions to read report documents (`*.yaml`)

The package keeps its name -- `rdf`, the *report data file* -- and reads a YAML
document; the hand-written `.rdf` text format it was named after is gone. The
format is described in `docs/rdf.md`.

## MODULE rdf.reportDataFile PROVIDES
   class ReportDataFile - reads a `.yaml` report document and is the entry to all the rest

     * reads the root document and every fragment it `_include_`s, through `rdf.loader`
     * refuses anything that is not a `.yaml`/`.yml` path, with a message
     * extracts "tasks" (list of ReportTask), one per entry of the document: a path, a value, what to do
     * a path is a location inside the document template
     * a value is the content, and an operation (apply/copy/add) is what to do with it
     * tasks may have modifiers - the entry's extra keys
     * a document with mistakes raises with every diagnostic; `errors` holds them as strings
     * `inspect()` - one dict per task; `showFiles()` - which of the files named exist

## PACKAGE rdf.loader PROVIDES
   the YAML reader: dialect (YAML 1.2 core schema), diagnostics, nodes, document, addresses, entries, fills, tasks; `load(path)` is the front door

## MODULE rdf.tasks.report_task PROVIDES
   class ReportTask - what to do, by address and value; the only thing a back end receives

## rdf.values PROVIDES
   class Value - the wrapper a back end reads (type, subtype, tostring, content, load())
   multiple class *Value - value classes for the various values of a ReportTask

## MODULE rdf.namespaces PROVIDES
   the section ladder per document type (`SECTION_NAMESPACES`) and `register_documenttype`
