#!/usr/bin/env python3
#
# part of:
#   S C R I P T U M 
#


class StringValue:
    """from rdf/task to content used in elements etc."""
    def __init__(self, value):
        self.value = value

    @property
    def content(self):
        return str(self)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return repr(self.value)


class TextValue:
    """from rdf/task to content used in elements etc."""
    def __init__(self, filename, exists):
        self.subtype = 'text'
        self.filename = filename
        self.exists = exists

    @property
    def content(self):
        if self.exists:
            # UTF-8 like every other file-backed value; the platform default
            # made the same document behave differently per machine.
            with open(self.filename, 'r', encoding='utf-8') as f:
                content = '\n'.join(f.readlines())
        else:
            content = str(self)
        return content

    def __str__(self) -> str:
        return f'non existing file {self.filename!r}'

    def __repr__(self) -> str:
        return f"{self.filename!r} exists: {self.exists} ({self.subtype})"

    #def getValue(self):
    #    return self.content

    # def getText(self) -> str:
    #     if self.subtype == 'text':
    #         if self.exists:
    #             text = []
    #             with open(self.filename, 'r') as f:
    #                 text += f.readlines()
    #             return ''.join(text)
    #         return 'file %r not found' % self.filename
    #     return 'file %r is no textfile' % self.filename
