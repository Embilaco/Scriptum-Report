"""A report document is data. Reading one must never execute what it contains.

The ``.rdf`` text format's value dispatcher ended in a fall-through that read a
bare number with ``eval()``, so any value the earlier branches did not
recognise was executed as a Python expression at parse time -- reachable from
every ``.rdf`` and from every file ``&include=loopfiles:*.rdf`` pulled in. It
was changed to ``ast.literal_eval`` and then removed with the text parser.

A YAML document has no such path at all: a scalar is a string, a number or a
boolean, the dialect refuses unknown tags (``test_yaml_dialect.py``), and no
value class evaluates text. This pins the property where it matters -- at the
document -- so it does not come back through some future convenience.
"""

import os
from pathlib import Path

from _setup_values import *  # noqa: F401,F403 - ensure package import setup


# Marker: if the expression ran, os.environ would carry it afterwards.
PAYLOAD = '__import__("os").environ.setdefault("SCRIPTUM_RDF_EXECUTED", "yes")'


def _document(tmp_path: Path, fills: list[str]) -> Path:
    base = tmp_path / "payload.yaml"
    base.write_text("\n".join([
        "_scriptum_:",
        "  version: 4",
        "  documenttype: docx",
        "_content_:",
        "  - section:a:",
    ] + [f"      - {fill}" for fill in fills]), encoding='utf-8')
    return base


def test_an_expression_in_a_value_is_text_and_is_not_executed(tmp_path: Path):
    os.environ.pop('SCRIPTUM_RDF_EXECUTED', None)

    rdf = ReportDataFile(str(_document(tmp_path, [
        f"head: '{PAYLOAD}'",
        f"text:description: {{text: '{PAYLOAD}'}}",
        "call: '__import__(\"os\").getpid()'",
    ])))

    assert 'SCRIPTUM_RDF_EXECUTED' not in os.environ, (
        'reading a document executed code from a value'
    )
    values = [t.value for t in rdf.tasks if t.target]
    assert [v.type for v in values] == ['str', 'str', 'str']
    assert str(values[0]) == PAYLOAD
    assert str(os.getpid()) not in str(values[2])


def test_arithmetic_is_text_too(tmp_path: Path):
    """`2+3` used to evaluate to 5 in the text format, then to be flagged
    ``invalid``; as a YAML scalar it is the three-character string it is."""
    rdf = ReportDataFile(str(_document(tmp_path, ["sum: 2+3", "number: 42",
                                                   "real: 3.5"])))

    by_target = {t.target: t.value for t in rdf.tasks if t.target}
    assert (by_target['sum'].type, str(by_target['sum'])) == ('str', '2+3')
    assert by_target['number'].type == 'int'
    assert by_target['real'].type == 'float'
