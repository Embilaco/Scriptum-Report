"""A date or time, stamped when the document is read."""

import re
from datetime import datetime

try:
    from dateutil import parser as date_parser
    HAS_DATEUTIL = True
except ModuleNotFoundError:  # pragma: no cover - fallback for environments without python-dateutil
    HAS_DATEUTIL = False

    class _SimpleDateParser:
        """Lightweight fallback parser approximating :mod:`dateutil.parser`."""

        _FORMATS = [
            '%m/%d/%y %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%y',
            '%m/%d/%Y',
            '%a %b %d %H:%M:%S %Y',
            '%H:%M:%S',
            '%H:%M',
        ]

        @staticmethod
        def parse(value: str) -> datetime:
            trimmed = value.strip()
            if not trimmed:
                raise ValueError('Empty date string')

            iso_candidate = trimmed.replace('Z', '+00:00')
            try:
                return datetime.fromisoformat(iso_candidate)
            except ValueError:
                pass

            for fmt in _SimpleDateParser._FORMATS:
                try:
                    return datetime.strptime(trimmed, fmt)
                except ValueError:
                    continue

            raise ValueError(f"Unable to parse date string: {value!r}")

    date_parser = _SimpleDateParser()


_NUMERIC = re.compile(r'^[-+]?\d+(?:\.\d+)?$')

#: The epoch, local time -- what an unreadable spec degrades to.
EPOCH = datetime.fromtimestamp(0)


class DateValue:
    """A date, formatted **in the constructor** -- the one value type that is
    fully eager (see *Dates are stamped at parse time* on the values board).
    Everything is **naive local time**: ``now`` is the local clock, a
    timestamp is converted to local time, and no time zone is ever attached.

    ``spec`` is what to evaluate, exactly as the document gives it:

    ==================  ======================================================
    ``now``             the current date and time; default format
                        ``settings.datetimeformat``. Any case.
    ``today``           the current date; default format ``settings.dateformat``.
                        Any case.
    a number            a Unix timestamp -- an ``int``/``float``, or a string
                        of digits; 13 digits or more are taken as milliseconds
    any other string    a date, read by ``dateutil`` (or the bundled fallback
                        parser when it is absent, which knows ISO 8601 and a
                        handful of US-ordered forms). ``dateutil`` reads an
                        ambiguous ``05/06/22`` month-first; ISO 8601
                        (``2022-12-15 14:24:59``) is the form that cannot be
                        misread.
    ==================  ======================================================

    ``format`` is the strftime pattern, given separately -- ``{date: now,
    format: '%H:%M:%S'}`` -- so a colon in either part is just a character.
    The text format packed spec and pattern into one ``date:spec:'fmt'`` value
    that this class then split on ``:`` with quote tracking; once YAML had
    consumed the quotes around a date string, a time inside it was split like
    a delimiter (``'12/15/22 14:24:59'`` read as 14:00 with the pattern
    ``24:59``). Taking the parts apart is what fixed it.

    **It does not raise, and it does not stay silent either.** Like every
    value class it degrades -- a spec that does not parse becomes the epoch, a
    pattern ``strftime`` rejects falls back to ``settings.dateformat`` -- but
    it says so: ``valid`` is False and ``problem`` names what went wrong, the
    way ``ColorValue`` reports an unrecognised colour. The loader reads those
    and refuses the document with the problem as a diagnostic, so a stray
    ``01. Jan 1970`` never reaches a page from a document; the degradation
    only matters to a caller constructing the class by hand. Note that
    ``strftime`` rejects an unknown directive on Windows only (glibc prints it
    literally), so that half is platform-dependent by nature.
    """

    def __init__(self, spec, settings, format=None):
        problem = None
        keyword = spec.strip().lower() if isinstance(spec, str) else None

        if keyword == 'now':
            dt = datetime.now()
            default = settings.datetimeformat
        elif keyword == 'today':
            dt = datetime.today()
            default = settings.dateformat
        else:
            dt = self._parse(spec)
            default = settings.datetimeformat
            if dt is None:
                problem = f'{spec!r} is not a date'
                if not HAS_DATEUTIL:
                    problem += (' (python-dateutil is not installed; without it only '
                                'ISO 8601 and a few common forms are recognised)')
                dt = EPOCH

        self.format = format if format else default
        self.dt = dt

        try:
            self.value = dt.strftime(self.format)
        except (ValueError, TypeError) as error:
            problem = problem or f'{self.format!r} is not a strftime pattern: {error}'
            self.value = dt.strftime(settings.dateformat)

        self.valid = problem is None
        self.problem = problem

    @staticmethod
    def _parse(spec):
        """A timestamp or a date string to a datetime, or None."""
        if isinstance(spec, bool) or spec is None:
            return None
        text = str(spec).strip()
        if not text:
            return None

        if isinstance(spec, (int, float)) or _NUMERIC.match(text):
            try:
                stamp = float(text)
                if '.' not in text and len(text.lstrip('+-')) >= 13:
                    stamp /= 1000.0
                return datetime.fromtimestamp(stamp)
            except (ValueError, OverflowError, OSError):
                return None

        try:
            return date_parser.parse(text)
        except (ValueError, OverflowError, TypeError):
            return None

    @property
    def content(self):
        return str(self)

    def __repr__(self) -> str:
        shown = f"'{self.value}' - use format '{self.format}'"
        if not self.valid:
            shown += f' - invalid: {self.problem}'
        return shown

    def __str__(self) -> str:
        return self.value
