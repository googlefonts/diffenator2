import pytest
import subprocess
import tempfile
import os
from fontTools.ttLib import TTFont
from . import *



@pytest.mark.parametrize(
    "fp",
    [
        (mavenpro_vf),
    ]
)
def test_run_diffbrowsers_proof(fp):
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(["diffbrowsers", "proof", fp, "-o", tmp_dir], check=True)

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
        subprocess.run(["diffbrowsers", "proof", fp, "--imgs", "-o", tmp_dir], check=True)

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
        # There should at least be an image for each html page
        assert len(imgs) >= len(html)



# TODO test diffbrowsers diff


#@pytest.mark.parametrize(
#    "fp_before, fp_after",
#    [
#        (mavenpro_vf, mavenpro_vf_mod)
#    ]
#)
#def test_diffenator(fp_before, fp_after):
#    with tempfile.TemporaryDirectory() as tmp_dir:
#        subprocess.run(["diffenator", fp_before, fp_after, "-o", tmp_dir])
#        assert os.path.basename(fp_before) in os.listdir(tmp_dir)
#        assert os.path.basename(fp_after) in os.listdir(tmp_dir)
#