

class SETTINGS:
    """store all current settings for every current RDF-file"""
    version        = 0
    # see: https://docs.python.org/3/library/datetime.html
    dateformat     = '%x'
    datetimeformat = '%c'
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

