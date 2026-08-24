#
# how to create this document manually
# Scriptum has to be in PYTHONPATH
#
# call this script using python >= 3.10 with installed python_pptx
#
import Scriptum

base_rdf = 'powerpoint_input.yaml'
rdf = Scriptum.ReportDataFile(base_rdf)

document = Scriptum.ManagedPptx('template.pptx')
document.artist(
    rdf,
    directfill=True,
    globalfill=True,
    cleardust=True,
    setproperties=True,
)

document.save('final_report.pptx', finish=True, createpdf=True)
