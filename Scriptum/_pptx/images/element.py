"""Image element helpers for PowerPoint rendering."""

from typing import Any, Mapping, Optional, Sequence, Tuple

from ...rdf import ReportTask
from ...rdf.values import ImageValue
from ...tag import Tag
from ..base import PptElement
from ..units import units


class PptImageElement(PptElement):
    """Image and video handling for PowerPoint shapes."""

    def __init__(self, elem: Any, tags: Sequence[Tag]):
        super().__init__(elem)
        self.tags = tags
        self.type = "image"

    # the next two functions are a legacy but work
    # next step could a unification with the "template"-module(class) copyAndFill method
    def fillImage(self, tag: Tag, task: ReportTask) -> None:
        value = task.value
        if value.type == "file" and value.object.exists:
            tag.args["shape"] = True

            width, height, top, left = getSizeFrom(tag=tag, image=value.object, shape=self, units=units)
            slide = self.thing._parent._parent
            slide.shapes.add_picture(value.object.filename, top=top, left=left, width=width, height=height)
            delete_shape(self.thing)
        else:
            self.leaveAMissingNote(tag, str(value.object))

    def fillAnimation(self, tag: Tag, task: ReportTask) -> None:
        value = task.value
        value.load()
        actions = task.actions
        if value.type == "file" and value.object.exists:
            posterimage = actions.get("image:poster") or actions.get("image")

            tag.args["shape"] = True

            width, height, top, left = getSizeFrom(tag=tag, image=posterimage.object, shape=self, units=units)
            slide = self.thing._parent._parent
            slide.shapes.add_movie(
                movie_file=value.content,
                poster_frame_image=posterimage.object.filename,
                top=top,
                left=left,
                width=width,
                height=height,
            )
            delete_shape(self.thing)
        else:
            self.leaveAMissingNote(tag, str(value.object))



    def leaveAMissingNote(self, tag: Tag, note: str) -> None:
        shape = self.thing
        shape.text = note
        tag.burn()


def getSizeFrom(
    tag: Tag,
    image: ImageValue,
    shape: Optional[PptImageElement],
    units: Mapping[str, Any],
) -> Tuple[float, float, float, float]:
    """Extract the size from tag, shape or/and image if possible."""

    top = 0
    left = 0

    width = tag.getLength("width", units)
    height = tag.getLength("height", units)
    scale = tag.getFloat("scale")
    useshape = "shape" in tag.args

    if scale and (width or height):
        print(f"Image: {image!r} - ignore scale={scale:5.2f} since width or height is set")
        scale = None

    if useshape and (width or height):
        print(f"Image: {image!r} - ignore shape size since since width or height is set")
        shape = None
        useshape = False
    elif not useshape:
        shape = None
        useshape = False
    elif shape:
        thing = shape.thing
        shapew, shapeh = thing.width, thing.height
        shapet, shapel = thing.top, thing.left
    else:
        useshape = False

    image.content
    imagew, imageh = image.width, image.height
    imagew = units["pt"](imagew)
    imageh = units["pt"](imageh)
    ratio = imagew / imageh

    if scale:
        imagew = scale * imagew
        imageh = scale * imageh

    if useshape:
        top = shapet
        left = shapel
        sratio = shapew / shapeh
        if sratio > ratio:
            nshapew = shapew / sratio * ratio
            left += 0.5 * (shapew - nshapew)
            shapew = nshapew
        elif sratio < ratio:
            nshapeh = shapeh * sratio / ratio
            top += 0.5 * (shapeh - nshapeh)
            shapeh = nshapeh

    if not width and not height:
        if useshape:
            width = shapew
            height = shapeh
        else:
            width = imagew
            height = imageh
    elif width and not height:
        height = width / ratio
    elif height and not width:
        width = height * ratio

    return width, height, top, left


def delete_shape(shape: Any) -> None:
    """Remove the XML element for a shape."""

    shape_element = shape._element
    if shape_element.getparent() is not None:
        shape_element.getparent().remove(shape_element)
        shape_element._element = None
