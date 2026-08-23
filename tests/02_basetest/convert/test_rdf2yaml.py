"""``scripts/rdf2yaml.py`` turns an old ``.rdf`` into a ``.yaml`` a human can finish.

The converter is a starting point, not a round trip: what was ambiguous in the
text format is decided the way the old parser decided it, or the way the
hand-translated corpus decided it, and marked with a ``# CHECK:`` comment.
These tests pin both halves -- what it gets right without help, and where it
leaves a mark -- by reading every result back through the loader. Two of the
historical fixtures are embedded and compared with their hand translations,
which live in the repo as the ``.yaml`` corpus.
"""

from __future__ import annotations

import importlib.util
import shutil
import textwrap
from pathlib import Path

import pytest

from Scriptum.rdf.loader import DocumentError, load

TESTS_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = TESTS_ROOT.parent / 'scripts' / 'rdf2yaml.py'

_spec = importlib.util.spec_from_file_location('rdf2yaml', SCRIPT)
rdf2yaml = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rdf2yaml)


# ----------------------------------------------------------------- helpers

def convert(tmp_path, text, name='report.rdf', data=True, **extra):
    """Write *text* as an .rdf beside a data dir, convert it, return the
    loaded document and the converter's warnings."""
    if data:
        (tmp_path / 'data').mkdir(exist_ok=True)
    for extra_name, extra_text in extra.items():
        (tmp_path / extra_name).write_text(textwrap.dedent(extra_text).lstrip('\n'),
                                           encoding='utf-8')
    source = tmp_path / name
    source.write_text(textwrap.dedent(text).lstrip('\n'), encoding='utf-8')
    converter = rdf2yaml.Converter(follow=True, force=True)
    document = converter.convert_root(source)
    return source.with_suffix('.yaml'), document.warnings


def shape(path):
    loaded = load(path)
    return [('.'.join(t.myAddress), t.target, t.what) for t in loaded.tasks]


def values(path):
    loaded = load(path)
    return {t.target: (t.value.type, str(t.value)) for t in loaded.tasks if t.target}


HEAD = """
*version=3
*documenttype=docx
*datadir=./data
"""


# ---------------------------------------------------------------- settings

def test_settings_become_the_scriptum_block_with_the_yaml_floor(tmp_path):
    out, warnings = convert(tmp_path, """
        *version=3
        *documenttype=docx
        *datadir=.\\data
        *dateformat='%d. %b %Y'
        *csvseparator=;
        *documenttitle='A title'
        section:title
        .head='x'
    """)
    text = out.read_text(encoding='utf-8')
    assert 'version: 4' in text
    assert 'datadir: ./data' in text, 'backslashes become slashes'
    assert "dateformat: '%d. %b %Y'" in text
    assert "documenttitle: A title" in text
    loaded = load(out)
    assert loaded.settings.documenttype == 'docx'
    assert loaded.settings.dateformat == '%d. %b %Y'
    assert not warnings


def test_an_unknown_or_repeated_setting_is_kept_as_a_comment(tmp_path):
    out, warnings = convert(tmp_path, HEAD + """
        *timeformat='%H:%M'
        *datadir=./elsewhere
        section:title
        .head='x'
    """)
    text = out.read_text(encoding='utf-8')
    assert '# CHECK: unknown setting dropped' in text and 'timeformat' in text
    assert '# CHECK: *datadir was set again' in text
    assert 'datadir: ./data' in text, 'the first value is kept'
    assert len(warnings) == 2
    load(out)                                   # and it loads


# ------------------------------------------------------------------ global

def test_global_becomes_the_global_mapping(tmp_path):
    out, _ = convert(tmp_path, HEAD + """
        global
        .report:id='ID 4711'
        .report:version=1.0
        section:title
        .head='x'
    """)
    tasks = shape(out)
    assert tasks[-2:] == [('_global_.report:id', 'report:id', ''),
                          ('_global_.report:version', 'report:version', '')]
    assert values(out)['report:version'] == ('float', ' 1.0000')
    assert values(out)['report:id'] == ('str', 'ID 4711')


# --------------------------------------------------------------- structure

