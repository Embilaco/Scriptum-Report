"""Tests for :mod:`rdf.values.namevalues_value`, through a report document."""

from datetime import datetime

from _setup_values import *

from Scriptum.rdf.values.namevalues_value import NameValueReader, strToTime # pyright: ignore[reportMissingImports]


# pytest fixture: injected by argument name -- each test that takes a
# 'workspace' parameter gets a fresh directory under pytest's per-test tmp_path.
@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    ensure_link(DATA_SOURCE, workdir / "data")
    return workdir


def _write_document(path: Path, settings: list[str], fills: list[str]) -> Path:
    """A document with ``section:parameters`` holding the given fills."""
    path.write_text("\n".join(
        ["_scriptum_:", "  version: 4", "  documenttype: docx", "  datadir: ."]
        + [f"  {line}" for line in settings]
        + ["_content_:", "  - section:parameters:"]
        + [f"      - {line}" for line in fills]
    ), encoding='utf-8')
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
    document = _write_document(
        workspace / "namevalue.yaml",
        ["nvseparator: ':'", "datetimeformat: '%Y-%m-%d %H:%M:%S'"],
        [
            "nv:nine: {parfile: params.nv, parameter: CreatedNine}",
            "nv:ten: {parfile: params.nv, parameter: CreatedTen}",
            "nv:milli: {parfile: params.nv, parameter: CreatedMilli}",
        ],
    )

    rdf = ReportDataFile(str(document))
    tasks = {task.target: task for task in rdf.tasks if task.target.startswith("nv:")}
    assert all(task.value.type == 'parfile' for task in tasks.values())
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
    document = _write_document(
        workspace / "missing_nv.yaml",
        [],
        ["nv:missing: {parfile: missing.nv, parameter: Foo}"],
    )

    rdf = ReportDataFile(str(document))
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
