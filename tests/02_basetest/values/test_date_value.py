# tests different data formats

import sys
import types
from datetime import datetime

from _setup_values import  *

def test_date_time_strings(tmp_path):
    base = tmp_path / "testDateTime.rdf"
    base.write_text("\n".join([
        "*version=100",
        "*dateformat=%x",
        "*timeformat = %X",
        "*datetimeformat = %c",
        "*documenttype=docx",
        "section:mysection.subsection:foo",
        ".setdate=date:today",
        ".settime=date:now",
        ".testtime=date:'12/15/22 14:24:59'",
        ".testtimefmt=date:'12/15/22 14:24:59':'%m/%d/%y %H:%M:%S'",
        ".created=date:now:'%d. %b %Y -- %H:%M:%S'",
        ".initial=date:1231231230:'%d. %b %Y -- %H:%M:%S'",
        ".toolong=date:12312312345689:'%d. %b %Y -- %H:%M:%S'",
        ".tooshort=date:123123:'%d. %b %Y -- %H:%M:%S'",
        ]))
    
    rdf = ReportDataFile(str(base), _root=[])

    setdate = next(t for t in rdf.tasks if t.target == "setdate").value
    created = next(t for t in rdf.tasks if t.target == "created").value
    settime = next(t for t in rdf.tasks if t.target == "settime").value
    testtime = next(t for t in rdf.tasks if t.target == "testtime").value
    initial = next(t for t in rdf.tasks if t.target == "initial").value
    tooshort = next(t for t in rdf.tasks if t.target == "tooshort").value
    toolong = next(t for t in rdf.tasks if t.target == "toolong").value
    #print(setdate) # 09/25/25
    #print(created) # 25. Sep 2025 -- 17:32:27
    #print(settime) # Thu Sep 25 17:32:27 2025
    #
    #print(testtime.object.dt)
    assert testtime.object.dt.year == 2022
    assert testtime.object.dt.month == 12
    assert testtime.object.dt.day == 15
    assert testtime.object.dt.hour == 14
    assert testtime.object.dt.minute == 24
    assert testtime.object.dt.second == 59
    testtimefmt = next(t for t in rdf.tasks if t.target == "testtimefmt").value
    assert str(testtimefmt) == "12/15/22 14:24:59"


    expected_toolong = datetime.fromtimestamp(12312312345689 / 1000.0).strftime("%d. %b %Y -- %H:%M:%S")
    expected_tooshort = datetime.fromtimestamp(123123).strftime("%d. %b %Y -- %H:%M:%S")
    expected_initial = datetime.fromtimestamp(1231231230).strftime("%d. %b %Y -- %H:%M:%S")
    assert str(toolong) == expected_toolong
    assert str(tooshort) == expected_tooshort
    assert str(initial) == expected_initial
    assert rdf.errors == []





