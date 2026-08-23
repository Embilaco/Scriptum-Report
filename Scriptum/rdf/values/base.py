"""The Value wrapper: one flat surface over the concrete value classes."""

from .date_value import DateValue
from .file_value import FileValue
from .number_value import FloatValue
from .number_value import IntegerValue
from .length_value import LengthValue
from .number_value import NumberValue
from .text_value import TextValue, StringValue
from .table_value import TableValue
from .color_value import ColorValue
from .image_value import ImageValue, AnimationValue
from .namevalues_value import NameValue


class Value:
    """A typed value, as a back end sees it.

    ``Value`` is a **wrapper, not a base class**: it holds a concrete value
    object (``DateValue``, ``TableValue``, ``StringValue``, ...) as
    ``self.object`` and exposes the flat surface every consumer relies on --
    ``type``, ``subtype``, ``tostring``, ``content`` and ``load()``. The
    concrete classes share no base class and agree by convention only; see
    *The Value wrapper and its duck-typed protocol* on the values board.

    It is built with its type **already decided**. The loader
    (``Scriptum/rdf/loader/fills.py``) reads a fill's shape and the target's
    namespace, picks the class, constructs the object and calls this with the
    result; nothing here inspects a string to find out what it is. The ``.rdf``
    text format needed such a guess -- a line offered nothing else to go on,
    so ``Value`` matched prefixes (``file:``, ``date:``, a unit suffix, ...) and
    fell through to a literal number -- and that parser went with the format.
    Every delimiter collision of the old value grammar went with it: nothing
    splits on ``+``, ``=`` or ``:``, so ``file: a+b.png`` is an ordinary path.

    ``type`` is the dispatch result a back end branches on: ``file``,
    ``parfile``, ``str``, ``datetime``, ``int``, ``float``, ``length``,
    ``color``, ``numbering``, ``readfrom``, ``newsection``. ``subtype`` is the
    file flavour -- ``image``, ``video``, ``text``, ``table``, ``parameterfile``,
    ``unclear`` -- and ``None`` for anything that is not a file. ``tostring``
    says whether ``str(value)`` may be used as the replacement text; when it is
    false ``str()`` returns ``''`` so a file value never leaks its filename into
    the document.
    """

    def __init__(self, type, object, tostring, subtype=None):
        self.type = type
        self.object = object
        self.subtype = subtype
        self.tostring = tostring
        self.content = None

    def applyActions(self, actions):
        if hasattr(self.object,'applyActions'):
            self.object.applyActions(actions)

    def load(self):
        """load the content of this value from whatever source it comes from"""
        if hasattr(self.object,'content'):
            self.content = self.object.content
        else:
            self.content = str(self)

    def __repr__(self) -> str:
        return f'{self.type} {self.object!r}'

    def __str__(self) -> str:
        if self.tostring:
            return str(self.object)
        return ''
