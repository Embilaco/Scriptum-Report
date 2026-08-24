#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M 
#

from .section import Section
from ...tag.tag import puretagOf

class Sections:
    """contains only sections as structured elements"""
    def __init__(self, sections):
        """will create the root elements of all and parse them
        sections are always the container everything is in"""
        
        self._sections = [ Section(s) for s in sections ]
        self._fillTemplates()

    def __iter__(self):
        """iterate content"""
        yield from iter(self._sections) # which is a list

    def byName(self, name):
        """Find a section by name, given a canonical address or a bare name.

        A task carries ``section:title::1``; a caller may still pass
        ``section:title`` or ``title``. The name is the second slot when there
        is a namespace and the first when there is not -- sections are never
        cloned, so the instance is always 1 and is simply not looked at.
        """
        parts = str(name).split(':')
        wanted = parts[1] if len(parts) >= 2 else parts[0]
        for s in self:
            if s.name == wanted:
                return s
    
    def findGlobal(self, what: str) -> list:
        """find in all sections
        * what is a string"""

        result = []
        # this is brute force we simply walk over everything but template section
        for sec in self:
            if sec.name == 'template': continue
            result += sec.findGlobal(what)
        
        return result

    def _fillTemplates(self):
        """generate all templates"""
        result = []
        for sec in self._sections:
            result += sec.getTemplates()

        self.templates = result
    
    def findTemplate(self, name):
        """Find one template by path (a list) or by bare name (a string).

        A bare name -- what an ``add`` at a marker carries -- matches any
        block flagged ``template``, wherever it stands: the templates list
        has always held the whole document (the template section plus every
        flagged block), only this lookup was restricted to
        ``section:template``. The template section still wins when the same
        name exists there and elsewhere -- it holds the general templates --
        and any further ambiguity is warned about, names being documented as
        unique within a document. Decided on the DOCX board: *Can a block
        flagged `template` outside section:template be added at a marker?*

        Matched by the name a document writes, never by an instance: there is
        one blueprint however many copies are made of it, and the tree's
        paths carry instance numbers now.
        """
        if type(name) == str:
            wanted = puretagOf(name)
            # e.path can be empty: the template section's own opening
            # paragraph rides along in the list.
            hits = [e for t, e in self.templates
                    if e.path and puretagOf(e.path[-1]) == wanted]
            hits.sort(key=lambda e: puretagOf(e.path[0]) != 'section:template')
            if len(hits) > 1:
                print(f'WARNING: template {name!r} is ambiguous: '
                      f'{[".".join(e.path) for e in hits]} - taking the first')
            if hits:
                return hits[0]
            print(f'WARNING: No such template in document: {name!r}')
            return None
        wanted = [puretagOf(part) for part in name]
        for t,e in self.templates:
            if wanted == [puretagOf(part) for part in e.path]:
                return e
        print(f'WARNING: No such template in document: {name}')
    
    def delete(self, sectionname):
        s = self.byName(sectionname)
        s.delete()

