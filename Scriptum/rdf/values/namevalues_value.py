#!/usr/bin/env python3
#
# part of:
#   S C R I P T U M 
#

from datetime import datetime

class NameValue:
    """from task.value to content used in elements etc.

    take a task to extract content and hold it

    written in the document as
    - position: {parfile: somefile.nv, parameter: parameter to look for}
    file somefile.nv
    parameter to look for:value

    we are interested in the "value" to be extracted and used at position
    """
    def __init__(self, filename, exists, settings, parname):
        self.subtype = 'parameterfile'
        self.filename = filename
        self.exists = exists
        self.parameter = str(parname)
        self.separator = settings.nvseparator
        self.datetimeformat = settings.datetimeformat
        self.floatformat = settings.floatformat
        self._parsed = False
           
    @property
    def content(self):
        if not self._parsed:
            self._raw_content = NameValueReader(self)
            self._parsed = True
        #print(self.parameter, str(self._raw_content))
        return self._raw_content.parsed.get(
            self.parameter.lower().replace(' ', ''),
            f'Not found: {self.parameter!r}'
        )

    def __repr__(self) -> str:
        if self.parameter:
            return (
                f"{self.filename!r} exists: {self.exists} ({self.subtype}) - "
                f'parameter to look for: {self.parameter!r}'
            )

    def __str__(self):
        # return the requested parameter
        try:
            return str(self.content)
        except:
            return f'no parameter requested from {self.filename!r}'

    # def getValue(self, name):
    #     if self.content:
    #         return self.content[name]
    #     else:
    #         return 'not parsed: %r'%self.filename

class NameValueReader:
    """store and handle full file content
    usually not used directly but in tests
    
    class to manage files with name:value content"""
    def __init__(self, nvobject):
        self.filename = nvobject.filename
        self.timeformat = nvobject.datetimeformat
        
        if nvobject.exists:
            self.exists = True
            self.raw_content = _readRawNVfile(self.filename, nvobject.separator)
            self.names = dict([ (name.replace(' ','').lower(), name) for name, value in self.raw_content ])
            self.unparsed = dict([ (name.replace(' ','').lower(), value) for name, value in self.raw_content ])
            self.parsed = {}
            self.full_to_parsed = dict([ (k,k) for k in self.unparsed.keys() ])
            
            self.parseCommon()
            
            self.parseTimes()
                
            self.parseJobDiagnostics()

            self.parseRest()
        else:
            self.exists = False


    def parseTimes(self):
        del_keys = []
        for key, value in self.unparsed.items():
            tv = strToTime(value)
            if tv:
                self.parsed[key] = tv.strftime(self.timeformat)
                del_keys += [key]
        for key in del_keys:
            del self.unparsed[key]
    
    def parseCommon(self):
        """parse common identifiers"""
        ids = ['title','name','createdfrom','revision','description']
        del_keys = []
        for key, value in self.unparsed.items():
            for element in ids:
                if key.startswith(element) or key.endswith(element):
                    self.parsed[key] = value
                    del_keys += [key]
        for key in del_keys:
            del self.unparsed[key]
            
    def parseJobDiagnostics(self):
        """parse special identifiers
        maybe user removed 'jobdiagnosticssummary'?
        however: we remove it here"""
        del_keys = []
        for key, value in self.unparsed.items():
            nkey = key.replace('_jobdiagnosticsummary_1','')
            if key.startswith('numberof'):
                self.parsed[nkey] = int(value)
                self.full_to_parsed[key] = nkey
                del_keys += [key]
            elif key.startswith('wallclocktime'):
                self.parsed[nkey] = float(value)
                self.full_to_parsed[key] = nkey
                del_keys += [key]

        for key in del_keys:
            del self.unparsed[key]
    
    def parseRest(self):
        """parse all remaining and do what you can"""
        del_keys = []
        for key, value in self.unparsed.items():
            try:
                value = int(value)
            except:
                try:
                    value = float(value)
                except:
                    if v := strToTime(value):
                        value = v.strftime(self.timeformat)
                    else:
                        pass
            self.parsed[key] = value
            self.full_to_parsed[key] = key
            del_keys += [key]

        for key in del_keys:
            del self.unparsed[key] 

    def __getitem__(self,key):
        
        if not self.exists:
            return f'file does not exist {self.filename!r}'
        else:
            lkey = key.replace(' ','').lower()
            try:
                nkey = self.full_to_parsed[lkey]
                return self.parsed[nkey]
            except:
                try:
                    return self.parsed[lkey]
                except:
                    try:
                        return self.unparsed[lkey]
                    except:
                        # always return something meaningful, exceptions are hard to catch in a process
                        return f'KeyError in file {self.filename!r} - {key}'
    
    def bracket(self,condensed=True, all=True):
        """put everything in brackets, keep condensed/lowered keys
        this makes sense only in case that parameter names and ppt-template match 1:1
        which isn't the case"""
        
        result = {}
        for key, value in self.parsed.items():
            if not condensed:
                key = self.names[key]
            result[f'<{key}>'] = value
        if all: # add the rest as well
            for key, value in self.unparsed.items():
                if not condensed:
                    key = self.names[key]
                result[f'<{key}>'] = value
        return result
    
    def translate(self,how={}):
        """translate parsed parameters with the dictionary 'how'"""
        result = {}
        # do that for all and for the condensed names only
        for key, nkey in how.items():
            value = self.parsed.get(key,self.unparsed.get(key,None))
            if value:
                result[nkey] = value
        return result      

    def __str__(self):
        r = []
        for n,v in self.parsed.items():
            r += [f" {n} = {v} {type(v)}"]
        return '\n'.join(r)      

