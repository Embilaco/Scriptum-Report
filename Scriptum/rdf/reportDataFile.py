#
# part of:
#   S C R I P T U M 

#
import os, glob
from pathlib import Path

MIN_REQUIRED_VERSION = 3

#: Extensions read as YAML. The code keeps its names -- this is still the
#: report data file -- but the extension changes, because it is the one name
#: tools read: highlighting, folding and validation all key off it, and for a
#: format whose structure is carried by indentation that is not cosmetic.
YAML_SUFFIXES = ('.yaml', '.yml')

from .namespaces import SECTION_NAMESPACES

from .common import removeQuotes, getCorrectFile, is_test_debug
from .settings import SETTINGS
from .values import Value
from .tasks import LogTask, ReportTask

_test_debug = is_test_debug()

class ReportDataFile:
    _testmode_=False
    _rlimit = 10 # limit the recursion depth
    _depth = 0
    _global_settings = {}
    def __init__(self, filename, debug=False,
                 _root=['___init___'], _mark='', _settings=None,
                 _visited=None):
        """open and read the data and all the subdatas from other files as well
        and create
        - ReportTasks inside self.tasks
        - LogTasks inside self.logs for debugging and other purposes

        A ``.yaml`` document is read by :mod:`Scriptum.rdf.loader` instead; see
        :meth:`_readYaml`. Everything below is the text format, which the YAML
        one supersedes.
        """

        self.errors = []
        self.logs = []
        self.tasks = []
        self.root=None

        # Only a root open can be YAML: the parameters below carry an *rdf*
        # include's inherited context, and a YAML include is spliced by the
        # loader without coming back through here.
        if _root == ['___init___'] and str(filename).lower().endswith(YAML_SUFFIXES):
            self._readYaml(filename, debug)
            return

        if _visited is None:
            _visited = set()
        self._visited = _visited

        filename = os.path.abspath(filename)

        if filename in self._visited:
            self.errors += [f'&include cycle detected: {filename}']
            return

        self._visited.add(filename)

        if not os.path.exists(filename):
            self.errors += [f'Cannot find report data file {filename!r}']
            return 
        
        ReportDataFile._depth += 1
        if ReportDataFile._depth > ReportDataFile._rlimit:
            self.errors += [
                f'Too many recursions: the limit of recursive files is set to {ReportDataFile._rlimit}'
            ]
            return
        
        baseData = open(filename,'r').readlines()
        self.source = filename
        
        ReportTask.set_debug(debug)
        
        self._currentroot = _root
        self._currentmark = _mark
        self.namespace = {'order': [], 'mandatory': True, 'names': {}}

        if not self._testmode_:
            self.logs += [
                LogTask(f'start file {os.path.normpath(self.source)!r}', comment=True)
            ]

        if _root == ['___init___']:
            # the very first open: define settings
            self.settings = SETTINGS()
            self.root = True
            # reset internal
            ReportTask._allPaths = {}
            ReportTask._newPaths = {}
            ReportDataFile._global_settings = {}
        else:
            # afterwards take from previous
            self.settings = SETTINGS(_settings)
            self.root = False
            doctype = self.settings.documenttype
            if doctype in SECTION_NAMESPACES:
                self.namespace = SECTION_NAMESPACES[doctype]

        #print('***********************',filename,self.settings.documenttype)            
        for i, line in enumerate(baseData):
            # go line by line
            # i is used to report line numbers in case or errors
            line=line.strip()
            if not line or line.startswith('#'):
                # skip comments and empty lines, but log as is
                self.logs += [line]
                continue
            
            firstchar = line[0].lower()
            ###################################################################
            # filter general errors and restrictions
            if firstchar in ['+','@','&'] and (not self._currentroot or self._currentroot[0] == 'global'):
                # global section or settings do not allow for the actions below
                self.errors += [
                    f'Marker ({firstchar}) is not allowed see line {i+1} of file {self.source!r}'
                ]
            
            elif firstchar == '+' and not self._currentmark:
                # + is allowed only after @marker
                self.errors += [
                    f'Adding content (+) with tag is not allowed without a marked (@) position; see line {i+1} of file {self.source!r}'
                ]
            
            elif firstchar == '.' and self._currentroot == ['___init___']:
                # this resets currentroot:
                # section:a.target='foo'
                self.errors += [
                    f'Using (.) without a section root is not allowed; see line {i+1} of file {self.source!r}'
                ]
                
            elif firstchar.isalpha() and '=' in line and self._currentroot == ['___init___']:
                # this happens only when first line after global or general is
                # section:a.target='foo'
                # without a 
                # section:a
                # before, which is required to trigger a new slide or group
                self.errors += [
                    f'Using (=) without a section root is not allowed; see line {i+1} of file {self.source!r}'
                ]
                
            elif firstchar.isalpha() and '@' in line:
                # allow only
                # @marker
                self.errors += [
                    f'(@) can be used only as first character of a line; see line {i+1} of file {self.source!r}'
                ]
            elif '+' in line and '@' in line and line.find('@')<line.find('='):
                # + can be used only in subsequent lines not in one
                # however @ can be in the data part
                self.errors += [
                    f'(@) and (+) cannot be used in the same line. Line with (+) has to follow line (@); see line {i+1} of file {self.source!r}'
                ]
            elif '&' in line and '@' in line:
                # & can be used only in subsequent lines not in one
                self.errors += [
                    f'(@) and (&) cannot be used in the same line. Line with (&) has to follow line (@); see line {i+1} of file {self.source!r}'
                ]

            ###################################################################
            # MAIN DATA SCAN
            elif firstchar.isalpha() or firstchar in '.@+&*':
                task, log, error = self.extractWork(firstchar, line, i)
                self.tasks += task
                self.logs += log
                self.errors += error
                
            else:
                self.errors += [
                    f'Error parsing line {i+1} of file {self.source!r}, first letter must be in "a-z.@+&*"'
                ]

        if self.settings.version < MIN_REQUIRED_VERSION:
            self.errors += [
                f'rdf version (*version) lower than {MIN_REQUIRED_VERSION} or not set'
            ]

        if not self.settings.documenttype:
            self.errors += ['*documenttype not set or invalid']

        if self.root and self.errors:
            # we cannot work with invalid rdf-files
            raise Exception('\n'.join(self.errors))
            
        if not self._testmode_:
            self.logs += [
                LogTask(f'end file {os.path.normpath(self.source)!r}', comment=True)
            ]
        #print(self.logs[-3:])
        
    def _readYaml(self, filename, debug):
        """Read a YAML report document through :mod:`Scriptum.rdf.loader`.

        The public surface a back end uses is ``tasks``, ``settings`` and
        ``errors``, and all three are filled the same way they are for a
        ``.rdf``. What is *not* filled is ``logs``: it mirrors an assembled
        text file line by line, and a YAML document has no such assembly --
        an include is spliced into a tree rather than pasted into a stream.

        ``errors`` is populated *and* the exception re-raised, so a caller can
        read the whole set either way. It carries every diagnostic rather than
        the first, which is the same all-or-nothing rule the text reader has at
        the root.
        """
        from .loader import DocumentError, load

        self.source = os.path.abspath(filename)
        self.root = True
        ReportTask.set_debug(debug)

        # The same process-global reset a root open does below. One root
        # document per interpreter is the standing rule either way.
        ReportTask._allPaths = {}
        ReportTask._newPaths = {}
        ReportDataFile._global_settings = {}

        try:
            document = load(filename)
        except DocumentError as error:
            self.errors = [str(entry) for entry in error.diagnostics]
            raise

        self.tasks = document.tasks
        self.settings = document.settings

    def extractWork(self, firstchar, line, i):
        tasks = []
        logs = []
        errors = []

        # "key=value" is supported
        # "key = value" may or may not work

        ###################################################################
        # (a-z) starts a new section or is a complete section and a task in one line
        if firstchar.isalpha():
            # reset currentmark
            self._currentmark = ''
            # proceed
            if '=' in line:
                # if full line is used
                # section:a.subsetion:b.target='Hello world!'
                # but avoid situations that mix roots like
                # section:a
                # section:b.value=1 <--- not allowed to switch root in-between
                # .other=2
                if not line.startswith('.'.join(self._currentroot)):
                    errors += [
                        f'mixing roots see line {i+1}, file: {self.source!r}:\n   {line}'
                    ]
                else:
                    if '+' in line:
                        tasks += self.taskSplitter(root='', line=line)
                    else:
                        tasks += [ReportTask(line=line, settings=self.settings)]
            elif line.lower() == 'global':
                self.updateRoot(i, line)
            else:
                # in case it stands alone it is a topic that starts a possible copy operation
                # so everything from here up to the last before the next copy can be copied
                # this copy operation is most likely only valid for word documents since
                # in powerpoint there is already some logic to copy by using master template slides
                # so copy is what later becomes a duplicated section in docx
                # for pptx it will be used to just create a new slide
                
                self.updateRoot(i, line)
                if self.settings.documenttype == 'pptx':
                    tasks += [ReportTask(root=self._currentroot, line='=newsection:', what='copy')]
                else:
                    # we never copy the sections
                    if len(self._currentroot) == 1:
                        pass
                    else:
                        tasks += [ReportTask(root=self._currentroot, line='=newsection:', what='copy', ifrequired=True)]

            logs += [LogTask(line)]
        
        ###################################################################
        # . indicates usually a task, maybe a longer root
        elif firstchar == '.':
            # reset currentmark
            self._currentmark = ''
            # proceed
            #_line = '.'.join(self._currentroot)+line
            if '=' in line: 
                # with new full line we create and save the task
                if '+' in line:
                    tasks += self.taskSplitter(root=self._currentroot, line=line[1:])
                else:
                    tasks += [ReportTask(root=self._currentroot, line=line[1:], settings=self.settings)]
            else:
                # enhance currentroot for multilevel roots
                # and reset it to the correct level if any sublevel is referenced
                # mostly for docx-files --> doc_sections['order']
                self.updateRoot(i,line)
                tasks += [ReportTask(root=self._currentroot,line='=newsection:', what='copy')]

            logs += [LogTask(line)]
        
        ###################################################################
        # @ means: do something at this marker, like add new content '+' (see next)
        # makes only sense when there is either such a + or a & in the coming lines
        elif firstchar == '@':
            # set currentmark
            self._currentmark = line[1:].lower()
            logs += [LogTask(line)]
    
        ###################################################################
        elif firstchar == '+':
            # use currentmark    
            tasks += self.taskSplitter(root=self._currentroot, line=line[1:], 
                                       what='add', where=self._currentmark)
            logs += [LogTask(line)]
        
        ###################################################################
        elif firstchar == '&':
            # use currentmark
            # for now &include only!
            if line.lower().startswith('&include'):
                # include further files or a single as RDF, optional with a given marker (@)
                # example:   &include=file:other*.rdf
                #            @marker:somewhere
                #            &include+=loopfiles:other*.rdf
                #
                _front,toinclude = line.split('=',1) # any case where I may find more than one "="?
                _front = _front.lower().replace('&include','',1) # now _front is '+' or ''
                # for now there is no difference between += and =
                if toinclude.lower().startswith('file'):
                    # include one file , be aware for cases in tests: C:\wherever
                    incfile = toinclude.split(':',1)[1]
                    incfile,exists = getCorrectFile(incfile, True)
                    if exists:
                        nfile = os.path.abspath(incfile)
                        if nfile in self._visited:
                            errors += [f'&include cycle detected: {nfile}']
                        else:
                            #print(self._currentroot)
                            newRdf = ReportDataFile(incfile,_root=self._currentroot,
                                                    _mark=self._currentmark, _settings=self.settings,
                                                    _visited=self._visited)
                            #print(self._currentroot)
                            ReportDataFile._depth -= 1
                            tasks += newRdf.tasks
                            logs += newRdf.logs
                            errors += newRdf.errors
                            # after return we need to reset currentpath and currenmark for the log!
                            logs += [LogTask('# reset root and mark when we come back from included files')]
                            logs += [LogTask('.'.join(self._currentroot))]
                            if self._currentmark:
                                logs += [LogTask('@'+self._currentmark)]
                    else:
                        errors += [f'&include fails to find file {incfile!r}']
                elif toinclude.lower().startswith('loopfiles'):
                    # include several files with wildcards
                    #print(toinclude.split(':')[1][1:-1])
                    _pat = toinclude.split(':')[1]
                    if glob.glob(_pat):
                        _glob = glob.glob(_pat)
                    else:
                        _glob = glob.glob(self.settings.datadir+os.sep+_pat)
                    if not _glob:
                        errors += [f'&include pattern {_pat!r} not found']
                    for incfile in _glob:
                        nfile = os.path.abspath(incfile)
                        if nfile in self._visited:
                            errors += [f'&include cycle detected: {nfile}']
                            continue
                        # glob returns only files that do exist
                        newRdf = ReportDataFile(incfile,_root=self._currentroot,
                                                _mark=self._currentmark, _settings=self.settings,
                                                _visited=self._visited)
                        ReportDataFile._depth -= 1
                        tasks += newRdf.tasks
                        logs += newRdf.logs
                        errors += newRdf.errors
                        # after return we need to reset currentpath and currenmark for the log!
                        logs += [LogTask('# reset root and mark when we come back from included files')]
                        logs += [LogTask('.'.join(self._currentroot))]
                        if self._currentmark:
                            logs += [LogTask('@'+self._currentmark)]
                    
            else:
                errors += [f'Meaning of line {i+1} in file {self.source!r} not defined']

        ###################################################################
        # read SETTINGS
        elif firstchar == '*':
            key,value = line[1:].split('=',1)
            key = key.strip() # although " = " is not supported
            value = value.strip()

            usage = ReportDataFile._global_settings.setdefault(key, [])
            if usage:
                errors += [f'Global setting *{key} defined more than once']
            usage.append((value, self.source, i+1))

            if key == 'version':
                if int(value) < MIN_REQUIRED_VERSION:
                    errors += [
                        f'Cannot read rdf version lower than {MIN_REQUIRED_VERSION}, see line {i+1} in file {self.source!r}'
                    ]
                    return [],[],errors
                if self.settings.version == 0:
                    # set only once
                    self.settings.version = int(value)
                    logs += [LogTask(line)]
            elif key == 'documenttype':
                value = value.lower()
                if not self.settings.documenttype:
                    if value in SECTION_NAMESPACES:
                        self.settings.documenttype = value
                        self.namespace = SECTION_NAMESPACES[value]
                        logs += [LogTask(line)]
                    else:
                        errors += [
                            f'No idea how to define *documenttype which is {value!r}'
                        ]
            elif key == 'datadir':
                # location of pictures etc.
                value = Path(value.replace('\\','/'))
                #print('PATH', os.getcwd(), value)
                if value.exists():
                    self.settings.datadir = value
                    logs += [LogTask(line)]
                else:
                    errors += [
                        f'Non existing *datadir {value!r} defined in {self.source!r}'
                    ]
            elif key in SETTINGS.allowed:
                if key.startswith('date') or key == 'documenttitle':
                    value = removeQuotes(value.strip())
                self.settings.__setattr__(key,value)
                logs += [LogTask(line)]
            else:
                logs += [LogTask('Ignored entry: '+line, comment=True)]

        ###################################################################
        return tasks, logs, errors

    def updateRoot(self, i, line):
        """check and update whether line can be a root and is within the valid namespace
        
        updates self._currentroot --> list of strings ['section:name','subsection: foo'...]
        """
        sline = line.lower().split('.')
        order = self.namespace['order']
        names = self.namespace['names']
        mand = self.namespace['mandatory']

        if sline == ['global']:
            self._currentroot = sline
        elif line[0].isalpha():
            for j, sl in enumerate(sline):
                try:
                    secname, othername = sl.split(':',1)
                except Exception as e:
                    # exception of the rule eg. for PPTX: allow for pure names
                    # in the docx case this will lead to an error below
                    secname = sl
                if nname := names.get(j,None):
                    if mand and nname != secname:
                        self.errors += [
                            f'File {self.source!r}:\n  section {secname!r}, line {i+1} is not in allowed order: {order}'
                        ]
                else:
                    self.errors += [
                        f'File {self.source!r}:\n  section naming {secname!r}, line {i+1} is not in allowed namespace[{j}]: {order}'
                    ]
            self._currentroot = sline
        else: # start with .
            secname, othername = sline[1].split(':',1)
            # check if is in order
            if secname not in order:
                self.errors += [
                    f'File {self.source!r}:\n  section {secname!r}, line {i+1} is not in allowed order: {order}'
                ]
            else:
                index = order.index(secname)
                lenroot = len(self._currentroot)
                if index == lenroot: 
                    # just the next level: add it
                    # recheck rest of line if any
                    self.updateRoot(i,'.'.join(self._currentroot+sline[1:]))
                elif index > lenroot:
                    # there is a gap!
                    self.errors += [
                        f'File {self.source!r}:\n  section {secname!r}, line {i+1} creates a gap in allowed order: {order}'
                    ]
                else: # index < lenroot
                    # cut back to the point we can implement
                    self.updateRoot(i,'.'.join(self._currentroot[:index]+sline[1:]))
        #print('U',self._currentroot)

    def taskSplitter(self, root, line, **modifier):
        """split inside unique tasks to extract content and lines like that
        +video:generic=file:harmonic.mp4+image:poster=file:harmonic.gif+description='an animated beam'+width=4cm
        
        .table:generic=file:table2.csv+description='Hello world'

        into:

        """
        if modifier.get('what',None) == 'add':
            elements = line.split('+') 
            addition = elements[0].split('=') # that is the rest of the path and the content + n modifiers
            # all the rest in the line are somehow modifiers
            actions = {}
            for el in elements[1:]:
                n,v = el.split('=')
                n = n.strip()
                actions[n] = Value(v.strip(),self.settings, target=n)
            modifier['actions'] = actions
            task = [ReportTask(root=root, 
                               line=addition[0].lower().strip()+'='+addition[1], settings=self.settings, **modifier)]    

        else:
            path, rawvalue = line.split('=',1)
            path = path.lower().strip()
            elements = rawvalue.split('+')
            actions = {}
            for el in elements[1:]:
                n,v = el.split('=')
                n = n.strip()
                actions[n] = Value(v.strip(),self.settings, target=n)
            modifier['actions'] = actions
            task = [ReportTask(root=root, line=path+'='+elements[0], settings=self.settings, **modifier)]

        return task

    def __repr__(self):
        """for debugging
        display content in assembled format and print what has been evaluated"""

        r = []

        if self.root == None:
            # never evaluated 
            r += self.errors
        elif self.root:
            r += [
                f'# *** base content of reportData-file {self.source!r} ***',
                '#   global SETTINGS (for the full project):',
            ]
            for k in self.settings.allowed:
                if k == 'version':
                    r += [f'# *{k} >= 1']
                    continue
                else:
                    r += [f'# *{k}={self.settings.__getattribute__(k)}']
        
        for t in self.logs:
            r += [str(t)]

        return '\n'.join(r)

    def inspect(self):
        r = []
        for t in self.tasks:
            r += [t._inspect()]
        return r

    def showFiles(self):
        """cycle through tasks and show which files are missing"""

        missing = ['Missing files']
        found = ['Existing files']
        for task in self.tasks:
            if task.value.type in ['file', 'parfile']:
                if not task.value.object.exists:
                    missing += [task.value.object.filename]
                else:
                    found += [task.value.object.filename]
        
        print('\n '.join(found))
        print('\n '.join(missing))

