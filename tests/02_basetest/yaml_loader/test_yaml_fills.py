"""A fill's value and its modifiers.

Two things these are really about.

**Quoting stops carrying type information.** ``.head=Serving`` fell through to
the literal-number branch and came out ``invalid``, surfacing in the finished
document rather than at parse time, while ``.head='Serving'`` worked. YAML
types the scalar, so there is nothing left to forget.

**The delimiters are gone, so their collisions are too.** The old value grammar
split on ``+`` anywhere, split a modifier on every ``=``, and on a ``+`` line
kept only the first two ``=``-pieces -- which discarded data with no
diagnostic. None of that survives a structure.
"""

from __future__ import annotations

import textwrap

import pytest

from Scriptum.rdf.loader import (Diagnostics, YamlSource, read_content,
                                 read_global, read_root)
from Scriptum.rdf.values import (AnimationValue, ColorValue, FileValue,
                                 ImageValue, NameValue, TableValue, TextValue)

SETTINGS = '_scriptum_:\n  version: 4\n  documenttype: docx\n'


def read(body, settings=SETTINGS):
    """Wrap *body* as the contents of one section and walk it."""
    text = textwrap.indent(textwrap.dedent(body).strip('\n'), '      ')
    document = f'{settings}_content_:\n  - section:a:\n{text}\n'

    diagnostics = Diagnostics()
    source = YamlSource.from_text(document.encode('utf-8'), 'doc.yaml',
                                  diagnostics)
    header = read_root(source, diagnostics)
    tree = read_content(header.content_node, source, header.settings,
                        diagnostics)
    children = tree[0].children if tree else []
    return children, diagnostics


def one(body, settings=SETTINGS):
    children, diagnostics = read(body, settings)
    assert not diagnostics, diagnostics.report()
    assert len(children) == 1
    return children[0]


def failing(body, settings=SETTINGS):
    _, diagnostics = read(body, settings)
    assert diagnostics, 'expected a diagnostic'
    return diagnostics.report()


# ----------------------------------------------------------------- scalars

def test_unquoted_text_is_text():
    """The trap the format was shaped to remove."""
    fill = one('- head: Serving')

    assert fill.value.type == 'str'
    assert str(fill.value) == 'Serving'


@pytest.mark.parametrize('written, kind, shown', [
    ('42', 'int', '42'),
    ("''", 'str', ''),
    ("'42'", 'str', '42'),
])
def test_scalars_are_typed_by_yaml(written, kind, shown):
    fill = one(f'- head: {written}')

    assert fill.value.type == kind
    assert str(fill.value) == shown


def test_a_float_is_rendered_with_the_configured_format():
    fill = one('- report:version: 1.0')

    assert fill.value.type == 'float'
    assert str(fill.value).strip() == '1.0000'


@pytest.mark.parametrize('written', ['no', 'NO', 'on', 'off', 'yes'])
def test_words_1_1_would_have_made_booleans_arrive_as_text(written):
    """The dialect restriction, seen from where it matters."""
    fill = one(f'- head: {written}')

    assert fill.value.type == 'str'
    assert str(fill.value) == written


def test_a_real_boolean_is_refused_rather_than_coerced():
    report = failing('- head: true')

    assert 'not values this format uses' in report
    assert 'Quote it' in report


def test_a_colour_is_chosen_by_the_target_and_not_by_the_value():
    """``color`` selects ColorValue whatever shape the value has -- which is
    the text format's rule, kept, because it is semantic."""
    fill = one("- color: '#ff0000'")

    assert fill.value.type == 'color'
    assert isinstance(fill.value.object, ColorValue)


def test_a_namespaced_colour_target_selects_it_too():
    fill = one("- color:accent: 'red'")
    assert fill.value.type == 'color'


def test_an_unquoted_hash_colour_is_told_that_yaml_ate_it():
    """``color: #ff0000`` is a YAML comment, so the value is null. The
    diagnostic says so rather than leaving the author staring at an empty
    element in the finished document."""
    report = failing('- color: #ff0000')

    assert 'YAML comment' in report
    assert "write '' instead" in report


# ------------------------------------------------------------ source keys

@pytest.mark.parametrize('target, expected', [
    ('image:generic', ImageValue),
    ('text:body', TextValue),
    ('video:clip', AnimationValue),
    ('table:data', TableValue),
    ('whatever:thing', FileValue),
])
def test_the_target_namespace_chooses_the_file_class(target, expected):
    """The mapping says where the bytes come from, the namespace says what
    they are."""
    fill = one(f'- {target}: {{file: some.dat}}')

    assert fill.value.type == 'file'
    assert isinstance(fill.value.object, expected)


