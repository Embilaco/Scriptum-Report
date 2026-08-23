"""Helpers for numbering values."""

import types

class IntegerValue:
    def __init__(self, value: int):
        self.value = value
        
    @property
    def content(self):
        return str(self)

    def __repr__(self) -> str:
        return f"{self.value!r}"

    def __str__(self) -> str:
        return str(self.value)

class FloatValue:
    def __init__(self, value: float, settings=None):
        if settings is None:
            settings = {}
        self.value = value
        self.floatformat = getattr(settings, 'floatformat', '7.4f')

    @property
    def content(self):
        return str(self)

    def __repr__(self) -> str:
        return f"'{self.value}' - use format '{self.floatformat}'"

    def __str__(self) -> str:
        fformat = (f"{{:{self.floatformat}}}").format
        return fformat(self.value)

class NumberValue:
    """A counter: a pre-expanded sequence of numbered strings, walked by
    ``next()`` -- reading ``content`` advances it (see *NumberValue.content
    advances an iterator* on the values board).

    Three parts, given separately -- ``{numbering: kind, format: 'Figure %s',
    start: 1}`` -- where the text format packed them into one
    ``numbering:kind:format[:start]`` value that this class split on ``:``.

    ``kind``    ``1`` (arabic), ``a``/``A`` (letters), ``i``/``I`` (roman, to
                39), or ``F`` (free: ``start`` is a ``;``-separated list of
                the values themselves). Given as a string or, for ``1``, an int.
    ``format``  a ``%``-pattern with one ``%s``; a ``:`` in it is just text.
    ``start``   the first counter value (an int, default 1), or the list for
                ``F``.

    An unknown kind or an unusable start does not raise: ``str`` says what went
    wrong and the sequence is empty, the house rule for every value class.
    """

    def __init__(self, kind, format, start=None):
        """Expand the counter from its parts."""

        k = str(kind).strip()
        f = str(format)
        value = f'numbering {k!r} {f!r}' + (f' from {start!r}' if start is not None else '')

        err = False
        if k == 'F':
            s = '' if start is None else str(start)
        else:
            try:
                s = 1 if start is None else int(start)
            except Exception:
                self.str = f'- failed to understand {value}'
                values = []
                err = True

        if not err:
            values = []
            if k == 'F':
                values = [f % v for v in s.split(';')]
                s = 1
            else:
                for i in range(100):
                    if k == '1':
                        values += [f % (i + 1)]
                    elif k == 'a':
                        values += [f % chr(i + 97)]
                        if i >= 26:
                            break
                    elif k == 'A':
                        values += [f % chr(i + 65)]
                        if i >= 26:
                            break
                    elif k == 'i':
                        values += [(f % self._int_to_roman(i + 1)).lower()]
                        if i >= 39:
                            break
                    elif k == 'I':
                        values += [f % self._int_to_roman(i + 1)]
                        if i >= 39:
                            break
                    else:
                        self.str = f'- unknown number format in {value}'
                        values = []
                        err = True
                        break

            values = values[s - 1:]

        if not err:
            self.str = '[ ' + str(values[:3])[1:-1] + ', ... ]'

        self.numbers = iter(values)

    def __next__(self):
        return next(self.numbers)

    @staticmethod
    def _int_to_roman(input: int) -> str:
        """Convert an integer to a Roman numeral (up to 39)."""

        ints = (10, 9, 5, 4, 1)
        nums = ('X', 'IX', 'V', 'IV', 'I')
        result = []
        for i in range(len(ints)):
            count = int(input / ints[i])
            result.append(nums[i] * count)
            input -= ints[i] * count
        return ''.join(result)

    def __repr__(self) -> str:
        return self.str

    @property
    def content(self):
        return next(self)

ZeroValue = types.ModuleType('ZeroFloat')
ZeroValue.object = FloatValue(0.0)
ZeroValue.type = 'float'
