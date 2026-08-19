"""Tests for :mod:`rdf.values.color_value`."""

import pytest

from _setup_values import *  # noqa: F401,F403 - ensure package import setup

from Scriptum.rdf.values.color_value import ColorValue


@pytest.mark.parametrize(
    "name, expected_hex, expected_rgb",
    [
        ("red", "FF0000", (255, 0, 0)),
        ("LightGray", "D3D3D3", (211, 211, 211)),
        ("aliceblue", "F0F8FF", (240, 248, 255)),
        ("RoyalBlue", "4169E1", (65, 105, 225)),
        ("#00ff00", "00FF00", (0, 255, 0)),
        ("0000ff", "0000FF", (0, 0, 255)),
    ],
)

def test_color_value_normalization(name, expected_hex, expected_rgb):
    color = ColorValue(name)

    assert color.content == expected_hex
    assert color.for_docx == expected_hex
    assert color.for_pptx == expected_rgb


@pytest.mark.parametrize("invalid", ["", "   ", "not-a-color", "#12345", "#1234567"])
def test_color_value_invalid_input(invalid):
    with pytest.raises(ValueError):
        ColorValue(invalid)
