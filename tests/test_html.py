import pytest
from tests import *
from diffenator.html import CSSFontStyle


@pytest.mark.parametrize(
    "fp, expected",
    [
        (mavenpro_regular, CSSFontStyle("font", "style", {"wght": 400})),
        (mavenpro_extra_bold, CSSFontStyle("font", "style", {"wght": 800})),
        (mavenpro_black, CSSFontStyle("font", "style", {"wght": 900})),
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
        (mavenpro_vf, {}, CSSFontStyle("font", "style", {"wght": 400})),
        (mavenpro_vf, {"wght": 800}, CSSFontStyle("font", "style", {"wght": 800})),
        (mavenpro_vf, {"wght": 900}, CSSFontStyle("font", "style", {"wght": 900}))
    ]
)
def test_diffenator_font_style_vf(fp, coords, expected):
    from diffenator.html import diffenator_font_style
    from diffenator.font import DFont

    font = DFont(fp)
    font.set_variations(coords)
    assert diffenator_font_style(font) == expected


@pytest.mark.parametrize(
    "fps, filters, style_count",
    [
        ([mavenpro_vf], "Regular", 1),
        # SemiBold, Bold and ExtraBold
        ([mavenpro_vf], ".*Bold.*", 3),
        ([mavenpro_vf], "Regular|Black", 2),
        # Get all styles
        ([mavenpro_vf], None, 6),
        # Test static
        ([mavenpro_regular, mavenpro_extra_bold], [], 2),
        ([mavenpro_extra_bold], "Regular", 0),
        ([mavenpro_regular, mavenpro_extra_bold], "Regular", 1),
        ([mavenpro_regular, mavenpro_extra_bold], "Regular|.*", 2),
    ]
)
def test_get_font_style_filtering(fps, filters, style_count):
    from fontTools.ttLib import TTFont
    from diffenator.html import get_font_styles

    ttfonts = [TTFont(fp) for fp in fps]
    styles = get_font_styles(ttfonts, filters=filters)
    assert len(styles) == style_count
