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
