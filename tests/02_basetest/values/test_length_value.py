# tests length values: the class itself, and how a document reaches it

from pathlib import Path

import pytest

from _setup_values import *

from Scriptum.rdf.loader import DocumentError
from Scriptum.rdf.values.length_value import LengthValue


@pytest.mark.parametrize("written, shown", [
    ("1in", "1.0 - unit: in"),
    ("12.3cm", "12.3 - unit: cm"),
    ("15pt", "15.0 - unit: pt"),
    ("123.56mm", "123.56 - unit: mm"),
    ("4inch", "4.0 - unit: in"),
])
def test_length_units(written, shown):
    assert repr(LengthValue(written)) == shown


def test_a_length_that_is_not_a_number_says_so():
    """The class degrades rather than raising, like every other value class:
    the message lands where the length would have."""
    wrong = LengthValue("123.3.4mm")
    assert "cannot evaluate length:" in repr(wrong)


def _document(tmp_path: Path, modifiers: str) -> Path:
    base = tmp_path / "testLength.yaml"
    base.write_text("\n".join([
        "_scriptum_:",
        "  version: 4",
        "  documenttype: docx",
        "_content_:",
        "  - section:mysection:",
        "      - subsection:foo:",
        f"          - image:generic: {{file: some.png, {modifiers}}}",
    ]), encoding='utf-8')
    return base


def test_lengths_reach_a_document_through_the_length_modifiers(tmp_path: Path):
    """A length is recognised by the modifier's *name* -- width, height, top,
    left, bottom, right -- not by sniffing a unit off the end of any value.
    """
    base = _document(tmp_path, "width: 1in, height: 12.3cm, top: 15pt, left: 123.56mm")

    rdf = ReportDataFile(str(base))
    image = next(t for t in rdf.tasks if t.target == "image:generic")

    lengths = {name: image.actions[name] for name in ('width', 'height', 'top', 'left')}
    assert all(value.type == 'length' for value in lengths.values())
    assert repr(lengths['width'].object) == "1.0 - unit: in"
    assert repr(lengths['height'].object) == "12.3 - unit: cm"
    assert repr(lengths['top'].object) == "15.0 - unit: pt"
    assert repr(lengths['left'].object) == "123.56 - unit: mm"


@pytest.mark.parametrize("written", ["12km", "123.3.4mm", "12"])
def test_a_length_modifier_refuses_what_is_not_a_length(tmp_path: Path, written):
    """The text format let ``12km`` fall through to ``invalid`` and surface in
    the finished document. The loader names the modifier and the units."""
    base = _document(tmp_path, f"width: {written}")

    with pytest.raises(DocumentError) as caught:
        ReportDataFile(str(base))

    assert "width needs a length with a unit" in str(caught.value)
