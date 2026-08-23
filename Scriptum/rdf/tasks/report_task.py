"""The task: one instruction for a back end, and the only thing it receives."""

#: ``path[0]`` of a task that fills everywhere rather than at one address.
#: A back end recognises a global task by this. It follows the document
#: key so the two cannot drift apart.
GLOBAL_ROOT = '_global_'


class ReportTask:
    """One instruction: an address, a value, and what to do with them.

    The loader builds these (``Scriptum/rdf/loader/tasks.py``) and a back end
    consumes them; it never sees the document text. So the attributes are the
    contract between reader and renderer:

    ``myAddress``
        the **instance** address as a list of canonical four-slot segments --
        ``['section:a::1', 'subsection:b::2', ':head::1']`` -- which joins with
        ``.`` for an addressbook lookup; ``[0]`` is the section, ``[:-1]`` the
        parent and ``[-1]`` the element itself.
    ``path``
        the **template** address: the ancestors as template names, without
        instance numbers. For a structural task it ends with the block being
        applied or copied, because that is what ``findTemplate`` looks up.
    ``target``
        the template name of the element to fill -- the tag as written in the
        ``.docx`` or ``.pptx``. Empty for a structural task.
    ``value``
        the typed :class:`~Scriptum.rdf.values.Value`.
    ``what``
        ``''`` (fill), ``apply``, ``copy`` or ``add`` -- the structural
        operation, decided by the loader from the instance id.
    ``where``
        the marker an ``add`` lands at.
    ``actions``
        the modifiers, each itself a ``Value``; already applied to the value
        for the types that read them (tables take their caption from one).
    ``modified``
        whether ``what``, ``where`` or ``actions`` mean anything.
    ``finaltarget``
        ``myAddress[-1]`` -- the instance address of the element.
    ``serial``
        the task's position in the list, 1-based, assigned by the loader once
        the list is complete. Tasks come out in document order, so it is also
        the execution order.

    ``target`` and ``myAddress[-1]`` say different things, which is the point:
    the template name and the instance address. The ``.rdf`` text format gave
    the first instance the same string for both and renamed only the repeats
    (``foo_c002``), so a blueprint and a copy of it shared one name by accident
    of which was written first.

    There is no class state here. The text parser kept a process-global tree
    to number repeats; a YAML document's instance numbers come from its own
    nesting, assigned while the loader walks, so nothing has to be remembered
    between documents.
    """

    _debug = False

    @classmethod
    def set_debug(cls, enabled: bool) -> None:
        """Enable or disable debug output for inspections."""

        cls._debug = bool(enabled)

    def __init__(self, myAddress, path, target, value,
                 what='', where='', actions=None):
        self.serial = 0
        self.myAddress = list(myAddress)
        self.path = list(path)
        self.target = target
        self.value = value
        self.what = what
        self.where = where
        self.actions = dict(actions) if actions else {}
        self.modified = bool(what or where or self.actions)
        self.finaltarget = self.myAddress[-1] if self.myAddress else ''

        if self.actions:
            self.value.applyActions(self.actions)

    def __repr__(self) -> str:
        rval = '   ' + '.'.join(self.path) + ' = ' + self.value.__repr__()
        if self.modified:
            rval += f"\n     +-> modified: what = {self.what}; where = {self.where}; actions = {self.actions}"

        if self.myAddress != self.path:
            rval += f"\n     +-> new (full) path: {'.'.join(self.myAddress)}"
        return rval

    def _inspect(self):
        r = {
            'number': self.serial,
            'path': self.path,
            'value': self.value,
            'address': self.myAddress,
        }
        if self.target:
            r['target'] = self.target
        if ReportTask._debug:
            r['modified'] = self.modified
        if self.modified:
            r['what'] = self.what
            if self.where:
                r['where'] = self.where
            if self.actions:
                r['actions'] = self.actions

        return r
