import pytest
from tests import *
from diffenator2.html import CSSFontStyle


@pytest.mark.parametrize(
    "fp, expected",
    [
        (mavenpro_regular, CSSFontStyle("font", "style", {"wght": 400})),
        (mavenpro_extra_bold, CSSFontStyle("font", "style", {"wght": 800})),
        (mavenpro_black, CSSFontStyle("font", "style", {"wght": 900})),
    ]
)
def test_diffenator_font_style_static(fp, expected):
    from diffenator2.html import diffenator_font_style
    from diffenator2.font import DFont

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
    from diffenator2.html import diffenator_font_style
    from diffenator2.font import DFont

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
    from diffenator2.html import get_font_styles

    ttfonts = [TTFont(fp) for fp in fps]
    styles = get_font_styles(ttfonts, filters=filters)
    assert len(styles) == style_count


@pytest.mark.parametrize(
    "pages,expected",
    [
        (
            [
                os.path.join("waterfall.html"),
                os.path.join("text.html"),
            ],
            (
                "<p><a href='text.html'>text.html</a></p>\n",
                "<p><a href='waterfall.html'>waterfall.html</a></p>"
            ),
        ),
        (
            [
                os.path.join("foo", "bar", "waterfall.html"),
                os.path.join("cat", "baz", "fee", "text.html")
            ],
            (
                "<p><a href='cat/baz/fee/text.html'>cat/baz/fee/text.html</a></p>\n",
                "<p><a href='foo/bar/waterfall.html'>foo/bar/waterfall.html</a></p>"
            ),
        ),
    ]
)
def test_build_index_page(pages, expected):
    import tempfile
    from diffenator2.html import build_index_page
    with tempfile.TemporaryDirectory() as tmp:
        for path in pages:
            fp = os.path.join(tmp, path)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "w") as doc:
                doc.write("<p>Hello world</p>")
        build_index_page(tmp)
        result = os.path.join(tmp, "diffenator2-report.html")
        with open(result, "r") as doc:
            res = doc.read()
            assert res == "".join(expected)
