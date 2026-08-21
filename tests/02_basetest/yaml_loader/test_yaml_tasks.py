"""The task list a back end runs, and ``load`` end to end.

Three decisions live here and are what these tests are for:

* tasks come out in document order, a container before its children, with
  **global fills last** -- so "applied last" is a property of the list rather
  than a rule every back end re-implements;
* **instance 1 applies and later instances copy** in Word, while PowerPoint
  copies always, its template holding layouts rather than slides;
* ``target`` and ``myAddress[-1]`` say different things on purpose -- the
  template name and the instance address, which the old ``_cNNN`` scheme
  conflated for whichever instance happened to be written first.
"""

from __future__ import annotations

import textwrap

import pytest

from Scriptum.rdf.loader import (Diagnostics, DocumentError, GLOBAL_ROOT,
                                 YamlSource, emit, load, read_content,
                                 read_global, read_root)

SETTINGS = '_scriptum_:\n  version: 4\n  documenttype: docx\n'


def tasks_of(document, documenttype='docx'):
    text = SETTINGS.replace('docx', documenttype) + textwrap.dedent(document)

    diagnostics = Diagnostics()
    source = YamlSource.from_text(text.encode('utf-8'), 'doc.yaml', diagnostics)
    header = read_root(source, diagnostics)
    globals_ = read_global(header.global_node, source, header.settings,
                           diagnostics)
    entries = read_content(header.content_node, source, header.settings,
                           diagnostics)
    assert not diagnostics, diagnostics.report()
    return emit(entries, header.settings, globals_)


def shape(tasks):
    return [(t.what, '.'.join(t.myAddress), t.target) for t in tasks]


# ------------------------------------------------------------------ order

def test_a_container_comes_before_its_own_children():
    tasks = tasks_of("""
        _content_:
          - section:a:
              - head: one
              - subsection:b:
                  - head: two
    """)

    assert shape(tasks) == [
        ('apply', 'section:a::1', ''),
        ('', 'section:a::1.:head::1', 'head'),
        ('apply', 'section:a::1.subsection:b::1', ''),
        ('', 'section:a::1.subsection:b::1.:head::1', 'head'),
    ]


def test_serials_run_in_document_order():
    tasks = tasks_of("""
        _content_:
          - section:a:
              - head: one
              - head: two
    """)

    assert [t.serial for t in tasks] == sorted(t.serial for t in tasks)


def test_global_fills_come_last_whatever_the_document_says():
    """The text format put them where the author wrote ``global`` -- usually
    first -- so each back end ran two passes and had to remember to skip them
    in the first. Here the list carries the rule."""
    tasks = tasks_of("""
        _global_:
          report:id: ID 4711
        _content_:
          - section:a:
              - head: one
    """)

    assert tasks[-1].target == 'report:id'
    assert tasks[-1].path == [GLOBAL_ROOT]


def test_a_marker_emits_no_task_of_its_own():
    """It is a position, not an element. What it holds carries its name."""
    tasks = tasks_of("""
        _content_:
          - section:a:
              - marker:content:
                  - image:generic: {file: a.png}
    """)

    assert [t.target for t in tasks] == ['', 'image:generic']
    assert tasks[1].where == 'marker:content'


# --------------------------------------------------------- apply or copy

def test_the_first_instance_applies_and_the_next_copies():
    """The settled rule, now decided by the id. The text format got the same
    answer by renaming a repeat to foo_c002 and then checking whether the name
    had changed."""
    tasks = tasks_of("""
        _content_:
          - section:a:
              - subsection:b:
                  - head: one
              - subsection:b:
                  - head: two
    """)

    structural = [(t.what, t.myAddress[-1]) for t in tasks if not t.target]
    assert structural == [('apply', 'section:a::1'),
                          ('apply', 'subsection:b::1'),
                          ('copy', 'subsection:b::2')]


def test_powerpoint_copies_every_instance():
    """Its template holds layouts, not slides, so there is no first instance
    sitting there to fill and the reuse question never arises."""
    tasks = tasks_of("""
        _content_:
          - TitleSlide:
              - title: one
          - TitleSlide:
              - title: two
    """, documenttype='pptx')

    structural = [(t.what, t.myAddress[-1]) for t in tasks if not t.target]
    assert structural == [('copy', ':titleslide::1'),
                          ('copy', ':titleslide::2')]


def test_a_container_task_carries_itself_in_its_address():
    """``[:-1]`` is the parent and ``[-1]`` the element to create, which is
    what the docx side reads when it looks for somewhere to put a copy."""
    tasks = tasks_of("""
        _content_:
          - section:a:
              - subsection:b:
                  - head: x
    """)

    copy = [t for t in tasks if not t.target][-1]
    assert copy.myAddress == ['section:a::1', 'subsection:b::1']
    assert copy.myAddress[:-1] == ['section:a::1']
    assert copy.path == copy.myAddress


def test_a_structural_task_carries_a_newsection_value():
    tasks = tasks_of('_content_:\n  - section:a:\n      - head: x\n')

    assert tasks[0].value.type == 'newsection'


