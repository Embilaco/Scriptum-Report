#
# part of:
#   S C R I P T U M
#

"""The report data file -- the front door to reading a report document.

A report document is written in YAML and named ``.yaml``; it is read by
:mod:`Scriptum.rdf.loader`, and this class is the public handle on the result.
The class keeps its name on purpose: the thing has not changed, it is still the
report data file, in a different syntax. Only the extension moved, because the
extension is the one name *tools* read -- highlighting, folding and validation
all key off ``.yaml``, and for a format whose structure is carried by
indentation that is not cosmetic.

The hand-written ``.rdf`` text syntax that used to be read here is gone. Nothing
reads both: the YAML format supersedes it outright, so a path that is not a
``.yaml`` document is refused with a message rather than guessed at.
"""

import os

from .loader import Diagnostics, DocumentError, load
from .tasks import ReportTask

#: Extensions read as report documents.
YAML_SUFFIXES = ('.yaml', '.yml')


class ReportDataFile:
    """A report document, read into the task list a back end runs.

    The surface a back end uses is ``tasks``, ``settings`` and ``errors``. A
    document that does not load raises :class:`DocumentError` carrying every
    diagnostic, not the first -- and ``errors`` holds the same set as strings,
    so a caller can read the whole list either way.

    Reading keeps no state outside the instance: two documents in one
    interpreter do not see each other.
    """

    def __init__(self, filename, debug=False):
        self.errors = []
        self.tasks = []
        self.settings = None
        self.source = os.path.abspath(filename)

        ReportTask.set_debug(debug)

        if not str(filename).lower().endswith(YAML_SUFFIXES):
            diagnostics = Diagnostics()
            diagnostics.error(
                f'not a report document: {os.path.basename(str(filename))!r}. '
                'A report document is written in YAML and named '
                f'{" or ".join(YAML_SUFFIXES)}; the .rdf text format is no '
                'longer read.',
                filename=str(filename))
            self.errors = [str(entry) for entry in diagnostics]
            diagnostics.raise_if_any()

        try:
            document = load(filename)
        except DocumentError as error:
            self.errors = [str(entry) for entry in error.diagnostics]
            raise

        self.tasks = document.tasks
        self.settings = document.settings

    def __repr__(self):
        """For debugging: where it came from, what it runs under, how much."""
        return (f'ReportDataFile({self.source!r}, {len(self.tasks)} tasks, '
                f'settings={self.settings!r})')

    def inspect(self):
        """One dict per task -- the debug view the notebooks print."""
        return [t._inspect() for t in self.tasks]

    def showFiles(self):
        """Cycle through the tasks and show which files are missing.

        Existence was decided when the document was read (see *Content is
        lazy, existence is eager* on the values board), so this is the place to
        audit the inputs before a document is built.
        """

        missing = ['Missing files']
        found = ['Existing files']
        for task in self.tasks:
            if task.value.type in ['file', 'parfile']:
                if not task.value.object.exists:
                    missing += [task.value.object.filename]
                else:
                    found += [task.value.object.filename]

        print('\n '.join(found))
        print('\n '.join(missing))
