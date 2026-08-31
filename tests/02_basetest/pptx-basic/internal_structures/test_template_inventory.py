"""The shipped pptx templates, layout by layout, tag by tag.

Every pptx case runs against a copy of the same corporate template --
``../simple/template.pptx`` and the one beside the pptreport example. Until
now only the notebooks in this directory ever looked inside one, so a template
edit that renamed a layout or dropped a tagged placeholder would surface only
as tasks quietly not finding their targets. This pins the inventory a document
can write to: the layout names in order, and per layout the tags of its
placeholders (first line only -- a marker placeholder carries its prompt
levels below the tag).

The ``Config:`` and ``Template:`` layouts deliberately list no tags: they are
read as configuration (colours, table styles, image frames), never copied as
slides, and their machinery is still experimental.
"""

from pathlib import Path

import pytest

pptx = pytest.importorskip('pptx')

THIS_DIR = Path(__file__).resolve().parent
TESTS = THIS_DIR.parents[2]

TEMPLATES = {
    'simple': THIS_DIR.parent / 'simple' / 'template.pptx',
    'pptreport': TESTS / '04_examples' / 'pptreport' / 'template.pptx',
}

#: The layouts, in slide-master order. A document's top-level entries name
#: these; renaming one here without renaming it in the documents strands them.
LAYOUTS = [
    'TitleSlide', 'AgendaSlide', 'Header', 'TaskProjectDefinition', 'Blank',
    'TitleContent', 'Material', 'ResultsTwoBlocks', 'ResultsGeneral',
    'ResultsAnimation', 'BackCover', 'Config:Colors', 'Template:Defaults',
    'Template:Tables', 'Template:Image:1', 'Template:Image:2',
    'Template:Animate:1', 'Template:textblocks',
]

#: What each layout offers a document to fill, as the placeholder tags read.
TAGS = {
    'TitleSlide': ['<title/>', '<subtitle/>', '<created/>', '<revision/>',
                   '<image:main_model/>'],
    'AgendaSlide': ['<item:highlight/>', '<item:other/>', '<title/>'],
    'Header': ['<title/>', '<subtitle/>'],
    'TaskProjectDefinition': [
        '<manu/>', '<plat/>', '<hierarchy/>', '<proj_ver/>', '<prod_ver/>',
        '<group/>', '<date:today/>', '<manager/>', '<proj_no/>', '<glob_no/>',
        '<sop/>', '<mod_ver/>', '<items/>', '<belongs/>', '<plant/>',
        '<report_no/>', '<name:surname1/>', '<name:surname2/>',
        '<name:surname3/>', '<name:surname4/>', '<name:surname5/>',
        '<image:model_icon shape/>', '<Dep:phone1/>', '<Dep:phone2/>',
        '<Dep:phone3/>', '<Dep:phone4/>', '<Dep:phone5/>', '<rf1/>',
        '<rf2/>', '<marker:content/>'],
    'Blank': ['<marker:content/>', '<reference/>', '<date_name/>'],
    'TitleContent': ['<title/>', '<marker:content/>', '<reference/>',
                     '<date_name/>', '<plant/>'],
    'Material': ['<title/>', '<marker:content/>', '<marker:table/>',
                 '<reference/>', '<date_name/>', '<plant/>'],
    'ResultsTwoBlocks': ['<title/>', '<reference/>', '<date_name/>',
                         '<plant/>', '<what/>', '<marker:right/>',
                         '<marker:left/>'],
    'ResultsGeneral': ['<title/>', '<marker:content/>', '<reference/>',
                       '<date_name/>', '<plant/>', '<what/>'],
    'ResultsAnimation': ['<title/>', '<reference/>', '<date_name/>',
                         '<plant/>', '<what/>', '<video:general/>'],
    'BackCover': [],
    'Config:Colors': [],
    'Template:Defaults': [],
    'Template:Tables': [],
    'Template:Image:1': [],
    'Template:Image:2': [],
    'Template:Animate:1': [],
    'Template:textblocks': [],
}


def inventory(path):
    """{layout name: [first line of each placeholder's text]} of a template."""
    deck = pptx.Presentation(path)
    return {layout.name: [(ph.text.splitlines() or [''])[0]
                          for ph in layout.placeholders]
            for layout in deck.slide_layouts}


@pytest.mark.parametrize('name', sorted(TEMPLATES))
def test_the_layouts_a_document_can_copy(name):
    assert list(inventory(TEMPLATES[name])) == LAYOUTS


@pytest.mark.parametrize('name', sorted(TEMPLATES))
def test_the_tags_each_layout_offers(name):
    assert inventory(TEMPLATES[name]) == TAGS


def test_both_case_templates_are_the_same_template():
    """simple and pptreport deliberately ship copies of one template; if they
    drift apart, the two case suites stop testing the same thing."""
    assert inventory(TEMPLATES['simple']) == inventory(TEMPLATES['pptreport'])


@pytest.mark.parametrize('name', sorted(TEMPLATES))
def test_the_template_ships_exactly_one_slide(name):
    """Every run ends with ``remove_slide(0)``: the template's own first slide
    is dropped and only the copies remain. That rests on there being exactly
    one to remove."""
    assert len(pptx.Presentation(TEMPLATES[name]).slides._sldIdLst) == 1
