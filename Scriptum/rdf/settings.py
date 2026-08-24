

class SETTINGS:
    """store all current settings for every current report document"""
    version        = 0
    # strftime patterns, see: https://docs.python.org/3/library/datetime.html
    # ISO 8601 by default: unambiguous, sortable, and the same in every
    # process. The C library's locale forms '%x' / '%c' were the defaults
    # before 2026-08-23; they render '08/23/26' / 'Sun Aug 23 14:05:09 2026' in
    # a plain Python process and follow the process locale the moment a host
    # calls setlocale(), so the same document read differently in a notebook
    # and on the command line. Both remain available as explicit settings.
    dateformat     = '%Y-%m-%d'
    datetimeformat = '%Y-%m-%d %H:%M:%S'
    datadir        = '.' # for almost all and global data, files etc.
    nvseparator    = ':' # new in version 2
    csvseparator   = ';' # new in version 3
    floatformat    = '7.4f' # new in version 3
    documenttitle  = 'Autoreport' # new in version 3
    documenttype   = None # new and important in version 3
    # allowed keys
    allowed = ['version','dateformat','datetimeformat','datadir','nvseparator','csvseparator',
               'floatformat', 'documenttitle']
    def __init__(self,settings=None):
        if settings:
            self.version = settings.version
            self.dateformat = settings.dateformat
            self.datetimeformat = settings.datetimeformat
            self.datadir = settings.datadir
            self.nvseparator = settings.nvseparator
            self.csvseparator = settings.csvseparator
            self.floatformat = settings.floatformat
            self.documenttitle = settings.documenttitle
            self.documenttype = settings.documenttype
        else:
            pass # keep the default

    def __repr__(self):
        r = {}
        for k in self.allowed:
            r[k] = self.__getattribute__(k)
        return str(r)

