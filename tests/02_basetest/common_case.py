"""Reusable helpers for docx creation tests.

This module extracts the reusable pieces from the legacy notebook-based
"CreateDOCforEssay" test so that new docx-based scenarios can reuse the same
setup and execution flow. To create a new case, define a :class:`CaseConfig`
pointing at the relevant RDF and template files and call :func:`run_docx_case`.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from _setup_basetest import *
import Scriptum  # type: ignore



@dataclass
class CaseConfig:
    """Configuration for a document generation scenario.

    Attributes:
        name: Identifier used for debugging output.
        case_dir: Directory that contains the RDF and template files.
        rdf_name: Name of the RDF file to load from ``case_dir``.
        template_doc_name: Name of the input Word/PowerPoint document.
        output_name: Name of the generated document.
        include_patterns: Glob patterns (relative to ``case_dir``) that should
            be linked into the workspace before running the test.
        data_source_dir: Optional override for the shared data source folder.
        finish: open in Word/PowerPoint to update tables etc
        createpdf: save from Word/PowerPoint as PDF
    """

    name: str
    case_dir: Path
    rdf_name: str
    template_doc_name: str
    output_name: str
    include_patterns: Sequence[str] = field(default_factory=list)
    data_source_dir: Path | None = None
    finish: bool = False
    createpdf: bool = False


class WorkspaceBuilder:
    """Prepare a disposable workspace for document generation tests."""

    def __init__(self, tmp_path: Path, data_source_dir: Path = DATA_SOURCE):
        self.tmp_path = tmp_path
        self.data_source_dir = data_source_dir

    def build(self, case_dir: Path, include_patterns: Iterable[str]) -> Path:
        """Create a workspace with linked input data.

        The workspace mirrors the steps from the original notebook: it links the
        shared ``data_source`` folder and any case-specific files that match the
        provided glob patterns.
        """

        workdir = self.tmp_path / "workspace"
        workdir.mkdir()

        ensure_link(self.data_source_dir, workdir / "data")

        include_files: set[Path] = set()
        for pattern in include_patterns:
            include_files.update(case_dir.glob(pattern))

        if not include_files:
            patterns = ", ".join(include_patterns)
            msg = f"No files found in {case_dir} for patterns: {patterns}"
            raise FileNotFoundError(msg)

        for src in include_files:
            ensure_link(src, workdir / src.name)

        print(f'WORKSPACE: {workdir}')

        return workdir


def run_docx_case(config: CaseConfig, tmp_path: Path) -> Path:
    """Execute a document generation test based on the provided configuration.

    The function handles workspace creation, running Scriptum to typeset the
    document, and returning the path to the generated file.
    """

    workspace = WorkspaceBuilder(
        tmp_path, config.data_source_dir or DATA_SOURCE
    ).build(config.case_dir, config.include_patterns)

    current_dir = Path(os.getcwd())
    os.chdir(workspace)
    try:
        base_rdf = workspace / config.rdf_name
        rdf = Scriptum.ReportDataFile(base_rdf)

        document = Scriptum.ManagedDocx(config.template_doc_name)
        document.typesetting(
            rdf,
            addcopy=True,
            directfill=True,
            globalfill=True,
            cleanup=True,
            removetemplate=True,
            cleardust=True,
            setproperties=True,
        )

        output_path = workspace / config.output_name
        document.save(config.output_name, finish=config.finish, createpdf=config.createpdf)
    finally:
        os.chdir(current_dir)

    return output_path

def run_pptx_case(config: CaseConfig, tmp_path: Path) -> Path:
    """Execute a document generation test based on the provided configuration.

    The function handles workspace creation, running Scriptum to typeset the
    document, and returning the path to the generated file.
    """

    workspace = WorkspaceBuilder(
        tmp_path, config.data_source_dir or DATA_SOURCE
    ).build(config.case_dir, config.include_patterns)

    current_dir = Path(os.getcwd())
    os.chdir(workspace)
    try:
        base_rdf = workspace / config.rdf_name
        rdf = Scriptum.ReportDataFile(base_rdf)

        document = Scriptum.ManagedPptx(config.template_doc_name)
        document.artist(
            rdf,
            directfill=True,
            globalfill=True,
            cleardust=True,
            setproperties=True,
        )

        output_path = workspace / config.output_name
        document.document.core_properties.title='AutoReport'
        document.remove_slide(0)
    
        document.save(config.output_name, finish=config.finish, createpdf=config.createpdf)
    finally:
        os.chdir(current_dir)

    return output_path
