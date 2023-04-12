import pytest
import subprocess
import tempfile
import os
from fontTools.ttLib import TTFont
from . import *



@pytest.mark.parametrize(
    "fp, cmd",
    [
        (mavenpro_vf, ["_diffbrowsers", "proof", mavenpro_vf]),
        (mavenpro_vf, ["_diffbrowsers", "proof", mavenpro_vf, "--imgs"]),
        (mavenpro_vf, ["_diffbrowsers", "proof", mavenpro_vf, "--filter-styles=Medium|ExtraBold"]),
    ]
)
def test_run_diffbrowsers_proof(fp, cmd):
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(cmd+["-o", tmp_dir], check=True)

        # check files are packaged
        assert any(f.endswith(".html") for f in os.listdir(tmp_dir))
        assert os.path.basename(fp) in os.listdir(tmp_dir)


@pytest.mark.parametrize(
    "fp",
    [
        (mavenpro_vf),
    ]
)
def test_run_diffbrowsers_proof_imgs(fp):
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(["_diffbrowsers", "proof", fp, "--imgs", "-o", tmp_dir], check=True)

        imgs, html = [], []
        # check images have been generated and there's an image for every html page
        for _, _, filenames in os.walk(tmp_dir):
            for f in filenames:
                if not f.endswith((".html", ".png", ".jpeg", "jpg")):
                    continue
                elif f.endswith(".html"):
                    html.append(f)
                else:
                    imgs.append(f)
        # There should at least be an image for each html page apart from the proofing page
        assert len(imgs) >= len(html)-1



# TODO test diffbrowsers diff


@pytest.mark.parametrize(
    "fp_before, fp_after",
    [
        (mavenpro_vf, mavenpro_vf_mod),
        (mavenpro_vf, mavenpro_extra_bold),
    ]
)
def test_diffenator(fp_before, fp_after):
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(["_diffenator", fp_before, fp_after, "-o", tmp_dir])
        new_font = f"old-{os.path.basename(fp_before)}"
        old_font = f"new-{os.path.basename(fp_after)}"
        assert new_font in os.listdir(tmp_dir)
        assert old_font in os.listdir(tmp_dir)
        assert any(f.endswith(".html") for f in os.listdir(tmp_dir))


@pytest.mark.parametrize(
    "fp_before, fp_after, threshold, has, missing",
    [
        # report will have modified "a" glyph
        (mavenpro_vf, mavenpro_vf_mod, 0.0001, ["LATIN SMALL LETTER A"], []),
        # report will not have modified "a" glyph
        (mavenpro_vf, mavenpro_vf_mod, 100.0, [], ["LATIN SMALL LETTER A"]),
    ]
)
def test_diffenator_threshold(fp_before, fp_after, threshold, has, missing):
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(["_diffenator", fp_before, fp_after, "-o", tmp_dir, "-t", str(threshold)])
        with open(os.path.join(tmp_dir, "diffenator.html"), "r", encoding="utf8") as doc:
            report = doc.read()
            for string in has:
                assert string in report
            
            for string in missing:
                assert string not in report


def test_assertion_no_styles_found():
    from diffenator2 import styles_in_fonts
    font = TTFont(mavenpro_vf)
    font["fvar"].instances = []
    with pytest.raises(Exception):
        styles_in_fonts([font])
