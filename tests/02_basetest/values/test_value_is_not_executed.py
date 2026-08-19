"""An .rdf is data. Parsing one must never execute what it contains.

The value dispatcher ends in a fall-through that tries to read a bare number.
It used to do that with `eval()`, so any value the earlier branches did not
recognise was executed as a Python expression at parse time -- reachable from
every `.rdf`, and from every file pulled in by `&include=loopfiles:*.rdf`.
"""

import os

from _setup_values import *  # noqa: F401,F403 - ensure package import setup

from Scriptum.rdf.values.base import Value
from Scriptum.rdf.settings import SETTINGS


SETTINGS_ = SETTINGS()

# Marker: if the expression ran, os.environ would carry it afterwards.
PAYLOAD = '__import__("os").environ.setdefault("SCRIPTUM_RDF_EXECUTED", "yes")'


def test_expression_in_a_value_is_not_executed():
    os.environ.pop('SCRIPTUM_RDF_EXECUTED', None)

    value = Value(PAYLOAD, SETTINGS_, target='text')

    assert 'SCRIPTUM_RDF_EXECUTED' not in os.environ, (
        'parsing an .rdf executed code from the value'
    )
    assert value.type == 'invalid'


def test_calls_do_not_run_even_when_they_look_harmless():
    value = Value('__import__("os").getpid()', SETTINGS_, target='text')

    assert value.type == 'invalid'
    assert str(os.getpid()) not in str(value.object or '')


def test_plain_numbers_still_parse():
    assert Value('42', SETTINGS_, target='text').type == 'int'
    assert Value('3.5', SETTINGS_, target='text').type == 'float'
    assert Value('-7', SETTINGS_, target='text').type == 'int'


def test_arithmetic_is_no_longer_silently_computed():
    """`2+3` used to evaluate to 5; it is now flagged instead of guessed at."""

    assert Value('2+3', SETTINGS_, target='text').type == 'invalid'
