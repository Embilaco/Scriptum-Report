#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""Turning the entry tree into the task list a back end runs.

A task is what a back end consumes: an address, a value, and what to do with
them. This module is the last step of loading, and it decides three things.

Order
-----
Tasks come out in **document order**, a container before its own children,
which is the order the text format emitted them in and the order both back
ends iterate. PPTX carries a current-slide position through the list, so this
is not merely tidy.

Global fills come **last**, always. The text format put them wherever the
author wrote ``global`` -- usually first -- so each back end had to run two
passes and remember to skip them in the first. Putting them at the end makes
"applied last" a property of the list rather than a rule every consumer
re-implements.

Apply or copy
-------------
For Word, **instance 1 fills the block the template already contains and later
instances are clones**. That is the settled rule, and the id now decides it:
the text format got the same answer by renaming a repeat to ``foo_c002`` and
then checking whether the name had changed.

For PowerPoint, **every instance is a copy**. Its template holds layouts, not
slides, so there is no first instance sitting there to fill and the reuse
question never arises. That difference is declared in the namespace table as
``always_copy`` rather than inferred from ``mandatory``: the two agree today
and there is no reason they must.

Adds
----
A fill inside a marker is an ``add``: it materialises a new element from the
template element its address names and places it at the marker. A fill outside
one targets something the template already contains. That split is unchanged.

Serials
-------
A task's ``serial`` is its position in the finished list, 1-based, stamped here
once the list is complete. The text parser counted on a class attribute that
lived for the whole interpreter, which is why one root document per process
used to be a rule; numbering the list instead leaves nothing behind between
documents.
"""

from ..namespaces import SECTION_NAMESPACES
from ..tasks import GLOBAL_ROOT, ReportTask
from ..values import Value
from .entries import Container, Fill, Marker

def emit(entries, settings, globals_=()):
    """Build the task list from a walked document.

    *entries* is the ``_content_`` tree, *globals_* the ``_global_`` fills.
    """
    ladder = SECTION_NAMESPACES.get(settings.documenttype) or {}
    always_copy = bool(ladder.get('always_copy'))

    tasks = []
    _emit_entries(entries, always_copy, tasks)
    tasks.extend(_global_task(fill) for fill in globals_)
    for number, task in enumerate(tasks, 1):
        task.serial = number
    return tasks


def _emit_entries(entries, always_copy, tasks):
    for entry in entries:
        if isinstance(entry, Container):
            tasks.append(_container_task(entry, always_copy))
            _emit_entries(entry.children, always_copy, tasks)
        elif isinstance(entry, Marker):
            # A marker emits nothing of its own: it is a position, and the
            # things placed there carry its name in `where`.
            _emit_entries(entry.children, always_copy, tasks)
        elif isinstance(entry, Fill):
            tasks.append(_fill_task(entry))


def _container_task(entry, always_copy):
    """One structural operation: fill the template's block, or clone it.

    ``myAddress`` includes the container itself, so ``[:-1]`` is its parent and
    ``[-1]`` the element being applied or created -- which is what the docx
    side reads when it looks for somewhere to put a copy.
    """
    what = 'copy' if (always_copy or entry.address.id != 1) else 'apply'

    return ReportTask(
        myAddress=list(entry.canonical_path) + [entry.address.canonical],
        # `path` is the **template** address and `myAddress` the **instance**
        # one -- which is the split the text format already had, and the reason
        # a copy could find its blueprint at all: it set `path` from the
        # un-renamed current root while `myAddress` carried the _cNNN name.
        # `findTemplate` looks up `path`; the addressbook is keyed on
        # `myAddress`.
        path=_template_path(entry),
        target='',
        value=Value('newsection', '', tostring=False),
        what=what,
    )


def _template_path(entry):
    """Ancestors and self as template names -- no instance numbers."""
    return [address.puretag for address in entry.path] + [entry.address.puretag]


def _fill_task(entry):
    """A value for one target, or an add when the fill sits in a marker."""
    return ReportTask(
        myAddress=list(entry.canonical_path) + [entry.address.canonical],
        # Ancestors as template names, matching the text format's `root`.
        path=[address.puretag for address in entry.path],
        # The template name, not the instance: this is the tag to look for.
        target=entry.address.puretag,
        value=entry.value,
        what='add' if entry.marker else '',
        where=entry.marker or '',
        actions=entry.actions,
    )


def _global_task(fill):
    """A fill applied everywhere, matched on ``target`` alone.

    No id and no path: a global fill is not an instance but a rule about every
    instance, and matching by ``puretag`` is exactly what lets it reach clones
    -- which the old ``_cNNN`` renaming silently prevented, since a renamed
    clone no longer equalled the name the global was addressed at.
    """
    return ReportTask(
        myAddress=[GLOBAL_ROOT, fill.address.puretag],
        path=[GLOBAL_ROOT],
        target=fill.address.puretag,
        value=fill.value,
        actions=fill.actions,
    )


__all__ = ['emit', 'GLOBAL_ROOT']
