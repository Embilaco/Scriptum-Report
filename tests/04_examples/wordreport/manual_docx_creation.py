#
# how to create this document manually
# Scriptum has to be in PYTHONPATH
# data-dir has to created linked here
#
# call this script using python >= 3.10 with installed python_docx
#
import Scriptum

rdf = Scriptum.ReportDataFile('word_input.yaml')

document = Scriptum.ManagedDocx('template.docx')
document.typesetting(
    rdf,
    addcopy=True,
    directfill=True,
    globalfill=True,
    cleanup=True,
    removetemplate=True,
    cleardust=True,
    setproperties=True,
)

document.save('final_report.docx', finish=True, createpdf=True)
