"""Pin the YAML dialect the loader reads documents in.

PyYAML implements YAML 1.1. Its implicit typing turns ``no`` into ``False``
and ``1:30`` into ``90``, which in a report data file is silent corruption of
the author's text -- the same class of failure as the old format turning
``.head=Serving`` into ``invalid``, and one of the reasons this format exists.

These tests are the record of what "restricted to the 1.2 core schema" means
in practice, and of the two ways of getting the restriction subtly wrong. Both
were found by measuring rather than by reading the docs, and both fail quietly:
a document keeps loading, it just means something else.
"""

from __future__ import annotations

import math

import pytest
import yaml

from Scriptum.rdf.loader.dialect import Core12Loader


def load(text):
    return yaml.load(f'k: {text}\n', Loader=Core12Loader)['k']


# ------------------------------------------------- what 1.2 gets right

@pytest.mark.parametrize('written', ['no', 'NO', 'No', 'on', 'off', 'yes', 'y', 'n'])
def test_words_that_1_1_turns_into_booleans_stay_text(written):
    """The headline case. A table cell reading 'no' must survive as 'no'."""
    assert load(written) == written


@pytest.mark.parametrize('written', ['true', 'True', 'TRUE', 'false', 'False', 'FALSE'])
def test_only_true_and_false_are_booleans(written):
    assert load(written) is (written.lower() == 'true')


def test_a_time_is_not_a_sexagesimal_number():
    """1.1 reads 1:30 as 1*60+30. Nobody writing a report means that."""
    assert load('1:30') == '1:30'


def test_underscores_are_not_digit_separators():
    assert load('1_000') == '1_000'


# ------------------------------- the trap: resolvers alone are not enough

def test_a_leading_zero_is_decimal_not_octal():
    """This is what catches replacing the resolvers but not the constructors.

    ``0755`` matches the 1.2 integer pattern, so a replaced resolver tags it
    ``int`` and stops there. PyYAML's own ``construct_yaml_int`` then reads it
    with 1.1 rules and produces octal 493 -- a 1.1 value wearing a 1.2 tag,
    with nothing anywhere reporting a problem.
    """
    assert load('0755') == 755
    assert yaml.safe_load('k: 0755\n')['k'] == 493      # what 1.1 does


@pytest.mark.parametrize('written, expected', [
    ('0o755', 493),
    ('0x1f', 31),
    ('-3', -3),
    ('+7', 7),
    ('007', 7),
])
def test_explicit_bases_and_signs(written, expected):
    assert load(written) == expected


@pytest.mark.parametrize('written, expected', [
    ('1.0', 1.0),
    ('2.5e3', 2500.0),
    ('.5', 0.5),
    ('-0.25', -0.25),
])
def test_floats(written, expected):
    assert load(written) == expected


def test_scientific_notation_is_a_float_here_and_a_string_in_1_1():
    """1.1's float pattern requires a '.', so PyYAML leaves 2.5e3 a string."""
    assert load('2.5e3') == 2500.0
    assert yaml.safe_load('k: 2.5e3\n')['k'] == '2.5e3'


@pytest.mark.parametrize('written', ['.inf', '.Inf', '.INF'])
def test_infinity(written):
    assert load(written) == math.inf


def test_negative_infinity():
    assert load('-.inf') == -math.inf


def test_not_a_number():
    assert math.isnan(load('.nan'))


@pytest.mark.parametrize('written', ['null', 'Null', 'NULL', '~', ''])
def test_null_is_unchanged_from_pyyaml(written):
    """1.1 and 1.2 agree on null, so its resolver is deliberately left alone."""
    assert load(written) is None


@pytest.mark.parametrize('written', ['4cm', 'Serving', 'Draft', 'ID 4711'])
def test_ordinary_text_is_text(written):
    assert load(written) == written


# --------------------------- the trap: mutating the shared resolver map

def test_the_subclass_owns_its_resolver_map():
    """Structural guard for the second way to get this wrong.

    ``yaml_implicit_resolvers`` is inherited. Editing it in place -- rather
    than assigning a filtered copy onto the subclass -- reconfigures
    ``SafeLoader`` itself, and with it every other user of PyYAML in the
    interpreter. The symptom appears in unrelated code.
    """
    assert 'yaml_implicit_resolvers' in Core12Loader.__dict__
    assert 'yaml_constructors' in Core12Loader.__dict__
    assert Core12Loader.yaml_implicit_resolvers is not \
        yaml.SafeLoader.yaml_implicit_resolvers


def test_importing_the_dialect_leaves_safeloader_alone():
    """The behavioural half of the test above."""
    assert yaml.safe_load('k: on\n')['k'] is True
    assert yaml.safe_load('k: 1:30\n')['k'] == 90


# --------------------------------------------------------- still safe

def test_an_unknown_tag_is_refused_rather_than_constructed():
    """Inherited from SafeLoader, and worth pinning: a document must not be
    able to name a Python type for the loader to instantiate. The text format
    reached ``eval`` on the same kind of input, which is why this is checked
    rather than assumed."""
    with pytest.raises(yaml.YAMLError):
        yaml.load('k: !!python/object/apply:os.system ["echo hi"]\n',
                  Loader=Core12Loader)
