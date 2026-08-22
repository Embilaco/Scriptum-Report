#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M 
#

###################
# MODULE .tag.tag - everything to manage Tags <foo>, </foo>, <foo/>
# PROVIDES 
#   class Tag - handle <...> tags inside the document template
#   function getTag
#

import re

# how tags look like
OPENING='</?'
CLOSING='/?>'

# what is allowed
# we don't care about the case, but always start with a letter
# in contrast to XML standards parameters are NOT enclosed in '' or "" since word tends to use other characters for these enclosings
GENERIC_PATTERN='[a-z]+[a-z0-9_\\- :;,=]*'
RECOMPILEFLAGS=re.IGNORECASE|re.UNICODE
# and what not
NOT_ALLOWED_IN_ARGS = ':' # not allowed in further args
NOT_ALLOWED_IN_TAG = '\\'
#

class Tag:
    def __init__(self,rawtag):
        self.rawtag = rawtag # as given in document, mostly for printing, or replication
        self.burned = False # when True it will not be used furthermore
        self.tagtype = '' # open, close, simple, invalid...
        self.puretag = '' # the pure and clean tag, lowercase, e.g. section:foo, whatever:name, etc.
        self.args = []
        self.ns = None
        self.name = None
        self.child = None
        #self.iwasadded = False
        #self.inElement = -1 # yet not really used
        # further split content
        innertext = rawtag[1:-1]
        if innertext.startswith('/') and innertext.endswith('/'):
            self.tagtype = 'invalid'
        elif innertext.startswith('/'):
            self.tagtype = 'close'
            innertext = innertext[1:]
        elif innertext.endswith('/'):
            self.tagtype = 'simple'
            innertext = innertext[:-1]
        else:
            if innertext.strip() == '':
                self.tagtype = 'invalid:empty'
            else:
                self.tagtype = 'open'
        
        # this is what we finally search while replacing the full tag
        self.tagtext = innertext
        
        if 'invalid' not in self.tagtype:
            tagcontent = innertext.split()
            # this is the "address" to find a tag in the document
            self.puretag = tagcontent[0].lower()
            # the first part can be split by : or not
            ns_name = self.puretag.split(':')
            if len(ns_name) == 1:
                self.ns = ns_name[0]
                self.name = ns_name[0]
            elif len(ns_name) == 2:
                self.ns, self.name = ns_name
            elif len(ns_name) == 3:
                self.ns, self.name, self.child = ns_name
            else:
                # This branch was written with '==' instead of '=', which made
                # it a no-op: a tag with four or more colon-separated segments
                # was accepted as a valid 'simple' tag, with ns, name and child
                # all left as None, and then quietly matched nothing instead of
                # being reported. The address grammar has three segments at
                # most, so anything longer is an error and has to say so.
                self.tagtype = 'invalid:ns_name'
            
            args = {}
            if [ c for c in NOT_ALLOWED_IN_ARGS if c in ''.join(tagcontent[1:]) ]:
                self.tagtype = 'invalid:not_allowed'
            else:
                for t in tagcontent[1:]:
                    t = t.split('=')
                    if len(t) == 1:
                        args[t[0].lower()] = None
                    elif len(t) == 2:
                        args[t[0].lower()] = t[1]
                    else:
                        self.tagtype = 'invalid:args_wrong'
            if 'invalid' not in self.tagtype:
                self.args = args

        if 'invalid' in self.tagtype:
            self.puretag = ''

    @property
    def instance(self):
        """Which instance of its template this tag is. Defaults to 1.

        The instance rides as an argument -- ``<head id=2/>`` -- rather than in
        the name. A tag with no ``id`` is instance 1, which is what lets a
        pristine template be read without editing it: every block in one is the
        first of its kind.

        Readability is the reason it is an argument. Opening a generated
        document and finding ``<head id=2/>`` says what it is; ``<head_c002/>``
        says only that something renamed it. It also repairs a real
        inconsistency: ``global`` matches on ``puretag``, so renaming a clone
        made every clone invisible to it, while an argument leaves the puretag
        alone.

        A non-integer id reads as 1 rather than raising. This is a document
        somebody typed into Word, and a mistyped number should not stop the run
        before the diagnostics that would explain it.
        """
        try:
            return int(self.args.get('id', 1))
        except (TypeError, ValueError):
            return 1

    @property
    def canonical(self):
        """This tag's four-slot address: ``namespace:name:child:id``.

        A single-segment tag leaves the **namespace** slot empty -- ``<head/>``
        is ``:head::1``, not ``head:head::1``. The tag sets namespace and name
        to the same word, which duplicates the value and makes "is there a
        namespace?" unanswerable; the slots keep them apart.
        """
        parts = self.puretag.split(':') if self.puretag else ['']
        namespace, name, child = '', parts[0], ''
        if len(parts) == 2:
            namespace, name = parts
        elif len(parts) > 2:
            namespace, name, child = parts[0], parts[1], parts[2]
        return f'{namespace}:{name}:{child}:{self.instance}'

    def withInstance(self, number):
        """This tag's text, numbered -- **without** changing this tag.

        A caller replacing the tag in a document has to match on the text that
        is still there, so the new text is computed first and applied after.
        """
        head, _, rest = self.tagtext.partition(' ')
        keep = [part for part in rest.split()
                if not part.lower().startswith('id=')]
        return ' '.join([head] + keep + [f'id={number}'])

    def setInstance(self, number):
        """Number this tag, in place, by writing an ``id`` argument.

        What a clone does instead of being renamed, so ``puretag`` is untouched
        and the tag stays readable. Returns the new tag text.
        """
        self.args = dict(self.args)
        self.args['id'] = str(number)
        self.tagtext = self.withInstance(number)
        return self.tagtext

    def getLength(self, name, units):
        """try to extract an arg with name name 
        usually name='width' or 'height' but can be 'top', 'left' and so on
        
        but always need to return a length value or None
        
        yet only used in images, but ..."""
        if name in self.args:
            l = self.args[name].lower()
            unit = l[-2:]
            if unit in ['mm', 'cm', 'in', 'pt']:
                vi = -2
            elif l.endswith('inch'):
                unit = 'in'
                vi = -4
            else:
                return None
            try:
                value = float(l[:vi])
                return units[unit](value)
            except:
                return None
        else:
            return None

    def getFloat(self, name):
        """try to extract name as a float
        usually used in 'scale=50%', 'scale=0.5' and so on"""
        if name in self.args:
            l = self.args[name]
            if l.endswith('%'):
                l = l[:-1]
                d = 100
            else:
                d = 1
            try:
                value = float(l)/d
                return value
            except:
                return None
        else:
            return None

    def burn(self):
        """burn this tag"""
        self.burned = True

    def rewriteTag(self,puretag):
        """rewrite that tag for copies..."""

        puretag = puretag.lower()
        # invalid tags shouldn't appear at any time?

        # keep
        # self.rawtag even if different
        # self.burned
        # self.tagtype
        # self.args = []
        
        # keep but check
        # self.ns 

        # change
        # self.name 
        # self.puretag 
        # this is what we finally search while replacing the full tag
        # self.tagtext

        error = []

        if 'invalid' in self.tagtype:
            error += [
                f'cannot rewrite tag, old tag was invalid: {self.ns}:{self.name}'
            ]

        ns_name = puretag.split(':')
        if len(ns_name) == 1:
            ns = ns_name[0]
            name = ns_name[0]
        elif len(ns_name) == 2:
            ns, name = ns_name
        else:
            error += [
                f'cannot rewrite tag, new tag will be invalid: {self.ns}:{self.name} --> {puretag}'
            ]

        if ns != self.ns:
            error += [
                f'cannot rewrite tag with new namespace: {self.ns} --> {puretag}'
            ]

        if not error:
            self.name = name
            self.tagtext = puretag
            self.puretag = puretag

    @property
    def printable(self, newline="\n     "):
        """return the printable tag, not using the common __str__ or __repr__"""
        _printable = [
                     f'Tag: {self.rawtag}',
                     f'tagtype: {self.tagtype}',
                     f'namespace: {self.ns}',
                     f'name: {self.name}',
                     f'args: {self.args}',
                     f'burned: {self.burned}',
                     f'puretag: {self.puretag}',
                     #': %s'%self.,
                     ]

        return newline.join(_printable)

