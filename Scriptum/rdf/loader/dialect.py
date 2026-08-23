#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

"""PyYAML restricted to the YAML 1.2 core schema.

PyYAML implements **YAML 1.1**, whose implicit typing is actively wrong for a
format whose values are report prose. Measured on PyYAML 6.0.3:

===========================  ======================  =================
written                      PyYAML default (1.1)    core schema (1.2)
===========================  ======================  =================
``no``, ``NO``, ``on``, ``off``, ``yes``   ``bool``  ``str``
``1:30``                     ``int 90`` (sexagesimal)   ``str``
``1_000``                    ``int 1000``            ``str``
``0755``                     ``int 493`` (octal)     ``int 755``
``2.5e3``                    ``str``                 ``float 2500.0``
===========================  ======================  =================

A cell reading ``no`` silently becoming ``False`` in a finished report is the
same class of failure as the old text format turning ``.head=Serving`` into
``invalid`` -- which is one of the things this format exists to end.

Two traps, both of which bite silently
--------------------------------------
**Replacing the implicit resolvers is not enough.** The resolver decides which
tag a plain scalar gets; the *constructor* decides what Python object that tag
becomes, and PyYAML's ``construct_yaml_int`` still applies 1.1 rules. Leave it
in place and ``0755`` resolves as an int and is then built as octal ``493`` --
a 1.1 value wearing a 1.2 tag. The constructors are replaced too.

**The resolver map must be copied onto the subclass before it is edited.**
``yaml_implicit_resolvers`` is inherited, so ``cls.yaml_implicit_resolvers[ch]
= ...`` mutates ``SafeLoader``'s own map and reconfigures YAML parsing for the
whole process -- every other library in the interpreter included. PyYAML's
``add_implicit_resolver`` and ``add_constructor`` both copy-on-write, keyed on
``'yaml_implicit_resolvers' in cls.__dict__``; assigning the filtered map first
*is* that copy, so the ``add_*`` calls below then see it and do not copy again.

What is deliberately left alone
-------------------------------
``null`` already matches 1.2 (``~``, ``null``, ``Null``, ``NULL``, empty).

What is removed outright
------------------------
The 1.1 schema resolves four more tags that the 1.2 core schema does not have,
and each of them bit or would bite:

* ``timestamp`` -- ``2022-12-15`` became a ``datetime.date`` and
  ``2022-12-15 14:24:59`` a ``datetime.datetime``, so an unquoted date written
  where the format asks for one (``{date: 2022-12-15}``) arrived as an object
  the loader could only refuse with "needs text". Under the core schema it is
  the string it looks like, and ``date:`` reads it.
* ``merge`` (``<<``) and ``value`` (``=``) -- SafeLoader resolves the tags but
  has no scalar constructor for them, so a stray ``<<`` written as a key or a
  value raised ``ConstructorError`` out of the loader instead of producing a
  diagnostic. As strings they are refused as what they are: not an address.
* ``yaml`` (``!``, ``&``, ``*`` as whole scalars) -- the same shape of failure.

So the resolver map keeps exactly ``null``, ``bool``, ``int`` and ``float`` --
which is the core schema.
"""

import re

import yaml

#: Tags whose 1.1 behaviour is replaced wholesale.
_REPLACED = frozenset({
    'tag:yaml.org,2002:bool',
    'tag:yaml.org,2002:int',
    'tag:yaml.org,2002:float',
})

#: 1.1 tags the core schema does not have at all. A scalar that would have
#: resolved to one of these is a plain string here.
_DROPPED = frozenset({
    'tag:yaml.org,2002:timestamp',
    'tag:yaml.org,2002:merge',
    'tag:yaml.org,2002:value',
    'tag:yaml.org,2002:yaml',
})

#: YAML 1.2 core schema. Note what is absent: ``yes``/``no``/``on``/``off``,
#: sexagesimals, ``_`` digit separators, and leading-zero octal.
BOOL_1_2 = re.compile(r'^(?:true|True|TRUE|false|False|FALSE)$')

#: A sign is allowed on the decimal form only, as in the 1.2 core schema.
INT_1_2 = re.compile(r'^(?:[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$')

FLOAT_1_2 = re.compile(
    r'^(?:[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?'
    r'|[-+]?\.(?:inf|Inf|INF)'
    r'|\.(?:nan|NaN|NAN))$'
)


class Core12Loader(yaml.SafeLoader):
    """``SafeLoader`` with 1.1 implicit typing removed.

    Safe in the same sense its base is: an unknown ``!`` tag is refused rather
    than constructed, so a document cannot name a Python type to instantiate.
    """


# Assigning the filtered map is what gives the subclass its own copy. Do this
# BEFORE any add_implicit_resolver call -- see the module docstring.
Core12Loader.yaml_implicit_resolvers = {
    first: [(tag, pattern) for tag, pattern in resolvers
            if tag not in _REPLACED and tag not in _DROPPED]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}

Core12Loader.add_implicit_resolver(
    'tag:yaml.org,2002:bool', BOOL_1_2, list('tTfF'))
Core12Loader.add_implicit_resolver(
    'tag:yaml.org,2002:int', INT_1_2, list('-+0123456789'))
Core12Loader.add_implicit_resolver(
    'tag:yaml.org,2002:float', FLOAT_1_2, list('-+0123456789.'))


def _construct_bool(loader, node):
    return loader.construct_scalar(node).lower() == 'true'


def _construct_int(loader, node):
    text = loader.construct_scalar(node)
    if text[:2].lower() in ('0o', '0x'):
        # base 0 reads the 0o/0x prefix; base 10 is used everywhere else so a
        # leading zero stays decimal instead of turning into octal.
        return int(text, 0)
    return int(text, 10)


def _construct_float(loader, node):
    text = loader.construct_scalar(node)
    lowered = text.lower()
    if lowered.endswith('.inf'):
        return float('-inf') if lowered.startswith('-') else float('inf')
    if lowered.endswith('.nan'):
        return float('nan')
    return float(text)


Core12Loader.add_constructor('tag:yaml.org,2002:bool', _construct_bool)
Core12Loader.add_constructor('tag:yaml.org,2002:int', _construct_int)
Core12Loader.add_constructor('tag:yaml.org,2002:float', _construct_float)


__all__ = ['Core12Loader', 'BOOL_1_2', 'INT_1_2', 'FLOAT_1_2']
