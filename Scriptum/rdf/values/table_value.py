#!/usr/bin/env python3
#
# part of:
#   S C R I P T U M 
#

import csv, types

class TableValue:
    """always use this class to open the table and provide its content

    manages all kind of tables
    
    - csv: csv type
    - ... further types to be defined

    .position.table:generic=file:somefile.csv

    """
    def __init__(self, filename, exists, settings):

        self.subtype = 'table'
        self.separator = settings.csvseparator
        self.floatformat = settings.floatformat
        self.filename = filename
        self.exists = exists
        #self.data = []
        #self.cols=0
        #self.rows=0
        # add later:
        self.actions = {}
        self._parsed = False
    
    def applyActions(self, actions):
        self.actions = actions

    def __str__(self) -> str:
        return f'non existing file {self.filename!r}'

    def __repr__(self) -> str:
        return f"{self.filename!r} exists: {self.exists} ({self.subtype})"

    @property
    def content(self):
        if not self._parsed:
            self._raw_content = Table(self, self.actions, dataSource='CSV')
            self._parsed = True
        return self._raw_content
        
    def fill(self, element):
        # fill exactly one table in time
        element.fillTable(self)

class Table: 
    """wrapper for all the table types below but used as a type elsewhere
    
    
    """
    def __init__(self, object: TableValue, actions: dict = {}, dataSource: str = 'CSV'):
        if dataSource == 'CSV':
            _raw_content = CSVTable(object, actions)
        else:
            _raw_content = types.ClassType('UnknownTable')
            _raw_content.caption = 'unknown/not implemented TableType'
            _raw_content.data = []
            _raw_content.rows = 0
            _raw_content.cols = 0

        self.exists = object.exists
        self.filename = object.filename
        self.caption = _raw_content.caption
        self.rows = _raw_content.rows
        self.cols = _raw_content.cols
        self.data = _raw_content.data

class CSVTable:
    """try to read a CSV-file
    if in actions a "readfrom" is found it is read from this file
    and replaced by a "insert" and the content

    @row can be used with 'description' only for now

    otherwise
    ignore blank lines and lines starting with a hash #
    fill missing values by setting count of columns to the largest value

    an empty cell -- written empty, or missing from a short row -- reads as
    a single blank ' ', so the fill overwrites whatever sample text a
    template's table carries there instead of letting it show through
    (decided 2026-08-25)
    """
    def __init__(self, obj: TableValue, actions: dict):
        self.cols =0
        self.rows = 0
        self.data = []
        self.caption = None
        if obj.exists:
            data = []
            try:
                with open(obj.filename, 'r', encoding='utf-8') as f:
                    for row in csv.reader(f, delimiter=obj.separator):
                        data += [[v.strip() for v in row]] # clean it
            except Exception as e:
                data = [[f'Cannot read csv file {obj.filename!r}']]
            
            desc = ''
            #print(actions, 'description' in actions, actions.keys())
            if 'description' in actions:
                v = actions['description']
                if v.type == 'readfrom':
                    # rowx
                    v = v.object
                    if v.startswith('row'):
                        i = int(v.replace('row',''))-1 # zero based correction
                        try:
                            desc = data[i][0]
                            del data[i]
                        except:
                            desc = f'cannot extract description from {v}'
                elif v.type == 'str':
                    desc = str(v)
                actions['description'] = desc
            self.rows = len(data)
            self.cols = max([ len(r) for r in data ])

            # refill if there is any row shorter than max (it used to append
            # a single '' however short the row was, which left cells beyond
            # it unwritten -- and template sample text showing through)
            for r in data:
                if len(r) < self.cols:
                    r += [''] * (self.cols - len(r))

            fformat = (f"{{:{obj.floatformat}}}").format
            newdata = []
            for r in data:
                row = []
                for v in r:
                    if v == '':
                        # an empty cell reads as a blank so the fill really
                        # overwrites the template's cell
                        v = ' '
                    else:
                        try:
                            v = int(v)
                        except:
                            try:
                                v = fformat(float(v))
                            except:
                                pass
                    row += [v]
                newdata += [row]
            self.data = newdata
            if desc:
                self.caption = desc
            
