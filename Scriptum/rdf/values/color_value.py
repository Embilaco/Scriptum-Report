#!/usr/bin/env python3
#
# part of:
#   S C R I P T U M 
#

"""Helper class to normalize color values for different backends."""

import re
from typing import Tuple


class ColorValue:
    """Normalize textual colors to values usable in python-docx/pptx."""

    #: Mapping of known color names to their RGB hex representation.
    #: The entries are aligned with the built-in colors exposed by both
    #: python-docx and python-pptx.  The hex value is always returned without
    #: the leading ``#`` to match the expectation of the respective libraries.
    COLOR_MAP = {
        "black": "000000",
        "white": "FFFFFF",
        "red": "FF0000",
        "green": "00FF00",
        "blue": "0000FF",
        "yellow": "FFFF00",
        "magenta": "FF00FF",
        "fuchsia": "FF00FF",
        "cyan": "00FFFF",
        "aqua": "00FFFF",
        "orange": "FFA500",
        "purple": "800080",
        "violet": "EE82EE",
        "pink": "FFC0CB",
        "brown": "A52A2A",
        "gray": "808080",
        "grey": "808080",
        "lightgray": "D3D3D3",
        "lightgrey": "D3D3D3",
        "darkgray": "A9A9A9",
        "darkgrey": "A9A9A9",
        "darkblue": "00008B",
        "navy": "000080",
        "teal": "008080",
        "olive": "808000",
        "maroon": "800000",
        "aliceblue": "F0F8FF",
        "antiquewhite": "FAEBD7",
        "aquamarine": "7FFFD4",
        "azure": "F0FFFF",
        "beige": "F5F5DC",
        "bisque": "FFE4C4",
        "blanchedalmond": "FFEBCD",
        "blueviolet": "8A2BE2",
        "burlywood": "DEB887",
        "cadetblue": "5F9EA0",
        "chartreuse": "7FFF00",
        "chocolate": "D2691E",
        "coral": "FF7F50",
        "cornflowerblue": "6495ED",
        "cornsilk": "FFF8DC",
        "crimson": "DC143C",
        "darkcyan": "008B8B",
        "darkgoldenrod": "B8860B",
        "darkgreen": "006400",
        "darkkhaki": "BDB76B",
        "darkmagenta": "8B008B",
        "darkolivegreen": "556B2F",
        "darkorange": "FF8C00",
        "darkorchid": "9932CC",
        "darkred": "8B0000",
        "darksalmon": "E9967A",
        "darkseagreen": "8FBC8F",
        "darkslateblue": "483D8B",
        "darkslategray": "2F4F4F",
        "darkslategrey": "2F4F4F",
        "darkturquoise": "00CED1",
        "darkviolet": "9400D3",
        "deeppink": "FF1493",
        "deepskyblue": "00BFFF",
        "dimgray": "696969",
        "dimgrey": "696969",
        "dodgerblue": "1E90FF",
        "firebrick": "B22222",
        "floralwhite": "FFFAF0",
        "forestgreen": "228B22",
        "gainsboro": "DCDCDC",
        "ghostwhite": "F8F8FF",
        "gold": "FFD700",
        "goldenrod": "DAA520",
        "greenyellow": "ADFF2F",
        "honeydew": "F0FFF0",
        "hotpink": "FF69B4",
        "indianred": "CD5C5C",
        "indigo": "4B0082",
        "ivory": "FFFFF0",
        "khaki": "F0E68C",
        "lavender": "E6E6FA",
        "lavenderblush": "FFF0F5",
        "lawngreen": "7CFC00",
        "lemonchiffon": "FFFACD",
        "lightblue": "ADD8E6",
        "lightcoral": "F08080",
        "lightcyan": "E0FFFF",
        "lightgoldenrodyellow": "FAFAD2",
        "lightgreen": "90EE90",
        "lightpink": "FFB6C1",
        "lightsalmon": "FFA07A",
        "lightseagreen": "20B2AA",
        "lightskyblue": "87CEFA",
        "lightslategray": "778899",
        "lightslategrey": "778899",
        "lightsteelblue": "B0C4DE",
        "lime": "00FF00",
        "limegreen": "32CD32",
        "linen": "FAF0E6",
        "mediumaquamarine": "66CDAA",
        "mediumblue": "0000CD",
        "mediumorchid": "BA55D3",
        "mediumpurple": "9370DB",
        "mediumseagreen": "3CB371",
        "mediumslateblue": "7B68EE",
        "mediumspringgreen": "00FA9A",
        "mediumturquoise": "48D1CC",
        "mediumvioletred": "C71585",
        "midnightblue": "191970",
        "mintcream": "F5FFFA",
        "mistyrose": "FFE4E1",
        "moccasin": "FFE4B5",
        "navajowhite": "FFDEAD",
        "oldlace": "FDF5E6",
        "orchid": "DA70D6",
        "palegoldenrod": "EEE8AA",
        "palegreen": "98FB98",
        "paleturquoise": "AFEEEE",
        "palevioletred": "DB7093",
        "papayawhip": "FFEFD5",
        "peachpuff": "FFDAB9",
        "peru": "CD853F",
        "plum": "DDA0DD",
        "powderblue": "B0E0E6",
        "rosybrown": "BC8F8F",
        "royalblue": "4169E1",
        "saddlebrown": "8B4513",
        "salmon": "FA8072",
        "sandybrown": "F4A460",
        "seagreen": "2E8B57",
        "seashell": "FFF5EE",
        "sienna": "A0522D",
        "silver": "C0C0C0",
        "skyblue": "87CEEB",
        "slateblue": "6A5ACD",
        "slategray": "708090",
        "slategrey": "708090",
        "snow": "FFFAFA",
        "springgreen": "00FF7F",
        "steelblue": "4682B4",
        "tan": "D2B48C",
        "thistle": "D8BFD8",
        "tomato": "FF6347",
        "turquoise": "40E0D0",
        "wheat": "F5DEB3",
        "whitesmoke": "F5F5F5",
        "yellowgreen": "9ACD32",
    }

    HEX_RE = re.compile(r"^#?(?P<hex>[0-9a-fA-F]{6})$")

    #: ``rgb(255, 0, 0)``, whitespace anywhere inside ignored.
    #:
    #: A channel outside 0-255 is refused rather than clamped: a clamped colour
    #: is a wrong colour nobody was told about.
    RGB_RE = re.compile(
        r"^rgb\(\s*(?P<r>\d{1,3})\s*,\s*(?P<g>\d{1,3})\s*,"
        r"\s*(?P<b>\d{1,3})\s*\)$"
    )

    # Deliberately NOT accepted: the three-digit shorthand '#f00'.
    #
    # It would make any three hex-ish letters a colour -- 'bad' quietly becomes
    # BBAADD, 'ace' AACCEE, '100' 110000 -- so a typo would silently produce
    # *a* colour instead of being reported. Since the YAML loader now reports
    # an unrecognised colour rather than letting the fallback stand, catching
    # the typo is worth more than the shorthand, which is cheap to write out
    # as 'ff0000'.

    #: Used when a colour cannot be understood. Every consumer still gets a
    #: usable RRGGBB string, because there is no way to write an explanatory
    #: sentence into a colour the way the other value types do.
    FALLBACK = "000000"

    def __init__(self, color):
        self._raw = color
        self._normalized = self._normalize(color)
        #: False when the input was not understood and FALLBACK is in use.
        self.valid = self._normalized is not None
        if not self.valid:
            self._normalized = self.FALLBACK

    # ------------------------------------------------------------------
    # exposed helpers
    @property
    def content(self) -> str:
        """Return the normalized color as ``RRGGBB`` string."""

        return self._normalized

    @property
    def for_docx(self) -> str:
        """Return the color representation used by python-docx.

        python-docx expects an RGB string without the leading ``#`` when
        setting colors via ``RGBColor.from_string``.  Returning the already
        normalized value allows the caller to directly forward it to that API.
        """

        return self._normalized

    @property
    def for_pptx(self) -> Tuple[int, int, int]:
        """Return an ``(r, g, b)`` tuple suitable for ``pptx.RGBColor``."""

        r = int(self._normalized[0:2], 16)
        g = int(self._normalized[2:4], 16)
        b = int(self._normalized[4:6], 16)
        return (r, g, b)

    # ------------------------------------------------------------------
    # helpers
    def _normalize(self, value):
        """Return the RRGGBB form, or None when *value* is not a colour."""

        if not isinstance(value, str) or not value.strip():
            return None

        candidate = value.strip().lower()

        if candidate in self.COLOR_MAP:
            return self.COLOR_MAP[candidate]

        match = self.HEX_RE.match(candidate)
        if match:
            return match.group("hex").upper()

        match = self.RGB_RE.match(candidate)
        if match:
            channels = [int(match.group(name)) for name in ('r', 'g', 'b')]
            if all(0 <= channel <= 255 for channel in channels):
                return '{:02X}{:02X}{:02X}'.format(*channels)
            return None

        return None

    # ------------------------------------------------------------------
    def __str__(self) -> str:
        if self.valid:
            return f"ColorValue({self._normalized})"
        return f"unknown color {self._raw!r}, using {self._normalized}"

    def __repr__(self) -> str:
        if self.valid:
            return f"color: {self._normalized} (raw={self._raw!r})"
        return f"color: {self._normalized} (raw={self._raw!r}, NOT RECOGNISED - fallback)"

    