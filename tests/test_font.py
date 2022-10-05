import pytest
from . import *
from diffenator.font import match_fonts
from diffenator.font import DFont
from diffenator.html import diffenator_font_style


@pytest.mark.parametrize(
    "fp_before,fp_after,expected",
    [
        (mavenpro_regular, mavenpro_vf, {"wght": 400}),
        (mavenpro_extra_bold, mavenpro_vf, {"wght": 800}),
        (mavenpro_black, mavenpro_vf, {"wght": 900}),
    ]
)
def test_match_coordinates(fp_before, fp_after, expected):
    font_before = DFont(fp_before)
    font_after = DFont(fp_after)
    match_fonts(font_before, font_after)
    assert font_after.variations == expected