# ------------------------------------------------------- what a task says

def test_target_is_the_template_name_and_myaddress_the_instance():
    """The split the whole id decision exists for.

    The old scheme gave the first instance the same string for both and
    renamed only the rest, so two different things -- a blueprint and a copy
    of it -- shared one name by accident of which was written first.
    """
    tasks = tasks_of("""
        _content_:
          - section:a:
              - head: one
              - head: two
    """)

    fills = [t for t in tasks if t.target]
    assert [t.target for t in fills] == ['head', 'head']
    assert [t.myAddress[-1] for t in fills] == [':head::1', ':head::2']
    assert [t.finaltarget for t in fills] == [':head::1', ':head::2']


def test_a_fill_inside_a_marker_is_an_add():
    tasks = tasks_of("""
        _content_:
          - section:a:
              - marker:content:
                  - image:generic: {file: a.png, description: a part}
    """)

    add = tasks[-1]
    assert (add.what, add.where) == ('add', 'marker:content')
    assert add.modified is True
    assert 'description' in add.actions


def test_a_plain_fill_is_not_modified():
    """``modified`` is what the docx side branches on to decide whether a task
    is structural at all."""
    tasks = tasks_of('_content_:\n  - section:a:\n      - head: x\n')

    assert tasks[1].modified is False
    assert (tasks[1].what, tasks[1].where) == ('', '')


def test_actions_reach_the_value_that_reads_them():
    tasks = tasks_of("""
        _content_:
          - section:a:
              - table:t: {file: t.csv, description: {from: row1}}
    """)

    fill = tasks[-1]
    assert fill.value.object.actions == fill.actions


def test_a_global_task_has_no_id_and_matches_on_target():
    """Matching by puretag is what lets a global reach clones -- which the old
    _cNNN renaming silently prevented, a renamed clone no longer equalling the
    name the global was addressed at."""
    tasks = tasks_of("""
        _global_:
          report:id: ID 4711
        _content_:
          - section:a:
              - head: x
    """)

    task = tasks[-1]
    assert task.myAddress == [GLOBAL_ROOT, 'report:id']
    assert task.target == 'report:id'
    assert '::' not in task.myAddress[-1]


def test_checkpath_does_not_run_and_nothing_is_renamed():
    """from_parts bypasses it. The instance numbers came from the document's
    own nesting, which is what checkPath was reconstructing from a flat file --
    running it as well would number them twice."""
    tasks = tasks_of("""
        _content_:
          - section:a:
              - subsection:b:
                  - head: x
              - subsection:b:
                  - head: y
    """)

    assert not any('_c0' in segment for t in tasks for segment in t.myAddress)


def test_inspect_still_works_on_an_emitted_task():
    """The debug surface the notebook tests use."""
    tasks = tasks_of('_content_:\n  - section:a:\n      - head: x\n')

    inspected = tasks[1]._inspect()
    assert inspected['target'] == 'head'
    assert inspected['address'] == ['section:a::1', ':head::1']


# ------------------------------------------------------------------- load

def test_load_runs_every_stage(tmp_path):
    (tmp_path / 'fragment.yaml').write_text(
        '- subsection:b:\n    - head: from the fragment\n', encoding='utf-8')
    document = tmp_path / 'report.yaml'
    document.write_text(SETTINGS + textwrap.dedent("""
        _global_:
          report:status: Draft
        _content_:
          - section:a:
              - head: Title
              - _include_: fragment.yaml
    """), encoding='utf-8')

    loaded = load(document)

    assert loaded.settings.documenttype == 'docx'
    assert shape(loaded.tasks) == [
        ('apply', 'section:a::1', ''),
        ('', 'section:a::1.:head::1', 'head'),
        ('apply', 'section:a::1.subsection:b::1', ''),
        ('', 'section:a::1.subsection:b::1.:head::1', 'head'),
        ('', f'{GLOBAL_ROOT}.report:status', 'report:status'),
    ]


def test_load_raises_with_every_diagnostic_not_the_first(tmp_path):
    document = tmp_path / 'report.yaml'
    document.write_text(textwrap.dedent("""
        _scriptum_:
          version: 2
          documentype: docx
        _content_:
          - 'section:a':
              - head: x
    """), encoding='utf-8')

    with pytest.raises(DocumentError) as caught:
        load(document)

    report = str(caught.value)
    assert 'needs at least 4' in report
    assert "unknown setting 'documentype'" in report
    assert len(caught.value.diagnostics) >= 3


def test_load_reports_a_file_it_cannot_read(tmp_path):
    with pytest.raises(DocumentError) as caught:
        load(tmp_path / 'absent.yaml')

    assert 'cannot read' in str(caught.value)


def test_a_document_repr_says_what_it_holds(tmp_path):
    document = tmp_path / 'report.yaml'
    document.write_text(SETTINGS + '_content_:\n  - section:a:\n      - head: x\n',
                        encoding='utf-8')

    assert '2 tasks' in repr(load(document))
