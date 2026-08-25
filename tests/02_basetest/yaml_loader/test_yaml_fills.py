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

def test_a_merge_key_is_refused_as_an_address_not_crashed_on():
    """``<<`` resolved to the 1.1 merge tag, which SafeLoader cannot construct
    as a scalar -- ``ConstructorError`` escaped the loader. It is a string
    now, and a string that is not an address."""
    assert 'not a valid segment' in failing('- <<: x')


def test_a_date_shaped_scalar_is_the_text_it_looks_like():
    fill = one('- head: 2022-12-15')
    assert (fill.value.type, str(fill.value)) == ('str', '2022-12-15')


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


@pytest.mark.parametrize('written, expected', [
    ('ff0000', 'FF0000'),
    ('FF0000', 'FF0000'),
    ("'#ff0000'", 'FF0000'),
    ('red', 'FF0000'),
    ('steelblue', '4682B4'),
    ('rgb(255,0,0)', 'FF0000'),
    ('rgb(255, 0, 0)', 'FF0000'),
    ('rgb(0,128,255)', '0080FF'),
])
def test_the_ways_a_colour_may_be_written(written, expected):
    fill = one(f'- color: {written}')

    assert fill.value.object.content == expected


@pytest.mark.parametrize('written, expected', [
    ('123456', '123456'),
    ('012345', '012345'),
    ('000000', '000000'),
])
def test_an_all_digit_hex_survives_yamls_typing(written, expected):
    """Read from the node's raw text rather than from its typed value.

    Under the 1.2 core schema ``123456`` is an integer, and ``012345`` is the
    integer ``12345`` -- the leading zero gone and the colour silently wrong.
    The node still holds exactly what was written, so reading that makes the
    typing irrelevant, and is what lets the ``#`` be dropped in *every* case
    rather than in most of them.
    """
    fill = one(f'- color: {written}')

    assert fill.value.object.content == expected


def test_the_hash_is_optional_but_costs_a_quote_when_it_is_used():
    """Unquoted, ``#`` makes the rest of the line a YAML comment, so the value
    is null -- and by the format's own rule a null value is a container, so
    what the author gets is a ladder complaint about an element they never
    wrote. The hint exists because the real mistake is three steps upstream --
    and it comes from the ladder check rather than from the colour code, which
    this value never reaches.
    """
    report = failing('- color: #ff0000')

    assert 'YAML comment' in report
    assert 'unless it is quoted' in report


@pytest.mark.parametrize('written', ['nosuchcolour', "'#f00'", 'rgb(300,0,0)',
                                     "'#12345'"])
def test_an_unrecognised_colour_is_reported_instead_of_silently_black(written):
    """ColorValue still degrades to black -- a colour has nowhere to put an
    explanatory sentence -- but that fallback used to be the whole story: a
    typo produced a black element and nothing anywhere said why. The loader
    has a diagnostic channel, so it uses it."""
    report = failing(f'- color: {written}')

    assert 'is not a colour' in report
    assert 'rgb(255,0,0)' in report


def test_a_channel_over_255_is_refused_rather_than_clamped():
    """A clamped colour is a wrong colour nobody was told about."""
    assert 'is not a colour' in failing('- color: rgb(256,0,0)')


def test_rgb_split_by_a_flow_mapping_is_explained():
    """``{color: rgb(255,0,0)}`` parses -- silently -- as three entries:
    ``{'color': 'rgb(255', 0: None, '0)': None}``. Nothing about that says what
    went wrong, so the diagnostic does."""
    report = failing('- image:x: {file: a.png, color: rgb(255,0,0)}')

    assert 'flow mapping' in report


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
    """The spec and the pattern reach DateValue as two arguments; nothing is
    composed and re-split, so a colon in either is just a character."""
    fill = one("- date:creation: {date: now, format: '%H:%M:%S'}")

    assert str(fill.value).count(':') == 2


def test_a_date_string_keeps_the_time_inside_it():
    """YAML consumes the quotes around a date string. While the loader composed
    ``date:spec:'fmt'`` for DateValue to split on ``:``, the time inside the
    string was split like a delimiter and '12/15/22 14:24:59' read as 14:00
    with the pattern '24:59'. The parts go to the class as parts now."""
    fill = one("- date:creation: {date: '12/15/22 14:24:59', format: '%H:%M:%S'}")

    assert str(fill.value) == '14:24:59'
    assert fill.value.object.format == '%H:%M:%S'


@pytest.mark.parametrize('written', ['1231231230', '1231231230.5'])
def test_a_timestamp_may_be_a_number(written):
    """``date:`` takes an integer timestamp, as the format says -- unquoted,
    which YAML types as a number; the loader used to refuse that with
    "'date' needs text"."""
    from datetime import datetime
    fill = one(f"- date:creation: {{date: {written}, format: '%Y'}}")

    assert str(fill.value) == datetime.fromtimestamp(float(written)).strftime('%Y')


@pytest.mark.parametrize('written', ['2022-12-15', '2022-12-15 14:24:59'])
def test_an_iso_date_needs_no_quotes(written):
    """Under the core schema a date-shaped scalar is a string, so the natural
    spelling reads. (Under the 1.1 typing it arrived as a datetime object and
    was refused with "needs text".)"""
    fill = one(f"- date:creation: {{date: {written}, format: '%Y-%m-%d'}}")

    assert str(fill.value) == '2022-12-15'


@pytest.mark.parametrize('written', ['Now', 'TODAY', 'today '])
def test_now_and_today_are_keywords_in_any_case(written):
    fill = one(f"- date:creation: {{date: '{written}', format: '%Y'}}")

    assert fill.value.object.valid
    assert len(str(fill.value)) == 4