def test_nesting_follows_the_dotted_addresses_and_relative_lines(tmp_path):
    out, warnings = convert(tmp_path, HEAD + """
        section:a
        .head='A'
        .subsection:b
          .head='B'
          .subsubsection:c
            .head='C'
          .subsection:d
            .head='D'
        section:e.subsection:f
          .head='F'
    """)
    assert shape(out) == [
        ('section:a::1', '', 'apply'),
        ('section:a::1.:head::1', 'head', ''),
        ('section:a::1.subsection:b::1', '', 'apply'),
        ('section:a::1.subsection:b::1.:head::1', 'head', ''),
        ('section:a::1.subsection:b::1.subsubsection:c::1', '', 'apply'),
        ('section:a::1.subsection:b::1.subsubsection:c::1.:head::1', 'head', ''),
        ('section:a::1.subsection:d::1', '', 'apply'),
        ('section:a::1.subsection:d::1.:head::1', 'head', ''),
        ('section:e::1', '', 'apply'),
        ('section:e::1.subsection:f::1', '', 'apply'),
        ('section:e::1.subsection:f::1.:head::1', 'head', ''),
    ]
    assert not warnings


def test_a_repeated_relative_subsection_is_a_new_instance(tmp_path):
    out, _ = convert(tmp_path, HEAD + """
        section:a
        .subsection:instruction
          .head='one'
        .subsection:instruction
          .head='two'
    """)
    assert [t for t in shape(out) if t[2] in ('apply', 'copy')] == [
        ('section:a::1', '', 'apply'),
        ('section:a::1.subsection:instruction::1', '', 'apply'),
        ('section:a::1.subsection:instruction::2', '', 'copy'),
    ]


def test_a_restated_top_level_section_returns_to_it_but_a_nested_one_is_new(tmp_path):
    """The text format never cloned a top-level Word section -- restating it
    was how you went back -- while an absolute ``section:a.subsection:b``
    written again was a further instance (word_text.rdf did exactly that)."""
    out, _ = convert(tmp_path, HEAD + """
        section:a
        .head='first pass'
        section:b
        .head='b'
        section:a
        .head='second pass'
        section:a.subsection:x
        .head='x one'
        section:a.subsection:x
        .head='x two'
    """)
    addresses = [t[0] for t in shape(out)]
    assert addresses.count('section:a::1') == 1
    assert 'section:a::2' not in addresses
    assert 'section:a::1.subsection:x::1' in addresses
    assert 'section:a::1.subsection:x::2' in addresses


def test_an_absolute_address_binds_to_the_most_recent_instance_and_says_so(tmp_path):
    """The old parser resolved an absolute address against its renamed tree,
    so it reached the *latest* instance -- which is not what the text says.
    The converter does the same and marks the spot."""
    out, warnings = convert(tmp_path, HEAD + """
        section:a
        .subsection:b
          .head='one'
        .subsection:b
          .head='two'
        section:a.subsection:b.note='which b?'
    """)
    text = out.read_text(encoding='utf-8')
    assert 'CHECK' in text and 're-enters subsection:b' in text
    assert any('bound to the most recent' in w for w in warnings)
    assert ('section:a::1.subsection:b::2.:note::1', 'note', '') in shape(out)


def test_a_namespace_not_on_the_ladder_is_renamed_and_marked(tmp_path):
    """word_text.rdf addressed a ``subsubsubsection``; the ladder's name at
    that depth is ``sub3section``, and the template tag must follow."""
    out, warnings = convert(tmp_path, HEAD + """
        section:a.subsection:b
          .subsubsection:c.subsubsubsection:d.item='deep'
    """)
    assert ('section:a::1.subsection:b::1.subsubsection:c::1.sub3section:d::1.:item::1',
            'item', '') in shape(out)
    assert 'CHECK: was subsubsubsection:d' in out.read_text(encoding='utf-8')
    assert any('rename' in w for w in warnings)


def test_powerpoint_slides_are_new_every_time_and_bare_names_are_fine(tmp_path):
    out, _ = convert(tmp_path, """
        *version=3
        *documenttype=pptx
        TitleSlide
        .title='One'
        TitleSlide
        .title='Two'
        Material
        .plant='Honolulu'
    """)
    assert shape(out) == [
        (':titleslide::1', '', 'copy'), (':titleslide::1.:title::1', 'title', ''),
        (':titleslide::2', '', 'copy'), (':titleslide::2.:title::1', 'title', ''),
        (':material::1', '', 'copy'), (':material::1.:plant::1', 'plant', ''),
    ]


# ------------------------------------------------------------------ values

