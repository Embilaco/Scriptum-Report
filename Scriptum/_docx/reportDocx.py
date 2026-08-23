#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M 
#

###################
# MODULE _docx.reportDocx
# PROVIDES 
#   class ManagedDocx - manage a full word docx-file and combines all other modules in the package
#                       main entry for word-documents

#

from docx import Document
from docx.oxml.ns import qn
from .section import Sections
from ..rdf.namespaces import docx_sections
from ..rdf.tasks.report_task import GLOBAL_ROOT, ReportTask
from ..tag import Tag

import os
if os.name == 'nt':
    import win32com.client

from .. import version

class ManagedDocx:
    def __init__(self, document: str, debug=False):
        self.document_name = document
        # open and store the Document as given by docx:
        self.document = Document(document)
        self._debug=debug
        
        ## evaluate structure of document and store it
        #self.elements = []

        # in that simple command all work is done to read and organize the document!
        self.sections = Sections(self.document.sections)
        # at least there is always one section

        # collect all errors and warnings
        errors = []
        warnings = []
        for s in self.sections:
            errors += s.error
            warnings += s.warning

        # expose collected diagnostics so callers can inspect them without
        # parsing stdout
        self.errors = errors
        self.warnings = warnings

        if warnings:
            print('There are warnings in the template, outcome might be not as expected:')
            print('  '+'\n  '.join(warnings))

        if errors:
            print('There are errors in the template, further action is needed:')
            print('  '+'\n  '.join(errors))
            print('Please fix prior to proceeding with that template')
            print('PROCESSING STOPPED')
        else:
            # get usable templates
            self.templates = self.sections.templates

            self.toc = self.findTableOfContents()
         
    def apply(self, what, task:ReportTask) -> None:
        """change the tag given as list == path or as string == tag
        
        within this step we do fill and replace content
        """

        #print('\nstart to apply:', what, task)

        if type(what) == str:
            # this may return many nad is used in global search only!
            found = self.sections.findGlobal(what)
        else:
            # this will return one and is used in each single task
            root = self.sections.byName(what[0])
            if not root:
                print(f'WARNING: cannot find section {what[0]!r}')
                return
            parent = root.addressbook.get('.'.join(what[:-1]),None)
            if parent:
                found = parent.findExact(what)
                #print('F',found)
            else:
                print(f'WARNING: cannot find parent structure {(".".join(what[:-1]))}')
                return

        #print('found for apply ...', found)
        value = task.value

        # do something special for tables and images when they are standalone
        if value.subtype in [ 'table', 'image' ]:
            # DocImageBlockElement or DocTableBlockElement
            for t,e in found:
                e.fill(task)

        else:
            # do something general for paragraphs (even in tables) when there are tags
            # in case of non-existing files above, write a message if possible
            # otherwise find inline tables, images, images in inline tables etc. as well
            for t,e in found:
                if hasattr(e, 'subtype') and e.subtype == 'text':
                    # DocTextBlockElement
                    e.fill(task)
                elif type(t) == str:
                    print(f'ERROR: FIX - no fill on {t} {e}')
                    continue
                elif not t or t.burned: 
                    continue
                else:
                    # The tag as the document spells it, not the canonical
                    # address: findExact has already picked out this exact
                    # tag, and the text to match on is what is written
                    # there. The instance rides as an `id` argument now,
                    # so a clone's tag still reads `text:description`.
                    self.fillGeneric(t.puretag,t,e,value)

    def fillGeneric(self, target: str, tag: Tag, elem, value):
        """always do that loop for paragraph type elements and text value types"""
        #obj = determineElement(elem)
        value.load()
        #print('fillGeneric 1a:',elem,target,tag.puretag,value)
        found = elem.replaceTagInAll(target, str(value))
        #print('fillGeneric 1b:',found, elem, value.tostring)
        if found and not value.tostring:
            if value.type == 'file' and tag.tagtype in ['open','simple']:
                #print('fillGeneric 2: sub',value.object.subtype)
                if not value.object.exists:
                    found.text = f'file {value.object.filename!r} not found'
                elif value.subtype == 'text':
                    found.text = value.object.content
                elif value.subtype == 'video':
                    found.text = f'{value.object.filename!r}: videos cannot be added to a word document'
                elif value.subtype == 'unclear':
                    found.text = f'{value.object.filename!r}: unclear what to do'
                elif value.subtype == 'image':
                    # images already done before
                    pass
                elif value.subtype == 'table':
                    # never happens since we require an open/close tag around
                    pass 

            elif value.type == 'parfile':
                if not value.object.exists:
                    found.text = f'file {value.object.filename!r} not found'
                else:
                    nv = value.load()
                    found.text = str(nv)

    def typesetting(self, rdf, 
                    addcopy=True, 
                    directfill=True,
                    globalfill=True,
                    cleanup=True,
                    removetemplate=True,
                    cleardust=True,
                    setproperties=True
                    ):
        """the final marriage between document and rdf and content
        
        usually all options are True, setting them to False will skip the step during typesetting
        however, this may cause some unintendent results, so use it with care and for debugging only

        * addcopy - apply all add and copy operations
        * directfill - fill all content that is directly addressed
        * globalfill - fill all global addressed content
        * cleanup - run cleanup - remove all remaining xml-syntax from document
        * removetemplate - remove the template section
        * cleardust - remove paragraphs initially marked for deletion
        * setproperties - set document properties
        """
        print('check consistency')

        # Blueprints that were cloned in place of being filled. They leave the
        # tree when their first instance is cloned, so the pruning pass at the
        # end cannot find them by walking it; they are remembered here instead.
        spentBlueprints = []

        if not addcopy:
            print('   SKIP: add and copy new paragraphs and more ...')
        else:
            print('   add and copy new paragraphs and more ...')

            #lasttask = None
            for t in rdf.tasks:
                # 'global' is the text parser's spelling, GLOBAL_ROOT the loader's:
                # both are still live until the text parser is retired, so a
                # global task must be recognised under either name.
                if t.path[0] in ('global', GLOBAL_ROOT): continue # apply the global tasks at the end
                if t.modified: # the modification tells me if I have to add or copy templates
                    #print('\nto %s  *******************\n'%t.what, 
                    #      f'{t.path} - {t.myAddress} - {t.where}')

                    root = self.sections.byName(t.myAddress[0])

                    if not root:
                        print(f'ERROR: cannot find section: {t.myAddress[0]}')
                        continue

                    if t.what == 'apply':
                        if len(t.myAddress) == 1:
                            # A top-level section. There is no parent to
                            # claim a subAnchor from, and the section is
                            # already in the document, so this is a no-op.
                            continue
                        # 'apply' is used on structures and sections that already exist in the document
                        #
                        # will just fill the already existing content later
                        # but we will remove any subAnchor from parent if it exists
                        # this happens always befor we do 'copy' a new section below!
                        parent = root.addressbook.get('.'.join(t.myAddress[:-1]),None)
                        if not parent:
                            print(f'WARNING: No such parent structure: '
                                  f'{(".".join(t.myAddress[:-1]))}')
                            continue

                        struct = parent.findExact(t.myAddress)
                        if not struct:
                            print(f'WARNING: Nothing to apply at '
                                  f'{(".".join(t.myAddress))}')
                            continue

                        element = struct[0][1]
                        firstElement = element.structure[0][1]

                        if element.isTemplate:
                            # A block whose tag says `template` is a blueprint,
                            # and every instance of it is a clone -- the first
                            # included. The clone goes exactly where the
                            # blueprint stands (before its opening paragraph),
                            # which keeps document order whatever order the
                            # data names things in; the blueprint itself is
                            # pruned at the end. Word now agrees with
                            # PowerPoint, which always copies.
                            #
                            # The blueprint leaves the parent's structure
                            # first: findExact takes the first match, and the
                            # fills to come must reach the clone, not a block
                            # that is about to be deleted. A blueprint nested
                            # inside a clone was never through getTemplates(),
                            # so it gets its deepcopy here.
                            if not hasattr(element, 'deepcopy'):
                                element.createTemplate()
                            parent.structure = [(pt, pe) for pt, pe in parent.structure
                                                if pe is not element]
                            spentBlueprints.append(element)
                            element.copy(firstElement, parent=parent,
                                         newpath=t.myAddress[:-1],
                                         newname=t.myAddress[-1], section=root)

                        # Claims this child *and everything ahead of it*, so a
                        # later clone cannot be inserted upstream of the block
                        # it follows -- see StructuredElement.claimSubAnchor.
                        parent.claimSubAnchor(firstElement)

                        continue

                    if t.what == 'add':
                        # 'add' is used when we add by '+' new content from templates after an @anchor
                        parent = root.addressbook.get('.'.join(t.myAddress[:-1]),None)
                        if not parent:
                            print(
                                f'WARNING: No such parent structure: {(".".join(t.myAddress[:-1]))}'
                            )
                            continue
                        where = parent.findExact(t.myAddress[:-1]+[t.where])
                        if not where:
                            print(
                                f'WARNING: No place to add found: {t.myAddress} {t.where} {where}'
                            )
                            continue
                        
                        anchor = where[0][1]
                        tpl = self.sections.findTemplate(t.target)
                        #print('   add tpl and anchor 0', t.myAddress, where, anchor, tpl)
                        
                        if tpl:
                            #print('   add tpl and anchor 1', parent)
                            newElement = tpl.copy(anchor, parent=parent, newpath=t.myAddress[:-1], newname=t.myAddress[-1], section=root)
                            

                    elif t.what == 'copy':
                        # 'copy' is used in any case we need to duplicate e.g. a section while the existing one is already in place
                        #print('addressbook is:')
                        #for k,v in root.addressbook.items():
                        #    print(' k,v',k,v)
                        #print('looking for',t.myAddress)
                        parent = root.addressbook.get('.'.join(t.myAddress[:-1]), None)
                        #print('parent is', parent)
                        if not parent or not parent.anchor:
                            print(f'WARNING: No place to copy found: {(".".join(t.myAddress[:-1]))}')
                            continue
                        
                        tpl = self.sections.findTemplate(t.path)

                        if parent.subAnchors:
                            #print('subAnchors')
                            #for a in parent.subAnchors:
                            #    print('   ',a.thing.text)
                            anchor = parent.subAnchors[0]
                        else:
                            #print('anc',parent.anchor)
                            anchor = parent.anchor

                        if tpl:
                            newElements = tpl.copy(anchor, parent=parent, newpath=t.myAddress[:-1], newname=t.myAddress[-1], section=root)

        if not directfill:                
            print('   SKIP: fill the content...')
        else:
            print('   fill the content...')
            for t in rdf.tasks:
                # both spellings, see above
                if t.path[0] in ('global', GLOBAL_ROOT): continue # apply the global tasks at the end
                #print('\n',t.isCopy, t.path,t.myAddress,t.target,t.value)
                if t.target:
                    # apply it on path, means: apply it on exact this item
                    #print('  apply to', t.myAddress, t.target, 'v',t.value.object, 'v')
                    self.apply(t.myAddress,t)

        if not globalfill:                
            print('   SKIP: fill the global content...')
        else:
            print('   fill the global content...')
            # apply the global tasks
            for t in rdf.tasks:
                # both spellings, see above
                if t.path[0] in ('global', GLOBAL_ROOT) and t.target:
                    self.apply(t.target,t)

        if not cleanup:                
            print('   SKIP: clean up...')
        else:
            print('   clean up...')
            # finally remove all tags which are not yet "burned"
            for sec in self.sections:
                for t,e in sec:
                    #print('clean1', sec, t)
                    if t in ['text','image','table','struct']:
                        e.clean()
                        continue
                    if not t or t.burned: continue
                    e.replaceTagInAll(t.puretag,'')
                    t.burn()

            # for t,e in self.sections.copies:
            #     if not t or e.anchor or t.burned: continue
            #     #obj = determineElement(e)
            #     e.replaceTagInAll(t.puretag,'')
            #     t.burn()

        if not removetemplate:
            print('   SKIP: remove template section and blueprints...')
        else:
            print('   remove template section and blueprints...')
            self.sections.delete('template')
            self.pruneBlueprints(spentBlueprints)

        if not cleardust:                
            print('   SKIP: clearing all the dust...')
        else:
            print('   clearing all the dust...')

            for sec in self.sections:
                for e in sec.markedForDeletion:
                    #print('md',e)
                    e.deleteIfEmpty()

        #self.cleanTableOfContent()

        if not setproperties:                
            print('   SKIP: set properties...')
        else:
            print('   set properties...')

            documenttitle = rdf.settings.documenttitle
            self.document.core_properties.author = f'Scriptum {version}'
            self.document.core_properties.title = documenttitle

        print('done')

    def pruneBlueprints(self, spent):
        """Remove every blueprint from the document, used or not.

        A blueprint is a section-ladder block whose tag says ``template``. It
        is never content: its instances are clones, and once they are placed
        the blueprint has nothing left to do -- and an unused one would stay
        in the finished document otherwise, tags cleaned and text intact,
        which is what used to happen.

        Two kinds have to be found two ways. A blueprint that was cloned left
        its parent's structure when that happened, so it is taken from
        ``spent``. One that was never used is still in the tree -- whether it
        came with the template or rides inside a clone, where a nested
        blueprint is copied along with everything else -- so the tree is
        walked for it. Clones themselves do not say ``template`` (numbering
        drops it), so the walk cannot mistake an instance for its blueprint.
        Deleting is a no-op on a detached element, so the overlap between
        the two is harmless, and so is meeting a nested blueprint after its
        parent already went.
        """
        ladder = docx_sections['order']
        found = list(spent)
        for sec in self.sections:
            if sec.name == 'template':
                continue  # went wholesale, just above
            found += [e for e in sec.iterOnStructures()
                      if e.isTemplate and e.type in ladder]
        for e in found:
            e.delete(verbose=False)

    def findTableOfContents(self):
        """find the table of contents, other tables untouched for now"""
        b=self.document._body._body
        if (m := b.find(qn('w:sdt'))) != None:
            #print(m)
            try: 
                n=m.find(qn('w:sdtPr')).find(qn('w:docPartObj')).find(qn('w:docPartGallery')).attrib[qn('w:val')]
                #print('n',n)
            except:
                return None
            if n != 'Table of Contents': return None # check for localization?
            try:
                toc = m.find(qn('w:sdtContent'))
                return toc
            except:
                return None
        return None

    def cleanTableOfContent(self):
        """reduce table of content since it will be updated only manually either way
        
        yet not working, TOC broken afterwards
        """
        
        for i,c in enumerate(self.toc.iterchildren()):
            if i < 2: continue
            c.clear()

    def save(self, filename, finish=False, createpdf=False):
        """do a final cleanup and save the result"""
        
        # save from with python-docx
        if filename == self.document_name:
            print('Sorry, overwriting by same name is yet not allowed!')
            return
        
        self.document.save(filename)
        
        if finish:
            if os.name == 'nt':
                in_file = os.path.abspath(filename)
                out_file = os.path.abspath(os.path.splitext(os.path.basename(filename))[0]+'.pdf')
                wdFormatPDF = 17

                try:
                    try:
                        word = win32com.client.GetActiveObject('Word.Application')
                        doquit = False
                    except:
                        word = win32com.client.Dispatch('Word.Application')
                        doquit = True
                    try:
                        word.Visible = False
                    except:
                        pass
                    doc = word.Documents.Open(in_file)
                    doc.Fields.Update()
                    try:
                        for i in range(1,doc.TablesOfContents.Count+1):
                            #print(i)
                            doc.TablesOfContents(i).Update()
                    except:
                        pass
                    try:
                        for i in range(1,doc.TablesOfFigures.Count+1):
                            #print(i)
                            doc.TablesOfFigures(i).Update()
                    except:
                        pass
                    doc.Save()
                    if createpdf:
                        doc.SaveAs(out_file, FileFormat=wdFormatPDF)
                    doc.Close(SaveChanges=True)
                    if doquit:
                        word.Quit()
                except Exception as e:
                    print(f'failed to update tables and/or save as PDF\nReason:\n{e}')
            else:
                print(f'Running on {os.name} will prevent any finishing work...')

