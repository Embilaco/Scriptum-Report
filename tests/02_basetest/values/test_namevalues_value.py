"""Tests for :mod:`rdf.values.namevalues_value`."""

from datetime import datetime

from _setup_values import *

from Scriptum.rdf.values.namevalues_value import NameValueReader, strToTime # pyright: ignore[reportMissingImports]


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    ensure_link(DATA_SOURCE, workdir / "data")
    return workdir


def _write_rdf(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines))
    return path


def _create_nv_file(directory: Path, name: str) -> Path:
    nv_path = directory / name
    nv_path.write_text(
        "\n".join(
            [
                "CreatedNine:123456789",
                "CreatedTen:1234567890",
                "CreatedMilli:1234567890000",
                "PlainText:Hello World",
            ]
        )
    )
    return nv_path


def test_namevalue_parses_timestamp_fields(monkeypatch: pytest.MonkeyPatch, workspace: Path) -> None:
    """Timestamp-like entries in *.nv files are converted using ``strToTime``."""

    _create_nv_file(workspace, "params.nv")
    monkeypatch.chdir(workspace)
    rdf_path = _write_rdf(
        workspace / "namevalue.rdf",
        [
            "*version=100",
            "*documenttype=docx",
            "*datadir=.",
            "*nvseparator=:",
            "*datetimeformat=%Y-%m-%d %H:%M:%S",
            "section:parameters",
            ".nv:nine=parfile:params.nv:CreatedNine",
            ".nv:ten=parfile:params.nv:CreatedTen",
            ".nv:milli=parfile:params.nv:CreatedMilli",
        ],
    )

    rdf = ReportDataFile(str(rdf_path), _root=[])
    tasks = {task.target: task for task in rdf.tasks if task.target.startswith("nv:")}
    readers = {target: NameValueReader(task.value.object) for target, task in tasks.items()}

    expected_nine = datetime.fromtimestamp(123456789).strftime("%Y-%m-%d %H:%M:%S")
    expected_ten = datetime.fromtimestamp(1234567890).strftime("%Y-%m-%d %H:%M:%S")
    expected_milli = datetime.fromtimestamp(1234567890).strftime("%Y-%m-%d %H:%M:%S")

    assert readers["nv:nine"]["CreatedNine"] == expected_nine
    assert readers["nv:ten"]["CreatedTen"] == expected_ten
    assert readers["nv:milli"]["CreatedMilli"] == expected_milli


def test_namevalue_missing_file_falls_back_to_message(
    monkeypatch: pytest.MonkeyPatch, workspace: Path
) -> None:
    """Missing ``*.nv`` files do not crash and expose a helpful placeholder."""

    monkeypatch.chdir(workspace)
    rdf_path = _write_rdf(
        workspace / "missing_nv.rdf",
        [
            "*version=100",
            "*documenttype=docx",
            "*datadir=.",
            "section:parameters",
            ".nv:missing=parfile:missing.nv:Foo",
        ],
    )

    rdf = ReportDataFile(str(rdf_path), _root=[])
    task = next(t for t in rdf.tasks if t.target == "nv:missing")
    reader = NameValueReader(task.value.object)

    assert not reader.exists
    assert "missing.nv" in str(task.value.object)


@pytest.mark.parametrize(
    "timestamp, expected",
    [
        ("1566995546", datetime.fromtimestamp(1566995546)),
        ("1566995546000", datetime.fromtimestamp(1566995546)),
        ("123456789", datetime.fromtimestamp(123456789)),
        ("12345", None),
        ("", None),
    ],
)
def test_strtotime_edge_cases(timestamp: str, expected: datetime | None) -> None:
    """``strToTime`` gracefully handles edge lengths and invalid input."""

    result = strToTime(timestamp)
    if expected is None:
        assert result is None
    else:
        assert result == expected
