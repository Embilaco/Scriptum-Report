# tests different date formats, read from a report document

from datetime import datetime
from pathlib import Path

import pytest

from _setup_values import *


def _document(tmp_path: Path, fills: list[str]) -> Path:
    base = tmp_path / "testDateTime.yaml"
    base.write_text("\n".join([
        "_scriptum_:",
        "  version: 4",
        "  documenttype: docx",
        "  dateformat: '%x'",
        "  datetimeformat: '%c'",
        "_content_:",
        "  - section:mysection:",
        "      - subsection:foo:",
        ] + [f"          - {fill}" for fill in fills]), encoding='utf-8')
    return base


def test_date_time_strings(tmp_path: Path):
    """The forms a ``date`` source takes, through the loader.

    The spec and the strftime pattern are separate keys; a timestamp may be
    written as a number or as text.
    """
    base = _document(tmp_path, [
        "setdate: {date: today}",
        "settime: {date: now}",
        "created: {date: now, format: '%d. %b %Y -- %H:%M:%S'}",
        "initial: {date: 1231231230, format: '%d. %b %Y -- %H:%M:%S'}",
        "toolong: {date: '12312312345689', format: '%d. %b %Y -- %H:%M:%S'}",
        "tooshort: {date: 123123, format: '%d. %b %Y -- %H:%M:%S'}",
    ])

    rdf = ReportDataFile(str(base))

    def value_of(target):
        return next(t for t in rdf.tasks if t.target == target).value

    setdate = value_of("setdate")
    created = value_of("created")
    settime = value_of("settime")
    initial = value_of("initial")
    tooshort = value_of("tooshort")
    toolong = value_of("toolong")
    #print(setdate) # 09/25/25
    #print(created) # 25. Sep 2025 -- 17:32:27
    #print(settime) # Thu Sep 25 17:32:27 2025

    assert setdate.type == settime.type == created.type == 'datetime'
    assert setdate.object.format == '%x'
    assert settime.object.format == '%c'
    assert created.object.format == '%d. %b %Y -- %H:%M:%S'

    expected_toolong = datetime.fromtimestamp(12312312345689 / 1000.0).strftime("%d. %b %Y -- %H:%M:%S")
    expected_tooshort = datetime.fromtimestamp(123123).strftime("%d. %b %Y -- %H:%M:%S")
    expected_initial = datetime.fromtimestamp(1231231230).strftime("%d. %b %Y -- %H:%M:%S")
    assert str(toolong) == expected_toolong
    assert str(tooshort) == expected_tooshort
    assert str(initial) == expected_initial
    assert rdf.errors == []


def test_a_date_string_with_a_time_in_it(tmp_path: Path):
    """``date:`` takes a date string as written; a time inside it is part of
    the date, not a delimiter. With ``format`` the same string is rendered
    through the pattern.

    This was wrong while DateValue re-tokenised a composed ``spec:'fmt'``
    string: YAML had consumed the quotes, so the time was split on its colons
    and '12/15/22 14:24:59' read as 14:00 with the format '24:59'.
    """
    base = _document(tmp_path, [
        "testtime: {date: '12/15/22 14:24:59'}",
        "testtimefmt: {date: '12/15/22 14:24:59', format: '%m/%d/%y %H:%M:%S'}",
    ])

    rdf = ReportDataFile(str(base))

    testtime = next(t for t in rdf.tasks if t.target == "testtime").value
    assert testtime.object.dt == datetime(2022, 12, 15, 14, 24, 59)
    assert testtime.object.format == '%c', 'no format given: the setting'

    testtimefmt = next(t for t in rdf.tasks if t.target == "testtimefmt").value
    assert str(testtimefmt) == "12/15/22 14:24:59"
    assert rdf.errors == []


# ------------------------------------------------- the class on its own

from Scriptum.rdf.settings import SETTINGS
from Scriptum.rdf.values.date_value import EPOCH, DateValue


@pytest.mark.parametrize('spec, expected_format', [
    ('now', '%Y-%m-%d %H:%M:%S'), ('Now', '%Y-%m-%d %H:%M:%S'),
    ('NOW ', '%Y-%m-%d %H:%M:%S'),
    ('today', '%Y-%m-%d'), ('Today', '%Y-%m-%d'),
])
def test_now_and_today_are_keywords_in_any_case(spec, expected_format):
    value = DateValue(spec, SETTINGS())

    assert value.valid
    assert value.format == expected_format
    assert abs((value.dt - datetime.now()).total_seconds()) < 5


def test_a_timestamp_is_local_naive_time():
    """Everything is naive local time: a timestamp is converted with
    fromtimestamp, now is the local clock, nothing carries a tzinfo."""
    value = DateValue(1231231230, SETTINGS(), format='%Y-%m-%d %H:%M:%S')

    assert value.dt == datetime.fromtimestamp(1231231230)
    assert value.dt.tzinfo is None
    assert str(value) == datetime.fromtimestamp(1231231230).strftime('%Y-%m-%d %H:%M:%S')


def test_thirteen_digits_are_milliseconds():
    assert DateValue('1566996265000', SETTINGS()).dt == datetime.fromtimestamp(1566996265)
    assert DateValue(1566996265000, SETTINGS()).dt == datetime.fromtimestamp(1566996265)


def test_what_does_not_parse_degrades_to_the_epoch_but_says_so():
    """The class never raises -- the house rule -- but it is not silent either:
    valid is False and problem names the spec, which is what the loader reads
    to refuse the document. A direct caller gets the epoch and the flag."""
    value = DateValue('next tuesday', SETTINGS())

    assert value.valid is False
    assert "'next tuesday' is not a date" in value.problem
    assert value.dt == EPOCH
    assert 'invalid' in repr(value)


def test_a_good_date_is_valid_and_quiet():
    value = DateValue('2022-12-15 14:24:59', SETTINGS(), format='%H:%M')

    assert (value.valid, value.problem) == (True, None)
    assert str(value) == '14:24'


def _strftime_rejects_an_unknown_directive():
    try:
        datetime(2001, 2, 3).strftime('%Q')
    except ValueError:
        return True
    return False


# skipif evaluates the probe at collection time -- on platforms whose strftime
# accepts unknown directives (glibc) the test is skipped, with the reason shown.
@pytest.mark.skipif(not _strftime_rejects_an_unknown_directive(),
                    reason='glibc prints an unknown directive literally')
def test_a_pattern_strftime_rejects_is_flagged_and_rendered_with_dateformat():
    value = DateValue('now', SETTINGS(), format='%Q')

    assert value.valid is False
    assert "'%Q' is not a strftime pattern" in value.problem
    assert value.value == value.dt.strftime('%Y-%m-%d'), 'the degrade: dateformat'


def test_the_defaults_are_iso_8601():
    """Decided 2026-08-23 (question 47d53a4d56f1 on the YAML board): a document
    that says nothing about formats renders the same in every process. The C
    library's '%x'/'%c' followed the process locale."""
    settings = SETTINGS()

    assert (settings.dateformat, settings.datetimeformat) ==         ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S')
    assert str(DateValue(1231231230, settings)) ==         datetime.fromtimestamp(1231231230).strftime('%Y-%m-%d %H:%M:%S')
