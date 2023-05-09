import tempfile
import pytest
import os
from io import BytesIO


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