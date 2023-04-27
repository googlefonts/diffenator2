from . import *
from diffenator2.matcher import FontMatcher
from diffenator2.font import DFont
import pytest


@pytest.mark.parametrize(
    """old_fps, new_fps, old_expected, new_expected""",
    [
        # Match VF against a VF
        (
            [mavenpro_vf],
            [mavenpro_vf],
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
                }
            ],
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
                }
            ],
        ),
        # Match VF against a static instance
        (
            [mavenpro_vf],
            [mavenpro_extra_bold, mavenpro_black],
            [
                {
                    "name": "ExtraBold",
                    "coords": {"wght": 800.0}
                }
            ],
            [
                {
                    "name": "ExtraBold",
                    "coords": {"wght": 800.0}
                }
            ],
        )
    ]
)
def test_match_instances(old_fps, new_fps, old_expected, new_expected):
    old_fonts = [DFont(f) for f in old_fps]
    new_fonts = [DFont(f) for f in new_fps]
    matcher = FontMatcher(old_fonts, new_fonts)
    matcher.instances()    

    assert len(matcher.old_styles) == len(matcher.new_styles)

    new_styles = {s.name: s for s in matcher.new_styles}
    for got in new_expected:
        new_style = new_styles.get(got["name"], None)
        assert new_style
        assert new_style.coords == got["coords"]

    old_styles = {s.name: s for s in matcher.old_styles}
    for got in old_expected:
        old_style = old_styles.get(got["name"], None)
        assert old_style
        assert old_style.coords == got["coords"]


@pytest.mark.parametrize(
    """old_fps,new_fps,old_expected,new_expected""",
    [
        (
            [mavenpro_original],
            [mavenpro_original],
            [
                {"coords": {"wght": 400.0}, "name": "wght-400_0"},
                {"coords": {"wght": 900.0}, "name": "wght-900_0"},
            ],
            [
                {"coords": {"wght": 400.0}, "name": "wght-400_0"},
                {"coords": {"wght": 900.0}, "name": "wght-900_0"},
            ],
        ),
        # Test two fonts which have different designspaces
        # We should only expect the wght axis
        (
            [commissioner_vf],
            [mavenpro_original],
            [
                {"coords": {"wght": 400.0}, "name": "wght-400_0"},
                {"coords": {"wght": 900.0}, "name": "wght-900_0"},
            ],
            [
                {"coords": {"wght": 400.0}, "name": "wght-400_0"},
                {"coords": {"wght": 900.0}, "name": "wght-900_0"},
            ],
        ),
    ]
)
def test_match_masters(old_fps, new_fps, old_expected, new_expected):
    old_fonts = [DFont(f) for f in old_fps]
    new_fonts = [DFont(f) for f in new_fps]
    matcher = FontMatcher(old_fonts, new_fonts)
    matcher.masters()
    
    assert len(matcher.old_styles) == len(matcher.new_styles)
    for got, want in zip(matcher.old_styles, old_expected):
        assert got.name == want["name"]
        assert got.coords == want["coords"]


@pytest.mark.parametrize(
    """old_fps,new_fps,old_expected,new_expected""",
    [
        (
            [mavenpro_original],
            [mavenpro_original],
            [
                {"coords": {"wght": 400.0}, "name": "wght-400_0"},
                {"coords": {"wght": 650.0}, "name": "wght-650_0"},
                {"coords": {"wght": 900.0}, "name": "wght-900_0"},
            ],
            [
                {"coords": {"wght": 400.0}, "name": "wght-400_0"},
                {"coords": {"wght": 650.0}, "name": "wght-650_0"},
                {"coords": {"wght": 900.0}, "name": "wght-900_0"},
            ],
        ),
        # Test two fonts which have different designspaces
        # We should only expect the wght axis
        (
            [commissioner_vf],
            [mavenpro_original],
            [
                {"coords": {"wght": 400.0}, "name": "wght-400_0"},
                {"coords": {"wght": 650.0}, "name": "wght-650_0"},
                {"coords": {"wght": 900.0}, "name": "wght-900_0"},
            ],
            [
                {"coords": {"wght": 400.0}, "name": "wght-400_0"},
                {"coords": {"wght": 650.0}, "name": "wght-650_0"},
                {"coords": {"wght": 900.0}, "name": "wght-900_0"},
            ],
        ),
    ]
)
def test_match_masters(old_fps, new_fps, old_expected, new_expected):
    old_fonts = [DFont(f) for f in old_fps]
    new_fonts = [DFont(f) for f in new_fps]
    matcher = FontMatcher(old_fonts, new_fonts)
    matcher.cross_product()
    
    assert len(matcher.old_styles) == len(matcher.new_styles)
    for got, want in zip(matcher.old_styles, old_expected):
        assert got.name == want["name"]
        assert got.coords == want["coords"]
    
    for got, want in zip(matcher.new_styles, new_expected):
        assert got.name == want["name"]
        assert got.coords == want["coords"]