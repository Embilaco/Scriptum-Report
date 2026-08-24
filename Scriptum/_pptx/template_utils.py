"""Helper utilities shared by the PowerPoint templates."""

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional

from .units import units


# dataclass: __init__/__repr__/__eq__ are generated from the fields below;
# frozen=True forbids reassignment, so instances are immutable and hashable.
@dataclass(frozen=True)
class BoundingBox:
    """Simple representation of a rectangular area in EMUs."""

    top: int
    left: int
    width: int
    height: int

    @property
    def bottom(self) -> int:
        return self.top + self.height

    @property
    def right(self) -> int:
        return self.left + self.width

    @classmethod
    def from_shape(cls, shape: Any) -> "BoundingBox":
        """Create a bounding box from a python-pptx shape."""

        return cls(int(shape.top), int(shape.left), int(shape.width), int(shape.height))

    def clamp(self, container: "BoundingBox") -> "BoundingBox":
        """Restrict the box so that it fits inside *container*."""

        top = min(max(self.top, container.top), container.bottom)
        left = min(max(self.left, container.left), container.right)
        bottom = min(max(self.bottom, container.top), container.bottom)
        right = min(max(self.right, container.left), container.right)
        width = max(0, right - left)
        height = max(0, bottom - top)
        return BoundingBox(top, left, width, height)


def compute_template_bounds(shapes: Iterable[Any]) -> BoundingBox:
    """Return the bounding box covering all *shapes*."""

    iterator = iter(shapes)
    first = next(iterator)
    top = int(first.thing.top)
    left = int(first.thing.left)
    right = int(first.thing.left + first.thing.width)
    bottom = int(first.thing.top + first.thing.height)

    for shape in iterator:
        thing = shape.thing
        top = min(top, int(thing.top))
        left = min(left, int(thing.left))
        right = max(right, int(thing.left + thing.width))
        bottom = max(bottom, int(thing.top + thing.height))

    return BoundingBox(top=top, left=left, width=right - left, height=bottom - top)


def length_from_actions(actions: Mapping[str, object], key: str, default: Optional[int] = None) -> Optional[int]:
    """Extract a length action and return it converted to EMUs."""

    action = actions.get(key)
    if action is None:
        return default

    obj = getattr(action, "object", action)
    value = getattr(obj, "value", None)
    unit = getattr(obj, "unit", None)

    if value is None or unit is None:
        return default

    converter = units.get(str(unit).lower())
    if converter is None:
        return default

    try:
        return int(converter(value))
    except Exception:
        return default


def float_from_actions(actions: Mapping[str, object], key: str) -> Optional[float]:
    """Extract a float based action (e.g. scale)."""

    action = actions.get(key)
    if action is None:
        return None

    obj = getattr(action, "object", action)
    value = getattr(obj, "value", None)

    if isinstance(value, (int, float)):
        return float(value)

    try:
        return float(obj)
    except (TypeError, ValueError):
        return None


def scale_dimension(value: int, scale: float) -> int:
    """Scale a dimension by *scale* while keeping pptx EMU units."""

    if scale == 1.0:
        return int(value)
    return int(round(float(value) * scale))


def resolve_template_box(
    shape: Any,
    template_width: int,
    template_height: int,
    actions: Mapping[str, object],
    *,
    default_width: str = "template",
    default_height: str = "template",
    ) -> BoundingBox:
    """Resolve the final bounding box for a template inside *shape*."""

    container = BoundingBox.from_shape(shape)

    top_offset = length_from_actions(actions, "top", 0) or 0
    left_offset = length_from_actions(actions, "left", 0) or 0
    bottom_offset = length_from_actions(actions, "bottom", 0) or 0
    right_offset = length_from_actions(actions, "right", 0) or 0

    top = container.top + top_offset
    left = container.left + left_offset
    bottom = container.bottom - bottom_offset
    right = container.right - right_offset

    if bottom < top:
        bottom = top
    if right < left:
        right = left

    available_width = right - left
    available_height = bottom - top

    width_override = length_from_actions(actions, "width")
    height_override = length_from_actions(actions, "height")
    #print('O', width_override, height_override)

    width = _pick_dimension(width_override, available_width, template_width, default_width)
    height = _pick_dimension(height_override, available_height, template_height, default_height)

    return BoundingBox(int(top), int(left), int(width), int(height)).clamp(container)


def _pick_dimension(override: Optional[int], available: int, template: int, mode: str) -> int:
    if override is not None:
        base = override
    elif mode == "available":
        base = available
    else:
        base = template if template is not None else available

    base = min(base, available)

    return max(0, int(base))

