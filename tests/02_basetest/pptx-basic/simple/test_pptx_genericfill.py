"""``genericFill`` hands a text file's content to the element it fills.

The branch read ``value.load().content`` -- and ``Value.load()`` returned
None, so a direct ``text:`` file fill on a slide would have raised
``AttributeError``. No shipped layout carries a ``<text:…/>`` placeholder, so
the branch is exercised here with a recording element rather than a deck.
"""

from pathlib import Path
import sys

import pytest

pytest.importorskip('pptx')             # Scriptum._pptx needs the library

THIS_DIR = Path(__file__).resolve().parent
CASE_ROOT = THIS_DIR.parent
if str(CASE_ROOT) not in sys.path:
    sys.path.append(str(CASE_ROOT))

from _setup_pptx_basic import *          # noqa: F401,F403

from Scriptum._pptx.base import genericFill


class Recording:
    """An element that remembers what it was asked to write."""

    def __init__(self):
        self.replaced = []

    def replaceTagInAll(self, tagname, replace):
        self.replaced.append((tagname, replace))
        return True


def test_a_text_file_fill_writes_the_files_content(tmp_path, monkeypatch):
    import Scriptum

    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'words.txt').write_text('lorem ipsum\n', encoding='utf-8')
    (tmp_path / 'case.yaml').write_text(
        '_scriptum_:\n  version: 4\n  documenttype: pptx\n  datadir: ./data\n'
        '_content_:\n  - Material:\n      - text:body: {file: words.txt}\n',
        encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    rdf = Scriptum.ReportDataFile('case.yaml')
    task = next(t for t in rdf.tasks if t.target == 'text:body')
    assert (task.value.type, task.value.subtype) == ('file', 'text')

    element = Recording()
    genericFill([element], task)

    assert element.replaced == [('text:body', 'lorem ipsum\n')]
