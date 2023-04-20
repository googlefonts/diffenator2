import pytest
from . import *
from itertools import combinations
from diffenator2.font import match_fonts
from diffenator2.font import DFont
from diffenator2.html import diffenator_font_style



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


@pytest.mark.parametrize(
    "fp, expected",
    [
        (
            mavenpro_vf,
            [
                {
                    "name": "Regular",
                    "coords": {"wght": 400.0}
                },
                {
                    "name": "Medium",
                    "coords": {"wght": 500.0}
                },
                {
                    "name": "SemiBold",
                    "coords": {"wght": 600.0}
                },
                {
                    "name": "Bold",
                    "coords": {"wght": 700.0}
                },
                {
                    "name": "ExtraBold",
                    "coords": {"wght": 800.0}
                },
                {
                    "name": "Black",
                    "coords": {"wght": 900.0}
                },
            ]
        ),
        (
            mavenpro_extra_bold,
            [
                {
                    "name": "ExtraBold",
                    "coords": {"wght": 800.0}
                },
            ]
        ),
    ]
)
def test_instances(fp, expected):
    font = DFont(fp)
    font_instances = font.instances()
    for got, want in zip(font_instances, expected):
        assert got.font == font
        assert got.name == want["name"]
        assert got.coords == want["coords"]


@pytest.mark.parametrize(
    """fp, expected""",
    [
        (
            mavenpro_vf,
            [
                {
                    "name": "wght-400_0",
                    "coords": {"wght": 400.0},
                },
                {
                    "name": "wght-650_0",
                    "coords": {"wght": 650.0},
                },
                {
                    "name": "wght-900_0",
                    "coords": {"wght": 900.0},
                },
            ]
        )
        # TODO add multi axis example
    ]
)
def test_cross_product(fp, expected):
    font = DFont(fp)
    styles = font.cross_product()
    for got, want in zip(styles, expected):
        assert got.name == want["name"]
        assert got.coords == want["coords"]