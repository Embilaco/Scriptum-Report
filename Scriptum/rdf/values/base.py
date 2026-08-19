"""Base Value implementation and dispatch helpers."""

import ast
import os

#from .. import common
#from ..common import removeQuotes
#from ..values import *
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

from ..common import getCorrectFile, removeQuotes, is_test_debug

class Value:
    """Store the value with all arguments."""

    def __init__(self, value: str, settings, target=None):
        lvalue = value.lower()
        self.type = 'unknown'
        self.object = None
        self.subtype = None
        self.tostring = None
        self.content = None

        if lvalue.startswith('file:'):
            # all kind of file-types
            self.type = 'file'
            filename = removeQuotes(value[5:].strip())
            #print(filename, settings.datadir, os.curdir)
            filename, _exists = getCorrectFile(filename, False, settings.datadir)

            if target == 'image' or target == 'image:poster': # strange, should be 'image' only
                self.object = ImageValue(filename, _exists)
            elif target == 'text':
                self.object = TextValue(filename, _exists)
            elif target == 'video':
                self.object = AnimationValue(filename, _exists)
            elif target == 'table':
                self.object = TableValue(filename, _exists, settings)
            else:
                # generic - should lead to error handling only?
                self.object = FileValue(filename, _exists)
            
            self.subtype = self.object.subtype
            self.tostring = False

        elif lvalue.startswith('parfile:'):
            # special type of a parameterfile
            self.type = 'parfile'
            restvalue = value[8:]
            _v = restvalue.split(':')
            parname = _v[-1]
            filename = removeQuotes(restvalue[:-(len(parname)+1)])
            filename, _exists = getCorrectFile(filename, False, settings.datadir)
            self.object = NameValue(filename, _exists, settings, parname)
            self.subtype = self.object.subtype
            self.tostring = False

        elif (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
            # quoted string
            self.type = 'str'
            self.object = StringValue(value[1:-1].replace('\\n', '\n'))
            self.tostring = True

        elif lvalue.startswith('@'):
            # used in tables where the caption/description is read from the table itself
            # mangled later into actions
            self.type = 'readfrom'
            self.object = lvalue[1:]
            self.tostring = False

        elif lvalue.startswith('newsection:'):
            # this will be automatically created for new section definitions
            self.type = 'newsection'
            self.object = ''
            self.tostring = False

        elif lvalue.startswith('date:'):
            # date and or time value
            self.type = 'datetime'
            v = value.split(':', 1)[1]
            self.object = DateValue(v, settings)
            self.tostring = True

        elif lvalue.startswith('numbering:'):
            # numbering for sections, counters etc
            self.type = 'numbering'
            self.object = NumberValue(value[10:])
            self.tostring = True

        elif value[-2:].lower() in ['cm', 'mm', 'in', 'pt']:
            # length value
            self.type = 'length'
            self.object = LengthValue(value)
            self.object.floatformat = settings.floatformat
            self.tostring = True

        elif target == 'color':
            # color value
            self.type = 'color'
            self.object = ColorValue(value)
            self.tostring = False

        else:
            # either integer or float or error
            try:
                # literal_eval, never eval: this reaches arbitrary text from a
                # data file, and eval() executed it. Only a literal number is
                # wanted here, and anything else falls through to 'invalid'
                # below, which is visible rather than silent.
                v = ast.literal_eval(value)
                if type(v) == int:
                    self.type = 'int'
                    self.object = IntegerValue(v)
                elif type(v) == float:
                    self.type = 'float'
                    self.object = FloatValue(v, settings)
                self.tostring = True

            except Exception as e:
                self.type = 'invalid'
                self.object = f'{e}: {value}'
                if not is_test_debug:
                    print(f'invalid {value!r} {lvalue!r}')
                self.tostring = True

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
