import pytest
import subprocess
import tempfile
import os
from fontTools.ttLib import TTFont
from . import *




@pytest.mark.parametrize(
    "fp, cmd",
    [
        (mavenpro_vf, ["diffenator2", "proof", mavenpro_vf, "--filter-styles", "Regular"]),
        (mavenpro_vf, ["diffenator2", "proof", mavenpro_vf, "--filter-styles", "Regular", "--imgs"]),
        (mavenpro_vf, ["diffenator2", "proof", mavenpro_vf, "--filter-styles=Medium|ExtraBold"]),
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
        subprocess.run(["diffenator2", "proof", fp, "--imgs", "-o", tmp_dir, "--filter-styles", ".*"], check=True)

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
        # There should be images for the text, glyphs and waterfall page
        assert len(imgs) == 3



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
        subprocess.run(["diffenator2", "diff", "-fb", fp_before, "-fa", fp_after, "-o", tmp_dir, "--filter-styles", ".*"])
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
        subprocess.run(
            ["diffenator2", "diff", "-fb", fp_before, "-fa", fp_after, "-o", tmp_dir, "-t", str(threshold), "--filter-styles", "Regular"])
        with open(os.path.join(tmp_dir, "MavenPro[wght].subset.mod-wght-400_0-diffenator.html"), "r", encoding="utf8") as doc:
            report = doc.read()
            for string in has:
                assert string in report
            
            for string in missing:
                assert string not in report


@pytest.mark.parametrize(
    "fp, cmd, pattern, has, missing",
    [
        (mavenpro_vf, "proof", ".*", ['>an tan</div>'], []),
        (mavenpro_vf, "proof", "[an]{1,2}", ['>an</div>'], []),
        (mavenpro_vf, "diff", ".*", ['>an tan</div>'], []),
        (mavenpro_vf, "diff", "[an]{1,2}", ['>an</div>'], []),
    ]
)
def test_diffbrowsers_filter_characters(fp, cmd, pattern, has, missing):
    with tempfile.TemporaryDirectory() as tmp_dir:
        if cmd == "proof":
            subprocess.run(["diffenator2", cmd, fp, "-c", pattern, "-o", tmp_dir, "--filter-styles", "Regular"])
        elif cmd == "diff":
            subprocess.run(["diffenator2", cmd, "-fb", fp, "-fa", fp, "-c", pattern, "-o", tmp_dir, "--filter-styles", "Regular"])

        with open(os.path.join(tmp_dir, "Regular-diffbrowsers_text.html"), "r", encoding="utf8") as doc:
            report = doc.read()
            for string in has:
                assert string in report
            
            for string in missing:
                assert string not in report


@pytest.mark.parametrize(
    "fp_before, fp_after, pattern, has, missing",
    [
        (mavenpro_vf, mavenpro_vf_mod, ".*", ["LATIN SMALL LETTER A"], []),
        (mavenpro_vf, mavenpro_vf_mod, "n|t", [], ["LATIN SMALL LETTER A"]),
    ]
)
def test_diffenator_filter_characters(fp_before, fp_after, pattern, has, missing):
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(["diffenator2", "diff", "-fb", fp_before, "-fa", fp_after, "-o", tmp_dir, "-ch", pattern, "--filter-styles", "Regular"])
        with open(os.path.join(tmp_dir, "MavenPro[wght].subset.mod-wght-400_0-diffenator.html"), "r", encoding="utf8") as doc:
            report = doc.read()
            for string in has:
                assert string in report

            for string in missing:
                assert string not in report

@pytest.mark.parametrize(
    "cmd",
    [
        ["diffenator2", "proof", mavenpro_vf],
        ["diffenator2", "diff", "-fb", mavenpro_vf, "-fa", mavenpro_vf_mod]
    ]
)
def test_user_templates(cmd):
    with tempfile.NamedTemporaryFile(suffix=".html") as doc, tempfile.TemporaryDirectory() as tmp_dir:
        doc.write("<p>Hello world</p>".encode("utf-8"))
        doc.seek(0)
        subprocess.run(cmd + ["--diffbrowsers-templates", doc.name, "-o", tmp_dir])
        html_filename = next(fp for fp in os.listdir(tmp_dir) if os.path.basename(doc.name) in fp)
        html_fp = os.path.join(tmp_dir, html_filename)
        assert html_fp
        with open(html_fp) as html:
            assert "<p>Hello world</p>" == html.read()
