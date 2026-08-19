"""Tests for :mod:`rdf.values.text_value`."""

import sys
import types
from pathlib import Path

import pytest

from _setup_values import *

@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a working directory with access to the shared sample data."""

    workdir = tmp_path / "workspace"
    workdir.mkdir()
    ensure_link(DATA_SOURCE, workdir / "data")
    return workdir


def _write_rdf(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines))
    return path


def test_text_value_temperatures_existing_file(monkeypatch: pytest.MonkeyPatch, workspace: Path) -> None:
    """Loading a referenced text file returns its full content."""

    monkeypatch.chdir(workspace)
    rdf_path = _write_rdf(
        workspace / "text_value.rdf",
        [
            "*version=100",
            "*documenttype=docx",
            "*datadir=./data",
            "section:content",
            ".text:description=file:dolor.txt",
        ],
    )

    rdf = ReportDataFile(str(rdf_path), _root=[])
    task = next(t for t in rdf.tasks if t.target == "text:description")
    task.value.load()

    with Path(DATA_SOURCE / "dolor.txt").open() as stream:
        expected = "\n".join(stream.readlines())
    assert task.value.content == expected


def test_text_value_missing_file_returns_placeholder(
    monkeypatch: pytest.MonkeyPatch, workspace: Path
) -> None:
    """Missing files fall back to a helpful placeholder message."""

    missing = workspace / "data" / "does_not_exist.txt"
    monkeypatch.chdir(workspace)
    rdf_path = _write_rdf(
        workspace / "text_missing.rdf",
        [
            "*version=100",
            "*documenttype=docx",
            "*datadir=./data",
            "section:content",
            ".text:description=file:does_not_exist.txt",
        ],
    )

    rdf = ReportDataFile(str(rdf_path), _root=[])
    task = next(t for t in rdf.tasks if t.target == "text:description")
    task.value.load()

    assert "non existing file" in task.value.content
    assert "does_not_exist.txt" in task.value.content
    

def test_text_value_embedded_literal(monkeypatch: pytest.MonkeyPatch, workspace: Path) -> None:
    """Quoted text is passed through without touching the filesystem."""

    monkeypatch.chdir(workspace)
    rdf_path = _write_rdf(
        workspace / "text_literal.rdf",
        [
            "*version=100",
            "*documenttype=docx",
            "section:content",
            ".text:description='Embedded literal line'",
        ],
    )

    rdf = ReportDataFile(str(rdf_path), _root=[])
    task = next(t for t in rdf.tasks if t.target == "text:description")
    task.value.load()

    assert task.value.content == "Embedded literal line"
    assert task.value.type == "str"