def getTag(text):
    """simple tags are always in xml syntax as closed elements defined, that means:
    a tag <foo/> is valid while a tag <foo> is only valid with a closing </foo>
    
    for further reading start at: https://www.w3schools.com/XML/xml_syntax.asp
    
    Thus pattern is only the inner part of the tag 'x foo=123' formulated as regular expression
    """
    
    # denied = [ c for c in _NOT_ALLOWED+opening+closing if c in innertext ]
    # if denied:
        # #print(text,innertext,'denied')   
        # return None, denied, 1
    # # complete the pattern
    pattern = OPENING + GENERIC_PATTERN + CLOSING
    
    tag = re.compile(pattern,flags=RECOMPILEFLAGS)
    found = tag.findall(text)
    #print(found)
    tags = []
    for f in found:
        tags += [Tag(f)]    
    return tags

def getReTag(tag: Tag):
    pattern = OPENING+tag.tagtext+CLOSING
    return re.compile(pattern,flags=RECOMPILEFLAGS)

def puretagOf(address: str) -> str:
    """The tag as a template spells it, from a four-slot canonical address.

    ``subsection:instruction::2`` is written ``<subsection:instruction>`` and
    ``:head::1`` is written ``<head/>`` -- an empty namespace slot means the
    name stands alone. Anything that is not four slots comes back unchanged, so
    a caller may pass either form.

    A template is looked up by the name a document writes, never by an
    instance: there is one blueprint however many copies are made of it.
    """
    parts = address.split(':')
    if len(parts) != 4:
        return address
    namespace, name, child, _instance = parts
    if not namespace:
        return name
    return f'{namespace}:{name}:{child}' if child else f'{namespace}:{name}'


def createTag(tagtext:str):
    return Tag("<"+tagtext+"/>")