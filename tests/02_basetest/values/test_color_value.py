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


@pytest.mark.parametrize("invalid", ["", "   ", "not-a-color", "#12345", "#1234567", None])
def test_color_value_invalid_input_degrades(invalid):
    """An unusable colour must not abort the run.

    Every other value type answers a bad input with a message that ends up
    in the document; a colour cannot carry a sentence, so it falls back to a
    usable value and reports itself as not valid instead of raising.
    """

    color = ColorValue(invalid)

    assert color.valid is False
    assert color.content == ColorValue.FALLBACK
    assert color.for_docx == ColorValue.FALLBACK
    assert color.for_pptx == (0, 0, 0)
    assert repr(invalid) in repr(color)


def test_color_value_reports_valid_input_as_valid():
    assert ColorValue("red").valid is True
