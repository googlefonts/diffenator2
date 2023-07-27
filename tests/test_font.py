import pytest
from . import *
from itertools import combinations
from diffenator2.font import DFont
from diffenator2.html import diffenator_font_style
from diffenator2.matcher import FontMatcher


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
    matcher = FontMatcher([font_before], [font_after])
    matcher.instances()
    matcher.new_styles[0].set_font_variations()
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
        (
            kablammo_vf,
            [
                {
                    "name": "Zoink",
                    "coords": {"MORF": 0.0},
                },
                {
                    "name": "Bloop",
                    "coords": {'MORF': 20.0},
                },
                {
                    "name": "Splat",
                    "coords": {'MORF': 40.0},
                },
                {
                    "name": "Eek",
                    "coords": {'MORF': 60.0},
                },

            ]
        )
    ]
)
def test_instances(fp, expected):
    font = DFont(fp)
    font_instances = font.instances()
    assert len(font_instances) == len(expected)
    for got, want in zip(font_instances, expected):
        assert got.font == font
        assert got.name == want["name"]
        assert got.coords == want["coords"]


@pytest.mark.parametrize(
    """fp, expected""",
    [
        # VF with single axis, we expect 1^3
        (
            mavenpro_vf,
            3**1
        ),
        # VF with 4 axes, we expect 3^4
        (
            commissioner_vf,
            3**4
        )
    ]
)
def test_cross_product(fp, expected):
    font = DFont(fp)
    styles = font.cross_product()
    assert len(styles) == expected


@pytest.mark.parametrize(
        """fp, expected""",
        [
            (
                mavenpro_original,
                [
                    {
                        "name": "wght-400_0",
                        "coords": {"wght": 400.0},
                    },
                    {
                        "name": "wght-900_0",
                        "coords": {"wght": 900.0},
                    }
                ]
            ),
            (
                commissioner_vf,
                [
                    {'name': 'wght-100_0_slnt-0_0_FLAR-0_0_VOLM-0_0', 'coords': {'wght': 100.0, 'slnt': 0.0, 'FLAR': 0.0, 'VOLM': 0.0}},
                    {'name': 'wght-100_0_slnt-0_0_FLAR-0_0_VOLM-100_0', 'coords': {'wght': 100.0, 'slnt': 0.0, 'FLAR': 0.0, 'VOLM': 100.0}},
                    {'name': 'wght-100_0_slnt-0_0_FLAR-100_0_VOLM-0_0', 'coords': {'wght': 100.0, 'slnt': 0.0, 'FLAR': 100.0, 'VOLM': 0.0}},
                    {'name': 'wght-100_0_slnt-0_0_FLAR-100_0_VOLM-100_0', 'coords': {'wght': 100.0, 'slnt': 0.0, 'FLAR': 100.0, 'VOLM': 100.0}},
                    {'name': 'wght-100_0_slnt--12_0_FLAR-0_0_VOLM-0_0', 'coords': {'wght': 100.0, 'slnt': -12.0, 'FLAR': 0.0, 'VOLM': 0.0}},
                    {'name': 'wght-100_0_slnt--12_0_FLAR-0_0_VOLM-100_0', 'coords': {'wght': 100.0, 'slnt': -12.0, 'FLAR': 0.0, 'VOLM': 100.0}},
                    {'name': 'wght-100_0_slnt--12_0_FLAR-100_0_VOLM-0_0', 'coords': {'wght': 100.0, 'slnt': -12.0, 'FLAR': 100.0, 'VOLM': 0.0}},
                    {'name': 'wght-100_0_slnt--12_0_FLAR-100_0_VOLM-100_0', 'coords': {'wght': 100.0, 'slnt': -12.0, 'FLAR': 100.0, 'VOLM': 100.0}},
                    {'name': 'wght-554_99_slnt-0_0_FLAR-0_0_VOLM-0_0', 'coords': {'wght': 554.99, 'slnt': 0.0, 'FLAR': 0.0, 'VOLM': 0.0}},
                    {'name': 'wght-554_99_slnt-0_0_FLAR-0_0_VOLM-100_0', 'coords': {'wght': 554.99, 'slnt': 0.0, 'FLAR': 0.0, 'VOLM': 100.0}},
                    {'name': 'wght-554_99_slnt-0_0_FLAR-100_0_VOLM-0_0', 'coords': {'wght': 554.99, 'slnt': 0.0, 'FLAR': 100.0, 'VOLM': 0.0}},
                    {'name': 'wght-554_99_slnt-0_0_FLAR-100_0_VOLM-100_0', 'coords': {'wght': 554.99, 'slnt': 0.0, 'FLAR': 100.0, 'VOLM': 100.0}},
                    {'name': 'wght-554_99_slnt--12_0_FLAR-0_0_VOLM-0_0', 'coords': {'wght': 554.99, 'slnt': -12.0, 'FLAR': 0.0, 'VOLM': 0.0}},
                    {'name': 'wght-554_99_slnt--12_0_FLAR-0_0_VOLM-100_0', 'coords': {'wght': 554.99, 'slnt': -12.0, 'FLAR': 0.0, 'VOLM': 100.0}},
                    {'name': 'wght-554_99_slnt--12_0_FLAR-100_0_VOLM-0_0', 'coords': {'wght': 554.99, 'slnt': -12.0, 'FLAR': 100.0, 'VOLM': 0.0}},
                    {'name': 'wght-554_99_slnt--12_0_FLAR-100_0_VOLM-100_0', 'coords': {'wght': 554.99, 'slnt': -12.0, 'FLAR': 100.0, 'VOLM': 100.0}},
                    {'name': 'wght-900_0_slnt-0_0_FLAR-0_0_VOLM-0_0', 'coords': {'wght': 900.0, 'slnt': 0.0, 'FLAR': 0.0, 'VOLM': 0.0}},
                    {'name': 'wght-900_0_slnt-0_0_FLAR-0_0_VOLM-100_0', 'coords': {'wght': 900.0, 'slnt': 0.0, 'FLAR': 0.0, 'VOLM': 100.0}},
                    {'name': 'wght-900_0_slnt-0_0_FLAR-100_0_VOLM-0_0', 'coords': {'wght': 900.0, 'slnt': 0.0, 'FLAR': 100.0, 'VOLM': 0.0}},
                    {'name': 'wght-900_0_slnt-0_0_FLAR-100_0_VOLM-100_0', 'coords': {'wght': 900.0, 'slnt': 0.0, 'FLAR': 100.0, 'VOLM': 100.0}},
                    {'name': 'wght-900_0_slnt--12_0_FLAR-0_0_VOLM-0_0', 'coords': {'wght': 900.0, 'slnt': -12.0, 'FLAR': 0.0, 'VOLM': 0.0}},
                    {'name': 'wght-900_0_slnt--12_0_FLAR-0_0_VOLM-100_0', 'coords': {'wght': 900.0, 'slnt': -12.0, 'FLAR': 0.0, 'VOLM': 100.0}},
                    {'name': 'wght-900_0_slnt--12_0_FLAR-100_0_VOLM-0_0', 'coords': {'wght': 900.0, 'slnt': -12.0, 'FLAR': 100.0, 'VOLM': 0.0}},
                    {'name': 'wght-900_0_slnt--12_0_FLAR-100_0_VOLM-100_0', 'coords': {'wght': 900.0, 'slnt': -12.0, 'FLAR': 100.0, 'VOLM': 100.0}},
                ]
            )
        ]
)
def test_masters(fp, expected):
    font = DFont(fp)
    masters = font.masters()
    for got, want in zip(masters, expected):
        assert got.name == want["name"]
        assert got.coords == want["coords"]