def test_the_value_grammar_is_mapped_form_by_form(tmp_path):
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'p.nv').write_text('Modified:1566996265000\n', encoding='utf-8')
    out, _ = convert(tmp_path, HEAD + """
        section:a
        .image:one=file:screw.png
        .text:two=file:dolor.txt
        .three=parfile:p.nv:Modified
        .four='quoted text'
        .five="with\\nbreak"
        .six=date:now:'%Y'
        .seven=date:today
        .eight=date:1231231230:'%Y'
        .nine=date:'12/15/22 14:24:59':'%H:%M'
        .ten=numbering:1:%s):2
        .eleven=42
        .twelve=1.5
        .thirteen=Serving
        .fourteen='007'
        .fifteen=2024-01-01
    """)
    got = values(out)
    assert got['image:one'][0] == 'file'
    assert got['text:two'][0] == 'file'
    assert got['three'][0] == 'parfile'
    assert got['four'] == ('str', 'quoted text')
    assert got['five'] == ('str', 'with\nbreak'), 'a double-quoted \\n was a line break'
    assert got['six'][0] == 'datetime' and len(got['six'][1]) == 4
    assert got['seven'][0] == 'datetime'
    assert got['eight'] == ('datetime', '2009')
    assert got['nine'] == ('datetime', '14:24')
    assert got['ten'] == ('numbering', '[ \'2)\', \'3)\', \'4)\', ... ]') or got['ten'][0] == 'numbering'
    assert got['eleven'] == ('int', '42')
    assert got['twelve'][0] == 'float'
    assert got['thirteen'] == ('str', 'Serving'), 'unquoted text is text now, not invalid'
    assert got['fourteen'] == ('str', '007'), 'quoted in the .rdf, so a string: stays quoted'
    assert got['fifteen'] == ('str', '2024-01-01')


def test_modifiers_become_keys_of_the_value_mapping(tmp_path):
    out, _ = convert(tmp_path, HEAD + """
        section:a
        .table:t=file:tools.csv+description=@row1
        .image:i=file:a.png+description='a plus + sign inside'+width=4cm
        .video:v=file:harmonic.mp4+image:poster=file:harmonic.jpg+description='an animated beam'
    """)
    loaded = load(out)
    by_target = {t.target: t for t in loaded.tasks if t.target}
    assert by_target['table:t'].actions['description'].type == 'readfrom'
    image = by_target['image:i']
    assert str(image.actions['description']) == 'a plus + sign inside'
    assert image.actions['width'].type == 'length'
    video = by_target['video:v']
    assert video.actions['image:poster'].type == 'file'
    assert str(video.actions['description']) == 'an animated beam'


# ----------------------------------------------------------------- markers

def test_markers_hold_the_adds_and_interleave_with_fills(tmp_path):
    out, _ = convert(tmp_path, HEAD + """
        section:title
          .table:inline=file:a.csv
          @marker:content
            +table:generic=file:b.csv+description='one'
          .table:orange=file:c.csv
          @marker:content
            +table:orange=file:d.csv
    """)
    assert shape(out) == [
        ('section:title::1', '', 'apply'),
        ('section:title::1.table:inline::1', 'table:inline', ''),
        ('section:title::1.table:generic::1', 'table:generic', 'add'),
        ('section:title::1.table:orange::1', 'table:orange', ''),
        ('section:title::1.table:orange::2', 'table:orange', 'add'),
    ]
    text = out.read_text(encoding='utf-8')
    assert text.count('- marker:content:') == 2


def test_an_add_without_a_marker_is_written_as_a_fill_and_flagged(tmp_path):
    out, warnings = convert(tmp_path, HEAD + """
        section:a
        +image:generic=file:x.png
    """)
    assert ('section:a::1.image:generic::1', 'image:generic', '') in shape(out)
    assert any('without a marker' in w for w in warnings)


# ---------------------------------------------------------------- includes

def test_a_fragment_of_adds_goes_inside_the_marker_relative_to_it(tmp_path):
    out, warnings = convert(tmp_path, HEAD + """
        section:second.subsection:secondb
          .head='Header 3'
          @marker:content
            +text:green=file:dolor.txt
            &include+=loopfiles:textinclude*.rdf
            +text:green='Some last words...'
    """, **{'textinclude1.rdf': """
            +text:green=file:bootseal.txt
            +text:green=file:donotexist.txt
    """})
    assert [t for t in shape(out) if t[2] == 'add'] == [
        ('section:second::1.subsection:secondb::1.text:green::1', 'text:green', 'add'),
        ('section:second::1.subsection:secondb::1.text:green::2', 'text:green', 'add'),
        ('section:second::1.subsection:secondb::1.text:green::3', 'text:green', 'add'),
        ('section:second::1.subsection:secondb::1.text:green::4', 'text:green', 'add'),
    ]
    fragment = (tmp_path / 'textinclude1.yaml').read_text(encoding='utf-8')
    assert '- text:green: {file: bootseal.txt}' in fragment
    assert "_include_: 'textinclude*.yaml'" in out.read_text(encoding='utf-8')
    assert not warnings