def test_a_filename_may_contain_plus_and_equals():
    """The headline of the whole migration.

    ``+image:g=file:a=b.png`` kept only the first two ``=``-pieces and threw
    the rest away with no diagnostic; a ``+`` anywhere in a path split it. The
    delimiters are gone, so a path is a path.
    """
    fill = one('- image:generic: {file: "a+b=c.png"}')

    assert fill.value.object.filename.endswith('a+b=c.png')


def test_a_parfile_names_its_parameter_in_its_own_key():
    fill = one('- report:menu: {parfile: Some.nv, parameter: MenuTitle}')

    assert fill.value.type == 'parfile'
    assert isinstance(fill.value.object, NameValue)


def test_a_parfile_without_a_parameter_is_reported():
    assert "needs 'parameter'" in failing('- report:menu: {parfile: Some.nv}')


def test_text_states_a_string_explicitly():
    """The way out when a value would otherwise be read as something else."""
    fill = one("- head: {text: '4cm'}")

    assert fill.value.type == 'str'
    assert str(fill.value) == '4cm'


def test_from_reads_a_value_out_of_the_table_itself():
    fill = one('- table:t: {file: t.csv, description: {from: Row1}}')

    caption = fill.actions['description']
    assert caption.type == 'readfrom'
    assert caption.object == 'row1'       # lowercased, as '@row1' was


@pytest.mark.parametrize('spec', ['now', 'today'])
def test_a_date_takes_its_spec_and_its_format_apart(spec):
    fill = one(f"- date:creation: {{date: {spec}, format: '%Y'}}")

    assert fill.value.type == 'datetime'
    assert len(str(fill.value)) == 4


def test_a_date_format_may_contain_colons():
    """Composed for DateValue with the format always quoted, so its tokeniser
    keeps ``%H:%M:%S`` in one piece. The author never writes the composed
    form, which is what makes the delimiter safe."""
    fill = one("- date:creation: {date: now, format: '%H:%M:%S'}")

    assert str(fill.value).count(':') == 2


def test_a_date_without_a_format_uses_the_setting():
    fill = one('- date:creation: {date: now}')
    assert fill.value.type == 'datetime'


def test_numbering_takes_kind_format_and_start():
    fill = one("- number:fig: {numbering: '1', format: 'Figure %s', start: 1}")

    assert fill.value.type == 'numbering'


def test_numbering_needs_a_format():
    assert "needs 'format'" in failing("- number:fig: {numbering: '1'}")


def test_a_numbering_format_with_a_colon_is_refused_rather_than_composed():
    """NumberValue splits on ``:`` and has no quoting, so composing one would
    be misread. The point of keeping the parts apart in the document is that a
    delimiter never decides something the author did not."""
    report = failing("- number:fig: {numbering: '1', format: 'a:%s'}")

    assert 'cannot contain ":"' in report


def test_inline_rows_are_reserved_and_say_so():
    report = failing('- table:t: {rows: [[1, 2]]}')

    assert 'reserved but not implemented' in report


def test_a_value_needs_a_source_key():
    report = failing('- image:generic: {description: nothing}')

    assert 'needs one source key' in report
    assert 'file' in report and 'parfile' in report


def test_a_value_has_only_one_source_key():
    report = failing('- image:generic: {file: a.png, text: b}')

    assert 'has one source key' in report


def test_a_companion_of_another_source_is_named():
    """``parameter`` with a ``file:`` is a mistake worth pointing at, rather
    than being silently treated as a modifier and ignored."""
    report = failing('- image:generic: {file: a.png, parameter: Title}')

    assert "belongs to 'parfile'" in report


# -------------------------------------------------------------- modifiers

def test_modifiers_are_the_remaining_keys():
    fill = one("- image:generic: {file: a.png, description: 'a part', "
               "info: Moore}")

    assert sorted(fill.actions) == ['description', 'info']
    assert str(fill.actions['description']) == 'a part'


def test_modifier_names_are_lowercased_like_every_other_key():
    """The text format lowercased addresses but not modifier names, so a
    modifier written ``Description`` never bound to its ``description`` child
    and nothing said so."""
    fill = one("- image:generic: {file: a.png, Description: 'a part'}")

    assert 'description' in fill.actions


def test_actions_are_applied_to_the_value_that_reads_them():
    fill = one('- table:t: {file: t.csv, description: {from: row1}}')

    assert fill.value.object.actions == fill.actions


