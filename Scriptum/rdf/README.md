# collect classes and functions to read `report-data-files` *.rdf

## MODULE rdf.reportDataFile PROVIDES 
   class ReportDataFile - reads rdf-files and is the entry to all the rest

     * This class reads .rdf-file or nested structures of those
     * It extracts "tasks" (list of ReportTask) from each line of that file which contain  itself path,value pairs
     * a path is a location inside the document
     * a value is the content and operation to be done
     * tasks may have modifiers - describing modifications of the task
     * print(rdf-object) - delivers inspection of the content

## MODULE rdf.tasks.report_task PROVIDES 
   class ReportTask - what to do, finalize the tasks to do by path and value

## rdf.values PROVIDES 
 multiple class *Value - value classes for the various values of a ReportTask