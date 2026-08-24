#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""What the shared element layer requires of the data it is given.

`element/` is the code both back ends share. It must be independent of the
document format *and* of where the content came from, so it cannot import
from `rdf` -- that would tie the shared layer to one particular producer and
reverse the intended dependency direction (see `rdf/namespaces.py`).

Instead of importing rdf's classes, `element/` states its requirements as
structural protocols. Any object with the right shape satisfies them; rdf's
`TableValue` and `Table` already do, without either package importing the
other. A different producer -- another tool, a test double, a future
non-rdf front end -- can drive these elements by matching the same shape.

These are typing constructs only. Nothing here is enforced at runtime, and
importing this module costs nothing.
"""

from typing import Any, Protocol, Sequence


class TableContent(Protocol):
    """Parsed, rectangular table data ready to be written into a document."""

    @property
    def rows(self) -> int:
        """Number of data rows."""

    @property
    def cols(self) -> int:
        """Number of columns; rows are padded to this width."""

    @property
    def data(self) -> Sequence[Sequence[Any]]:
        """Row-major cell values. Cells are written with ``str()``."""


class TableSource(Protocol):
    """A source that can supply table content on demand.

    ``content`` is deliberately a property: producers are expected to load
    lazily and cache, so it may be read more than once cheaply. It is only
    meaningful when ``exists`` is true -- a caller that skips that check is
    responsible for whatever the producer returns.

    ``str(source)`` should yield a human-readable explanation when ``exists``
    is false; that string is what gets written into the document in place of
    the missing table.
    """

    @property
    def exists(self) -> bool:
        """Whether the underlying source could be located."""

    @property
    def content(self) -> TableContent:
        """The parsed table. Only meaningful when :attr:`exists` is true."""


__all__ = ['TableContent', 'TableSource']
