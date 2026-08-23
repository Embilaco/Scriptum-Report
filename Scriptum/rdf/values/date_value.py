"""A date or time, stamped when the document is read."""

import re
from datetime import datetime

try:
    from dateutil import parser as date_parser
except ModuleNotFoundError:  # pragma: no cover - fallback for environments without python-dateutil
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


class DateValue:
    """A date, formatted **in the constructor** -- the one value type that is
    fully eager (see *Dates are stamped at parse time* on the values board).

    ``spec`` is what to evaluate, exactly as the document gives it:

    ==================  ======================================================
    ``'now'``           the current date and time; default format
                        ``settings.datetimeformat``
    ``'today'``         the current date; default format ``settings.dateformat``
    a number            a Unix timestamp -- an ``int``/``float``, or a string
                        of digits; 13 digits or more are taken as milliseconds
    any other string    a date, read by ``dateutil`` (or the bundled fallback
                        parser when it is absent)
    ==================  ======================================================

    ``format`` is the strftime pattern, given separately -- ``{date: now,
    format: '%H:%M:%S'}`` -- so a colon in either part is just a character.
    The text format packed spec and pattern into one ``date:spec:'fmt'`` value
    that this class then split on ``:`` with quote tracking; the loader handed
    it the date string without the quotes YAML had consumed, and a time inside
    the string was split like a delimiter (``'12/15/22 14:24:59'`` read as
    14:00 with the pattern ``24:59``). Taking the parts apart is what fixed it.

    Two degradations are kept as they were and are on the date audit's list:
    a date that does not parse becomes the **epoch** silently, and a pattern
    ``strftime`` rejects falls back to ``settings.dateformat``. ``self.dt``
    holds the datetime either way.
    """

    def __init__(self, spec, settings, format=None):
        if isinstance(spec, str):
            spec = spec.strip()

        if spec == 'now':
            dt = datetime.now()
            default = settings.datetimeformat
        elif spec == 'today':
            dt = datetime.today()
            default = settings.dateformat
        else:
            dt = self._parse(spec)
            default = settings.datetimeformat

        self.format = format if format else default
        self.dt = dt

        try:
            self.value = dt.strftime(self.format)
        except Exception:
            self.value = dt.strftime(settings.dateformat)

    @staticmethod
    def _parse(spec):
        """A timestamp or a date string to a datetime; the epoch if neither."""
        text = str(spec).strip()

        if isinstance(spec, (int, float)) and not isinstance(spec, bool) \
                or _NUMERIC.match(text):
            try:
                stamp = float(text)
                if '.' not in text and len(text.lstrip('+-')) >= 13:
                    stamp /= 1000.0
                return datetime.fromtimestamp(stamp)
            except Exception:
                pass

        if text:
            try:
                return date_parser.parse(text)
            except Exception:
                pass

        return datetime.fromtimestamp(0)

    @property
    def content(self):
        return str(self)

    def __repr__(self) -> str:
        return f"'{self.value}' - use format '{self.format}'"

    def __str__(self) -> str:
        return self.value