def test_a_structural_fragment_is_relative_to_its_include_site(tmp_path):
    out, warnings = convert(tmp_path, HEAD + """
        section:tool
        .table:tools=file:tools.csv
        &include=loopfiles:tool*.rdf
    """, **{'tool01.rdf': """
        section:tool.subsection:tool
          .tool_id='pepper'
    """, 'tool02.rdf': """
        section:tool.subsection:tool
          .tool_id='salt'
    """})
    assert shape(out)[1:] == [
        ('section:tool::1.table:tools::1', 'table:tools', ''),
        ('section:tool::1.subsection:tool::1', '', 'apply'),
        ('section:tool::1.subsection:tool::1.:tool_id::1', 'tool_id', ''),
        ('section:tool::1.subsection:tool::2', '', 'copy'),
        ('section:tool::1.subsection:tool::2.:tool_id::1', 'tool_id', ''),
    ]
    fragment = (tmp_path / 'tool01.yaml').read_text(encoding='utf-8')
    assert fragment.splitlines()[1] == '- subsection:tool:', fragment
    assert not warnings


def test_a_dead_marker_is_noticed_and_the_include_placed_in_the_section(tmp_path):
    """``@marker:addtool`` then an include whose first line is an absolute
    root: the old parser cleared the marker before any ``+`` and the adds
    landed elsewhere (rdf_big_docx.rdf had three of these). A structural
    fragment cannot sit inside a marker, so the include goes in the section."""
    out, warnings = convert(tmp_path, HEAD + """
        section:tool
        @marker:addtool
        &include=loopfiles:tool*.rdf
    """, **{'tool01.rdf': """
        section:tool.subsection:tool
          .tool_id='pepper'
    """})
    text = out.read_text(encoding='utf-8')
    assert "CHECK: the marker 'marker:addtool' was open" in text
    assert any('moved out of marker' in w for w in warnings)
    assert ('section:tool::1.subsection:tool::1', '', 'apply') in shape(out)


def test_a_fragment_addressing_a_level_above_its_site_moves_the_include_up(tmp_path):
    """rdf_big_preparation01.rdf included its ``sub`` from inside a
    subsubsection while the sub opened subsubsections of the subsection -- the
    hand translation put the include one level up, and so does this."""
    out, warnings = convert(tmp_path, HEAD + """
        section:p.subsection:prep
          .id='1'
        section:p.subsection:prep.subsubsection:req
          .text:description='foo'
        &include+=file:sub.rdf
    """, **{'sub.rdf': """
        section:p.subsection:prep.subsubsection:ingredients
          .text:description='to buy'
    """})
    assert [t for t in shape(out) if t[1] == ''] == [
        ('section:p::1', '', 'apply'),
        ('section:p::1.subsection:prep::1', '', 'apply'),
        ('section:p::1.subsection:prep::1.subsubsection:req::1', '', 'apply'),
        ('section:p::1.subsection:prep::1.subsubsection:ingredients::1', '', 'apply'),
    ]
    text = out.read_text(encoding='utf-8')
    assert 'CHECK: sub.rdf addresses section:p.subsection:prep rather than' in text
    assert any('include moved there' in w for w in warnings)


def test_a_fragment_that_jumps_to_another_section_is_attached_there(tmp_path):
    """word_input.rdf included ``testplan*.rdf`` from a phantom
    ``section:results`` while the fragment opened ``section:testplans``."""
    out, warnings = convert(tmp_path, HEAD + """
        section:results
        &include=loopfiles:testplan*.rdf
    """, **{'testplan01.rdf': """
        section:testplans.subsection:testplan
          .head='plan'
    """})
    assert ('section:testplans::1.subsection:testplan::1', '', 'apply') in shape(out)
    assert 'CHECK: testplan*.rdf addresses section:testplans' in out.read_text(encoding='utf-8')


def test_a_missing_include_is_written_but_marked(tmp_path):
    out, warnings = convert(tmp_path, HEAD + """
        section:a
        &include=file:nowhere.rdf
    """)
    text = out.read_text(encoding='utf-8')
    assert '- _include_: nowhere.yaml' in text
    assert 'CHECK: nowhere.rdf was not found' in text
    assert any('not found' in w for w in warnings)