def _readRawNVfile(filename, separator=':',ticks="'"):
    """read and 'normalize' content, the file parser adapter is a...
    no empty lines or comments but in multiline strings!
    #par:1 

    other:2
    #foo:'bar'

    @TODO: how to handle this case:
    str2[0]=hallo
    str2[1]=welt
    str1=hallo
    Int2[0]=1
    Int2[1]=5
    Int1=42
    Real2[0]=1.0
    Real2[1]=43.2
    Real2[2]=42.0
    Real2[3]=-5.7
    Real2[4]=4.1
    real1=0.0
    multi[0,0]=1.0
    multi[0,1]=4.4
    multi[0,2]=4.0
    multi[1,0]=1.9
    multi[1,1]=2.0
    multi[1,2]=2.2
    """
    lines = open(filename,'r').readlines()
    newlines = []
    openline = False
    assembledvalue = '' 
    for line in lines:
        line = line.rstrip('\n')
        #print(openline, separator in line)        
        if not openline and separator in line:
            # start of a value or...
            if line.startswith('#') or '[' in line or not line.strip():
                # ignore for now comment lines and array values
                continue
            k,v = line.split(separator,1)
            if v.count(ticks) == 0 or (v.startswith(ticks) and v.endswith(ticks)):
                # normal string behavior or in any other case (hopefully)
                newlines.append((k,v))
            else: # v.count(ticks) == 1:
                openline = True
                assembledvalue = v
        elif openline:
            if line.endswith(ticks):
                assembledvalue += '\n'+line
                newlines.append((k,assembledvalue[1:-1]))
                assembledvalue = ''
                openline = False
            else:
                assembledvalue += '\n'+line
    
    if not newlines:
        print(f"{filename} is empty or does not contain separator '{separator}'")
    return newlines

def strToTime(timestamp):
    """Try to convert ``timestamp`` to a :class:`datetime.datetime`.
    
    tries to extract a datetime from 1566995546000 or 1566995546 values"""

    multipliers = {9: 1, 10: 1, 13: 1 / 1000}

    if timestamp is None:
        return None

    timestamp = str(timestamp).strip()
    mul = multipliers.get(len(timestamp))
    if mul is None:
        return None

    try:
        ts = int(timestamp) * mul
        return datetime.fromtimestamp(ts)
    except (TypeError, ValueError, OverflowError):
        return None
