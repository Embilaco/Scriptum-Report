# hold all generic info for all tests

from pathlib import Path
import sys, os
import types
import shutil
import pytest

# Ensure the package root is importable
TEST_ROOT = Path(__file__).resolve().parent # -> resolve to Scriptum/tests/.

DATA_SOURCE = TEST_ROOT / 'data_source'

# install folder of Scriptum
SCRIPTUM_BASE = TEST_ROOT.parent
#SCRIPTUM_ROOT = TEST_ROOT.parent.parent
#if str(SCRIPTUM_ROOT) not in sys.path:
#    sys.path.append(str(SCRIPTUM_ROOT)) # allow us to import SCRIPTUM

# in order to test RDF we need to import from inside SCRIPTUM
if str(SCRIPTUM_BASE) not in sys.path:
    sys.path.append(str(SCRIPTUM_BASE)) 
    


def ensure_link(src: Path, dest: Path) -> None:
    """used for ...
    """
    if dest.exists():
        return
    if src.is_dir():
        try:
            dest.symlink_to(src, target_is_directory=True)
        except OSError:
            shutil.copytree(src, dest)
    else:
        try:
            dest.symlink_to(src)
        except OSError:
            shutil.copy(src, dest)

# Some modules expect Pillow to be present; provide a simple stub when it is not
# available in the execution environment.
try:  # pragma: no cover - depends on optional dependency
    import PIL  # type: ignore  # noqa: F401
    import PIL.Image  # type: ignore  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - executed only when Pillow missing
    pil_module = types.ModuleType("PIL")
    pil_image_module = types.ModuleType("PIL.Image")
    pil_image_module.open = lambda filename: None  # type: ignore[assignment]
    pil_module.Image = pil_image_module  # type: ignore[attr-defined]
    sys.modules.setdefault("PIL", pil_module)
    sys.modules.setdefault("PIL.Image", pil_image_module)

MonkeyPatch = pytest.MonkeyPatch

def write(tmp_path, name, content):
    f = tmp_path / name
    f.write_text(content)
    return f

import Scriptum.rdf.reportDataFile as rdf_module # pyright: ignore[reportMissingImports]

ReportDataFile = rdf_module.ReportDataFile
ReportTask = rdf_module.ReportTask

# There is no autouse reset fixture any more. The text parser kept
# process-global state (a numbering tree and a serial counter on the classes)
# that had to be cleared between tests; the YAML reader keeps none, so two
# documents in one interpreter do not see each other.

def setupTestEnvironment(tmp_path, data_source, report_source, include_patterns):
    """setup the test environment based on and for pytest"""
    ensure_link(data_source, tmp_path / "data")

    include_files = set()
    for pattern in include_patterns:
        include_files.update(report_source.glob(pattern))

    #print(include_files)
    for src in include_files:
        ensure_link(src, tmp_path / src.name)

    os.chdir(tmp_path)

    print(f'\nTEST runs in {tmp_path}')