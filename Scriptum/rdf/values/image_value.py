#!/usr/bin/env python3
#
# part of:
#   S C R I P T U M 
#

# covers some image AND video processing tools
# for now avoid using opencv2 or similar

class ImageValue:
    """from task to content used in elements etc."""
    def __init__(self, filename: str, exists: bool):
        self.subtype = 'image' 
        self.filename = filename
        self.exists = exists
        self.width = -1
        self.height = -1
        self._parsed = None

    @property
    def content(self):
        if self.exists:
            if not self._parsed:
                # imported here, not at module level: parsing an .rdf that
                # places no images must not require Pillow, so that rdf stays
                # usable on its own.
                from PIL import Image

                self._parsed = content = Image.open(self.filename)
            else:
                content = self._parsed
            self.width, self.height = content.size
            
            return content
        else:
            return str(self)

    def __str__(self) -> str:
        if self.exists:
            return f'image from file: {self.filename!r}'
        else:
            return f'no file with image: {self.filename!r}'

    def __repr__(self) -> str:
        return f"{self.filename!r} exists: {self.exists} ({self.subtype})"

class AnimationValue(ImageValue):
    def __init__(self, filename: str, exists: bool):
        super().__init__(filename, exists)
        self.subtype = 'video' 

    @property
    def content(self):
        if self.exists:
            # video wont be opened to avoid dependency on cv2-module or others
            # we do use the poster image later instead!
            content = self.filename
            self.width, self.height = (-1,-1)
            
            return content
        else:
            return str(self)

    def __str__(self) -> str:
        if self.exists:
            return f'video from file: {self.filename!r}'
        else:
            return f'no file with video: {self.filename!r}'
 