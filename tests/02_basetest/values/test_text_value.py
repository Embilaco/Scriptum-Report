"""Tests for :mod:`rdf.values.text_value`, through a report document."""

from pathlib import Path

import pytest

from _setup_values import *


# pytest fixture: injected by argument name -- each test that takes a
# 'workspace' parameter gets a fresh directory under pytest's per-test tmp_path.
@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a working directory with access to the shared sample data."""

    workdir = tmp_path / "workspace"
    workdir.mkdir()
    ensure_link(DATA_SOURCE, workdir / "data")
    return workdir


def _write_document(path: Path, value: str) -> Path:
    """A document whose one fill is ``text:description`` with *value*."""
    path.write_text("\n".join([
        "_scriptum_:",
        "  version: 4",
        "  documenttype: docx",
        "  datadir: ./data",
        "_content_:",
        "  - section:content:",
        f"      - text:description: {value}",
    ]), encoding='utf-8')
    return path


def test_text_value_temperatures_existing_file(monkeypatch: pytest.MonkeyPatch, workspace: Path) -> None:
    """Loading a referenced text file returns its content **as written** --
    the breaks the file has, not one more. (The old readlines-join doubled
    every line break, so a multi-line file rendered with a blank line after
    every line; unnoticed while every text fixture was a single line.)"""

    monkeypatch.chdir(workspace)
    document = _write_document(workspace / "text_value.yaml", "{file: dolor.txt}")

    rdf = ReportDataFile(str(document))
    task = next(t for t in rdf.tasks if t.target == "text:description")
    assert task.value.type == 'file' and task.value.subtype == 'text'
    task.value.load()

    with Path(DATA_SOURCE / "dolor.txt").open(encoding='utf-8') as stream:
        expected = stream.read()
    assert task.value.content == expected
    assert '\n\n' not in task.value.content, 'the readlines-join doubling is back'


def test_text_value_missing_file_returns_placeholder(
    monkeypatch: pytest.MonkeyPatch, workspace: Path
) -> None:
    """Missing files fall back to a helpful placeholder message."""

    monkeypatch.chdir(workspace)
    document = _write_document(workspace / "text_missing.yaml", "{file: does_not_exist.txt}")

    rdf = ReportDataFile(str(document))
    task = next(t for t in rdf.tasks if t.target == "text:description")
    task.value.load()

    assert "non existing file" in task.value.content
    assert "does_not_exist.txt" in task.value.content


def test_text_value_embedded_literal(monkeypatch: pytest.MonkeyPatch, workspace: Path) -> None:
    """A scalar is text, and is passed through without touching the filesystem."""

    monkeypatch.chdir(workspace)
    document = _write_document(workspace / "text_literal.yaml", "'Embedded literal line'")

    rdf = ReportDataFile(str(document))
    task = next(t for t in rdf.tasks if t.target == "text:description")
    task.value.load()

    assert task.value.content == "Embedded literal line"
    assert task.value.type == "str"
