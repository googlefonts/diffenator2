import tempfile
import pytest
import os
from io import BytesIO
from . import *


def test_download_google_fonts_family_to_file():
    from diffenator2.utils import download_google_fonts_family

    with tempfile.TemporaryDirectory() as tmp:
        family = download_google_fonts_family("Maven Pro", tmp)
        assert os.listdir(tmp)
    

def test_download_google_fonts_family_to_bytes():
    from diffenator2.utils import download_google_fonts_family
    family = download_google_fonts_family("Maven Pro")
    assert family
    for f in family:
        assert isinstance(f, BytesIO)


def test_download_google_fonts_family_not_existing():
    from diffenator2.utils import download_google_fonts_family
    with pytest.raises(ValueError):
        download_google_fonts_family("foobar2")


def test_download_latest_github_release():
    from diffenator2.utils import download_latest_github_release
    with tempfile.TemporaryDirectory() as tmp:
        files = download_latest_github_release(
            "googlefonts",
            "Gulzar",
            tmp,
            github_token=os.environ.get("GH_TOKEN")
        )
        assert len(files) != 0


def test_glyphs_in_string():
    from diffenator2.utils import characters_in_string

    assert characters_in_string("hello", set(["h", "e", "l", "o"]))
    assert not characters_in_string("hello", set(["e", "l", "o"]))


@pytest.mark.parametrize(
    """fp,pattern,expected""",
    [
        (mavenpro_vf, ".*", {'n', ' ', 't', 'a'}),
        (mavenpro_vf, "t|a", {"t", "a"}),
        (mavenpro_vf, "\W", {" "})
    ]
)
def test_re_filter_glyphs(fp, pattern, expected):
    from diffenator2.utils import re_filter_characters
    from diffenator2.font import DFont
    font = DFont(fp)
    assert re_filter_characters(font, pattern) == expected