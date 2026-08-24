#
# how to create this document manually
# Scriptum has to be in PYTHONPATH
#
# call this script using python >= 3.10 with installed python_docx
#
import Scriptum

base_rdf = 'essay.yaml'
rdf = Scriptum.ReportDataFile(base_rdf)

document = Scriptum.ManagedDocx('essay.docx')
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

document.save('final_essay.docx', finish=True, createpdf=True)
