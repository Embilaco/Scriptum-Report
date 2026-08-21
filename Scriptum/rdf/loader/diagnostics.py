#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""Positioned diagnostics for the YAML document loader.

Two properties are carried over from the text format deliberately:

* **Errors accumulate.** A document with six mistakes reports six. The root
  document raises once, at the end, with the whole set joined together.
* **Every diagnostic names a place.** The text format could give a file and a
  line number. A YAML document can do better, and should: a line number alone
  does not say *which* part of a deeply indented structure is wrong.

So a diagnostic carries a position **and** an address path::

    fragments/tools.yaml:14:7  at _content_ > section:tool > subsection:tool
      unknown modifier 'Descriptoin'

That format is why the loader walks the node graph rather than calling
``yaml.safe_load``: plain Python objects have no positions attached, while
every node carries a ``start_mark`` with file, line and column.

PyYAML marks are 0-based. Humans, and every editor that will jump to one of
these, are 1-based -- :meth:`Position.of` converts once, here, so no caller has
to remember to.
"""


class Position:
    """Where in a document something is. Line and column are 1-based."""

    __slots__ = ('filename', 'line', 'column')

    def __init__(self, filename, line, column):
        self.filename = filename
        self.line = line
        self.column = column

    @classmethod
    def of(cls, node, filename):
        """Build from a PyYAML node, converting its 0-based mark."""
        mark = node.start_mark
        return cls(filename, mark.line + 1, mark.column + 1)

    def __str__(self):
        # A missing filename must still render: __str__ returning None is a
        # TypeError, which would turn a diagnostic about someone's document
        # into a crash inside the error reporting.
        name = self.filename or '<document>'
        # Line 0 means "somewhere in this file" -- a document that would not
        # parse at all, say. Printing ':0:0' invites a reader to go looking for
        # a line that is not the one at fault.
        if not self.line:
            return name
        return f'{name}:{self.line}:{self.column}'

    def __repr__(self):
        return f'Position({self!s})'

    def __eq__(self, other):
        if not isinstance(other, Position):
            return NotImplemented
        return (self.filename, self.line, self.column) == \
               (other.filename, other.line, other.column)

    def __hash__(self):
        return hash((self.filename, self.line, self.column))


class Diagnostic:
    """One problem, with where it is and what part of the document it is in."""

    __slots__ = ('position', 'path', 'message')

    def __init__(self, position, path, message):
        self.position = position
        self.path = tuple(path)
        self.message = message

    def __str__(self):
        head = str(self.position)
        if self.path:
            head += '  at ' + ' > '.join(self.path)
        return f'{head}\n  {self.message}'

    def __repr__(self):
        return f'Diagnostic({self.message!r} at {self.position!s})'


class DocumentError(Exception):
    """Raised once by the root document, carrying every diagnostic.

    A parse is all-or-nothing at the top: an included fragment hands its
    diagnostics upward rather than raising, so the reader sees the whole set
    instead of only the first file that went wrong.
    """

    def __init__(self, diagnostics):
        self.diagnostics = list(diagnostics)
        super().__init__('\n'.join(str(d) for d in self.diagnostics))


class Diagnostics:
    """An accumulating list of problems.

    Deliberately not an exception-raiser: callers report and keep walking, so
    one malformed entry does not hide the next five.
    """

    def __init__(self):
        self.entries = []

    def error(self, message, node=None, filename=None, path=()):
        """Record a problem. ``node`` supplies the position when there is one."""
        position = Position.of(node, filename) if node is not None \
            else Position(filename, 0, 0)
        self.entries.append(Diagnostic(position, path, message))
        return self.entries[-1]

    def extend(self, other):
        """Take on another document's diagnostics -- how an include reports."""
        self.entries.extend(other.entries if isinstance(other, Diagnostics) else other)

    def ordered(self):
        """Diagnostics as a reader wants them: by position within each file.

        Files keep the order they were first reported in, which is include
        order and carries meaning. Within a file the entries are sorted by line
        and column, because the order they were *found* in does not: the
        top-level keys of a document are checked before the settings block
        nested inside it, so a mistake on line 7 would otherwise be printed
        above one on line 3.

        The sort is stable, so two diagnostics at the same position stay in the
        order they were recorded.
        """
        order = {}
        for entry in self.entries:
            order.setdefault(entry.position.filename, len(order))
        return sorted(
            self.entries,
            key=lambda e: (order[e.position.filename],
                           e.position.line, e.position.column),
        )

    def raise_if_any(self):
        """Raise :class:`DocumentError` with the whole set, or return quietly."""
        if self.entries:
            raise DocumentError(self.ordered())

    def report(self):
        return '\n'.join(str(entry) for entry in self.ordered())

    def __bool__(self):
        return bool(self.entries)

    def __len__(self):
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    def __repr__(self):
        return f'Diagnostics({len(self.entries)} entries)'


__all__ = ['Position', 'Diagnostic', 'Diagnostics', 'DocumentError']
