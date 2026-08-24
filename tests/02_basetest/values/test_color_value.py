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


@pytest.mark.parametrize(
    "written, expected",
    [
        ("rgb(255,0,0)", "FF0000"),
        ("rgb(255, 0, 0)", "FF0000"),
        ("RGB( 0 , 128 , 255 )", "0080FF"),
        ("rgb(0,0,0)", "000000"),
    ],
)
def test_rgb_notation_is_normalised(written, expected):
    """Added because it is what people reach for, and it costs one pattern."""
    color = ColorValue(written)

    assert color.valid is True
    assert color.content == expected


@pytest.mark.parametrize("written", ["rgb(256,0,0)", "rgb(0,0,300)"])
def test_an_rgb_channel_out_of_range_is_refused_rather_than_clamped(written):
    """A clamped colour is a wrong colour nobody was told about."""
    assert ColorValue(written).valid is False


@pytest.mark.parametrize("written", ["rgb(255,0)", "rgb(1,2,3,4)", "rgb 1,2,3"])
def test_malformed_rgb_is_not_a_colour(written):
    assert ColorValue(written).valid is False


@pytest.mark.parametrize("written", ["#f00", "abc", "bad"])
def test_the_three_digit_shorthand_is_deliberately_not_accepted(written):
    """It would make any three hex-ish letters a colour -- 'bad' quietly
    becoming BBAADD -- so a typo would silently produce *a* colour rather than
    being reported. Since the YAML loader now reports an unrecognised colour
    instead of letting the black fallback stand, catching the typo is worth
    more than the shorthand, which writes out as 'ff0000' anyway."""
    assert ColorValue(written).valid is False