@pytest.mark.parametrize('unit', ['cm', 'mm', 'in', 'pt', 'inch'])
def test_a_length_modifier_takes_any_of_the_units(unit):
    fill = one(f'- image:generic: {{file: a.png, width: 4{unit}}}')

    assert fill.actions['width'].type == 'length'


def test_inch_works_here_as_it_already_did_in_a_tag_argument():
    """Closing a split: LengthValue has always understood 'inch' and
    Tag.getLength tests for it, so width=4inch worked in a template tag -- but
    a value line tested only the last *two* characters, so '4inch' ended in
    'ch', missed the length branch and came out invalid."""
    fill = one('- image:generic: {file: a.png, width: 4inch}')

    assert fill.actions['width'].object.unit == 'in'


@pytest.mark.parametrize('written', ['4', '4.5', "'four'", "'4 furlongs'"])
def test_a_length_modifier_needs_a_unit(written):
    """Recognising lengths by name is what makes this diagnosable: the loader
    knows a length was meant, so it can say the unit is missing instead of
    quietly producing a number."""
    report = failing(f'- image:generic: {{file: a.png, width: {written}}}')

    assert 'needs a length with a unit' in report


def test_a_unit_suffix_on_a_name_that_is_not_a_length_is_just_text():
    """Which is what suffix-sniffing could never express: the text format
    decided a value was a length by its last two characters, anywhere."""
    fill = one("- image:generic: {file: a.png, description: '4cm'}")

    assert fill.actions['description'].type == 'str'


def test_scale_is_not_a_length():
    fill = one('- image:generic: {file: a.png, scale: 0.5}')

    assert fill.actions['scale'].type == 'float'


def test_a_modifier_may_carry_its_own_source():
    fill = one('- video:clip: {file: c.mp4, image:poster: {file: c.gif}}')

    poster = fill.actions['image:poster']
    assert isinstance(poster.object, ImageValue)


def test_a_modifier_may_not_carry_modifiers_of_its_own():
    """Reported rather than ignored.

    Silently dropping the extra key would lose what the author wrote, which is
    the failure mode this format is shaped against -- and it is what the first
    version of this code did, having returned an empty actions dict without
    looking at what was in it.
    """
    report = failing('- video:clip: {file: c.mp4, '
                     'image:poster: {file: c.gif, width: 2cm}}')

    assert "'width' is a modifier of a modifier" in report


def test_a_modifier_cannot_be_a_sequence():
    report = failing('- image:generic: {file: a.png, description: [a, b]}')

    assert 'a sequence is a body' in report


def test_a_fill_given_a_sequence_is_told_it_reads_as_a_container():
    """Not a special case: a sequence value *is* a body by the format's own
    rule, so this really is a container called ``head`` and the ladder refuses
    it. The hint is what turns a true-but-baffling message into a useful one."""
    report = failing('- head: [a, b]')

    assert 'A sequence value is a body' in report
    assert "A fill's value is a scalar or a mapping" in report


# ----------------------------------------------------------------- global

def test_global_fills_are_built_like_any_other():
    diagnostics = Diagnostics()
    document = (SETTINGS + '_global_:\n'
                "  report:id: ID 4711\n"
                "  report:version: 1.0\n")
    source = YamlSource.from_text(document.encode('utf-8'), 'doc.yaml',
                                  diagnostics)
    header = read_root(source, diagnostics)
    entries = read_global(header.global_node, source, header.settings,
                          diagnostics)

    assert not diagnostics, diagnostics.report()
    assert [e.value.type for e in entries] == ['str', 'float']


def test_a_global_fill_takes_no_id():
    """It is not an instance, it is a rule applied to every instance. ``global``
    matches on puretag alone -- deliberately, since that is what lets it reach
    clones -- so a number would name something the match ignores."""
    diagnostics = Diagnostics()
    document = SETTINGS + '_global_:\n  report:id: ID 4711\n'
    source = YamlSource.from_text(document.encode('utf-8'), 'doc.yaml',
                                  diagnostics)
    header = read_root(source, diagnostics)
    entry, = read_global(header.global_node, source, header.settings,
                         diagnostics)

    assert entry.address.id is None
    assert entry.address.puretag == 'report:id'
    assert entry.path == ()


def test_a_marker_in_global_is_refused():
    diagnostics = Diagnostics()
    document = SETTINGS + '_global_:\n  marker:content: x\n'
    source = YamlSource.from_text(document.encode('utf-8'), 'doc.yaml',
                                  diagnostics)
    header = read_root(source, diagnostics)
    read_global(header.global_node, source, header.settings, diagnostics)

    report = diagnostics.report()
    assert 'names a position inside one element' in report
