import tempfile
import pytest
import os
from io import BytesIO


def test_download_google_fonts_family_to_file():
    from diffenator.utils import download_google_fonts_family

    with tempfile.TemporaryDirectory() as tmp:
        family = download_google_fonts_family("Maven Pro", tmp)
        assert os.listdir(tmp)


def test_download_google_fonts_family_to_bytes():
    from diffenator.utils import download_google_fonts_family
    family = download_google_fonts_family("Maven Pro")
    assert family
    for f in family:
        assert isinstance(f, BytesIO)