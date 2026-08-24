"""The placement math of ``Scriptum._pptx.template_utils``, pinned.

``resolve_template_box`` decides where a ``Template:Image`` block lands inside
a marker shape: the marker is the container, ``top``/``left``/``bottom``/
``right`` actions shrink it, ``width``/``height`` override the block's own
size, and whatever comes out is clamped so nothing ever leaves the marker.
These tests fix that order of operations -- offsets first, then size, then the
clamp -- with plain-number stubs, because a wrong box here shows up as a
picture quietly parked at the slide edge, which no text comparison sees.
"""

from types import SimpleNamespace

from pptx.util import Cm

from Scriptum._pptx.template_utils import (
    BoundingBox,
    compute_template_bounds,
    length_from_actions,
    resolve_template_box,
    scale_dimension,
)


def box(top=0, left=0, width=0, height=0):
    return BoundingBox(top=top, left=left, width=width, height=height)


def length(value, unit):
    """An action the way the tag parser hands it over: value plus unit."""
    return SimpleNamespace(value=value, unit=unit)


# ------------------------------------------------------------- BoundingBox

def test_a_box_knows_its_far_edges():
    assert (box(top=10, left=20, width=100, height=50).right,
            box(top=10, left=20, width=100, height=50).bottom) == (120, 60)


def test_from_shape_reads_the_pptx_ordering():
    shape = SimpleNamespace(top=1, left=2, width=3, height=4)
    assert BoundingBox.from_shape(shape) == box(top=1, left=2, width=3, height=4)


def test_clamp_cuts_a_box_to_its_container():
    container = box(0, 0, 100, 100)
    assert box(10, 10, 200, 200).clamp(container) == box(10, 10, 90, 90)


def test_clamp_collapses_a_box_entirely_outside():
    container = box(0, 0, 100, 100)
    assert box(200, 200, 50, 50).clamp(container) == box(100, 100, 0, 0)


def test_template_bounds_cover_all_shapes():
    """The union box over ``.thing`` geometry -- what a multi-shape template
    block occupies before it is scaled into its marker."""
    shapes = [SimpleNamespace(thing=SimpleNamespace(top=0, left=0, width=10, height=10)),
              SimpleNamespace(thing=SimpleNamespace(top=20, left=5, width=10, height=10))]
    assert compute_template_bounds(shapes) == box(top=0, left=0, width=15, height=30)


# ------------------------------------------------- actions to EMU lengths

def test_a_length_action_converts_its_unit():
    actions = {'top': length(2, 'cm')}
    assert length_from_actions(actions, 'top') == Cm(2)


def test_an_unknown_unit_falls_back_to_the_default():
    actions = {'top': length(2, 'furlong')}
    assert length_from_actions(actions, 'top', default=7) == 7
    assert length_from_actions({}, 'top', default=7) == 7


def test_scaling_keeps_integer_emus():
    assert scale_dimension(Cm(1), 1.0) == Cm(1)
    assert scale_dimension(100, 0.333) == 33


# ------------------------------------------------- resolving the final box

MARKER = SimpleNamespace(top=Cm(2), left=Cm(1), width=Cm(10), height=Cm(5))


def test_without_actions_the_template_keeps_its_own_size():
    resolved = resolve_template_box(MARKER, Cm(4), Cm(3), {})
    assert resolved == box(top=Cm(2), left=Cm(1), width=Cm(4), height=Cm(3))


def test_top_and_left_move_the_box_inside_the_marker():
    actions = {'top': length(1, 'cm'), 'left': length(2, 'cm')}
    resolved = resolve_template_box(MARKER, Cm(4), Cm(3), actions)
    assert resolved == box(top=Cm(3), left=Cm(3), width=Cm(4), height=Cm(3))


def test_an_oversized_override_is_capped_at_the_marker():
    resolved = resolve_template_box(MARKER, Cm(4), Cm(3),
                                    {'width': length(20, 'cm')})
    assert resolved.width == Cm(10)


def test_mode_available_fills_the_marker_instead():
    resolved = resolve_template_box(MARKER, Cm(4), Cm(3), {},
                                    default_width='available',
                                    default_height='available')
    assert (resolved.width, resolved.height) == (Cm(10), Cm(5))