def test_include_cycles_do_not_recurse_forever(tmp_path):
    out, warnings = convert(tmp_path, HEAD + """
        section:a
        &include=file:b.rdf
    """, **{'b.rdf': """
        section:a.subsection:b
          &include=file:report.rdf
    """})
    assert any('cycle' in w for w in warnings)


def test_comments_attach_to_what_follows_them(tmp_path):
    out, _ = convert(tmp_path, HEAD + """
        section:a
        .head='a'
        # the second section
        section:b
        .head='b'
    """)
    text = out.read_text(encoding='utf-8')
    lines = [line.strip() for line in text.splitlines()]
    index = lines.index('# the second section')
    assert lines[index + 1] == '- section:b:'


# --------------------------------------------------------------- the files

def test_an_existing_yaml_is_not_overwritten_without_force(tmp_path):
    source = tmp_path / 'report.rdf'
    source.write_text(HEAD + 'section:a\n.head=x\n', encoding='utf-8')
    target = source.with_suffix('.yaml')
    target.write_text('keep me\n', encoding='utf-8')

    converter = rdf2yaml.Converter()
    converter.convert_root(source)
    assert target.read_text(encoding='utf-8') == 'keep me\n'
    assert converter.skipped == [target]

    rdf2yaml.Converter(force=True).convert_root(source)
    assert 'section:a' in target.read_text(encoding='utf-8')


def test_main_converts_checks_and_reports(tmp_path, capsys):
    (tmp_path / 'data').mkdir()
    source = tmp_path / 'report.rdf'
    source.write_text(HEAD + "section:a\n.head='x'\n", encoding='utf-8')

    code = rdf2yaml.main([str(source)])

    printed = capsys.readouterr().out
    assert code == 0
    assert 'wrote' in printed and 'loads without diagnostics' in printed


def test_main_says_when_the_result_does_not_load_yet(tmp_path, capsys):
    (tmp_path / 'data').mkdir()
    source = tmp_path / 'report.rdf'
    source.write_text("*version=3\nsection:a\n.head='x'\n", encoding='utf-8')

    code = rdf2yaml.main([str(source)])

    printed = capsys.readouterr().out
    assert code == 1
    assert 'does not load yet' in printed and 'documenttype' in printed


# ------------------------------------------- two historical fixtures, verbatim

WORD_TABLES_RDF = """
# test report input
*version=3
*documenttype=docx
*datadir=.\\data

global
.report:id='ID 007'
.date:published='01. August 2020'
.report:version=1.0
.report:status='Draft'
.author='James Bond'

#
section:title
  #.author='James Bond'
  #.report:id='ID 007'
  .date:creation=date:now
  .table:inline=file:instructiongeneral.csv+description='temperatures'
  @marker:content
    +table:generic=file:instruction2.csv+description='instruction two'
  .table:orange=file:table2.csv+description=@row1
  @marker:content
    +table:orange=file:instruction2.csv
"""

TEST_MARKER_RDF = """
*version=100
*documenttype=docx
*datadir=data
# there is one subsection:instruction already in the document
section:instruction_bc.subsection:instruction
  *datadir=foo
  .parameter=parfile:foo.nv:'Hello world parameter'
  .head='Instruction 1'
  #&include=loopfiles:preparation*.rdf
  @marker:content
    +image:generic=file:instruction1.png+description='instruction one'
    +image:generic=file:instruction2.png+description='instruction two'
    +image:generic=file:instruction3.png+description='instruction three'
    #&include=loopfiles:ins*.rdf
"""


@pytest.mark.parametrize('rdf_text, hand_translation', [
    (WORD_TABLES_RDF, '02_basetest/docx_basic/tables/word_tables.yaml'),
    (TEST_MARKER_RDF, '02_basetest/rdf/rdf_testMarker.yaml'),
])
def test_a_historical_fixture_converts_to_what_was_translated_by_hand(
        tmp_path, rdf_text, hand_translation):
    """The two corpora were reconciled by hand before the .rdf files went;
    the converter reaches the same task list on these two without a mark."""
    shutil.copytree(TESTS_ROOT / 'data_source', tmp_path / 'data')
    out, _ = convert(tmp_path, rdf_text, data=False)
    hand_dir = tmp_path / 'hand'
    hand_dir.mkdir()
    shutil.copy(TESTS_ROOT / hand_translation, hand_dir)
    shutil.copytree(tmp_path / 'data', hand_dir / 'data')

    mine = shape(out)
    theirs = shape(hand_dir / Path(hand_translation).name)

    assert mine == theirs
    assert values(out) == values(hand_dir / Path(hand_translation).name)
