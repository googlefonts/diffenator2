import pytest
from tests import *
from diffenator.html import CSSFontStyle


@pytest.mark.parametrize(
    "fp, expected",
    [
        (mavenpro_regular, CSSFontStyle("Maven Pro", "Regular", {"wght": 400})),
        (mavenpro_extra_bold, CSSFontStyle("Maven Pro", "ExtraBold", {"wght": 800})),
        (mavenpro_black, CSSFontStyle("Maven Pro", "Black", {"wght": 900})),
    ]
)
def test_diffenator_font_style_static(fp, expected):
    from diffenator.html import diffenator_font_style
    from diffenator.font import DFont

    font = DFont(fp)
    assert diffenator_font_style(font) == expected


@pytest.mark.parametrize(
    "fp, coords, expected",
    [
        (mavenpro_vf, {}, CSSFontStyle("Maven Pro", "Regular", {"wght": 400})),
        (mavenpro_vf, {"wght": 800}, CSSFontStyle("Maven Pro", "ExtraBold", {"wght": 800})),
        (mavenpro_vf, {"wght": 900}, CSSFontStyle("Maven Pro", "Black", {"wght": 900}))
    ]
)
def test_diffenator_font_style_vf(fp, coords, expected):
    from diffenator.html import diffenator_font_style
    from diffenator.font import DFont

    font = DFont(fp)
    font.set_variations(coords)
    assert diffenator_font_style(font) == expected