def test_a_pattern_written_in_the_date_slot_is_named():
    """Three translated fixtures wrote {date: 'FORMAT'} and rendered
    01. Jan 1970 in the settings format -- DateValue degraded to the epoch
    and nothing said so. The fingerprint is a '%' in the spec."""
    report = failing("- date:creation: {date: '%d. %b %Y'}")

    assert 'looks like a strftime pattern' in report
    assert "{date: today, format: '%d. %b %Y'}" in report


@pytest.mark.parametrize('written', ["'next tuesday'", "'01. Jan 1970 -- 01:00:00 x'"])
def test_what_is_not_a_date_is_refused_not_the_epoch(written):
    """The document is the one place where printing 01. Jan 1970 is worse
    than stopping."""
    report = failing(f"- date:creation: {{date: {written}}}")

    assert 'is not a date' in report


@pytest.mark.parametrize('written', ['12', "''"])
def test_a_date_format_needs_text(written):
    report = failing(f"- date:creation: {{date: now, format: {written}}}")

    assert "'format' needs text" in report


def _strftime_rejects_an_unknown_directive():
    from datetime import datetime
    try:
        datetime(2001, 2, 3).strftime('%Q')
    except ValueError:
        return True
    return False


# skipif evaluates the probe at collection time -- on platforms whose strftime
# accepts unknown directives (glibc) the test is skipped, with the reason shown.
@pytest.mark.skipif(not _strftime_rejects_an_unknown_directive(),
                    reason='glibc prints an unknown directive literally; '
                           'only Windows strftime rejects it')
def test_a_pattern_strftime_rejects_is_refused_not_swapped_for_the_default():
    """DateValue used to fall back to dateformat silently when strftime
    raised -- on Windows, that is; glibc never raises, so this half of the
    rule is platform-dependent by nature."""
    report = failing("- date:creation: {date: now, format: '%Q'}")

    assert 'is not a strftime pattern' in report


def test_a_date_namespace_does_not_make_a_scalar_a_date():
    """`date:published: 01. August 2020` is the text the author wrote,
    verbatim. Only the source key `date` evaluates anything: the namespace is
    the tag's name in the template, and re-rendering a literal publication
    date in datetimeformat is the last thing the author wants."""
    fill = one('- date:published: 01. August 2020')

    assert (fill.value.type, str(fill.value)) == ('str', '01. August 2020')


def test_a_date_without_a_format_uses_the_setting():
    fill = one('- date:creation: {date: now}')
    assert fill.value.type == 'datetime'


def test_numbering_takes_kind_format_and_start():
    fill = one("- number:fig: {numbering: '1', format: 'Figure %s', start: 1}")

    assert fill.value.type == 'numbering'
    assert next(fill.value.object) == 'Figure 1'


def test_the_counter_kind_1_may_be_a_number():
    """Unquoted, YAML types it as an int; the loader used to refuse that with
    "'numbering' needs text"."""
    fill = one("- number:fig: {numbering: 1, format: '%s)', start: 3}")

    assert [next(fill.value.object) for _ in range(2)] == ['3)', '4)']


def test_numbering_needs_a_format():
    assert "needs 'format'" in failing("- number:fig: {numbering: '1'}")


def test_a_numbering_format_may_contain_a_colon():
    """NumberValue takes kind, format and start as three arguments, so a
    colon in the format is just a character. The text format's
    ``numbering:kind:format[:start]`` could not say that, and for a while the
    loader refused the colon rather than compose something misread."""
    fill = one("- number:fig: {numbering: '1', format: 'a:%s'}")

    assert next(fill.value.object) == 'a:1'


def test_inline_rows_are_reserved_and_say_so():
    report = failing('- table:t: {rows: [[1, 2]]}')

    assert 'reserved but not implemented' in report


def test_a_value_needs_a_source_key():
    report = failing('- image:generic: {description: nothing}')

    assert 'needs one source key' in report
    assert 'file' in report and 'parfile' in report


@pytest.mark.parametrize('body, text', [
    ("- title:\n    From Typewriting to Variable Fonts:",
     'From Typewriting to Variable Fonts'),
    ('- title: {a}', 'a'),
])
def test_one_key_and_no_value_is_named_as_an_unquoted_colon(body, text):
    """The fingerprint from the directive: a fill that arrives as a mapping
    whose single key is not a source key and whose value is null is, almost
    always, an unquoted value ending in ':' (or a stray {word}). The message
    says so and quotes the text back, instead of talking about source keys."""
    report = failing(body)

    assert 'one key and no value' in report
    assert f"quote it: '{text}:'" in report


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


def test_a_colour_modifier_is_a_colour():
    """``color`` selects ColorValue as a modifier too -- the back ends paint
    the filled text with it. Written as corporate hex here: quoted, because
    an all-digit hex would otherwise arrive as a number."""
    fill = one("- report:status: {text: DRAFT, color: 'B00020'}")

    colour = fill.actions['color']
    assert colour.type == 'color'
    assert isinstance(colour.object, ColorValue)
    assert colour.object.for_docx == 'B00020'
    assert colour.object.for_pptx == (176, 0, 32)


def test_an_unrecognised_colour_modifier_is_reported():
    """Reported at parse time like a colour target -- not silently black,
    and not silently dropped like the text format's modifiers."""
    report = failing('- report:status: {text: DRAFT, color: not-a-colour}')

    assert 'is not a colour' in report


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
