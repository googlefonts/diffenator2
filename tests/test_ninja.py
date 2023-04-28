from . import *
import pytest
from diffenator2.font import DFont
import re



@pytest.mark.parametrize(
    """kwargs,expected_fp""",
    [
        # standard, just two fonts families
        (
            dict(
                fonts_before=[DFont(mavenpro_vf)],
                fonts_after=[DFont(mavenpro_vf_mod)],
            ),
            os.path.join(DATA_FP, "ninja_files", "diff-standard.txt")
        ),
        # include imgs
        (
            dict(
                fonts_before=[DFont(mavenpro_vf)],
                fonts_after=[DFont(mavenpro_vf_mod)],
                imgs=True,
            ),
            os.path.join(DATA_FP, "ninja_files", "diff-imgs.txt")
        ),
        # include filter-styles
        (
            dict(
                fonts_before=[DFont(mavenpro_vf)],
                fonts_after=[DFont(mavenpro_vf_mod)],
                imgs=True,
                filter_styles="Medium|ExtraBold"
            ),
            os.path.join(DATA_FP, "ninja_files", "diff-filter-styles.txt")
        ),
        # change threshold
        (
            dict(
                fonts_before=[DFont(mavenpro_vf)],
                fonts_after=[DFont(mavenpro_vf_mod)],
                threshold=0.01,
            ),
            os.path.join(DATA_FP, "ninja_files", "diff-threshold.txt")
        ),
    ]
)
def test_run_ninja_diff(kwargs, expected_fp):
    from diffenator2 import _ninja_diff

    _ninja_diff(**kwargs)

    with open(expected_fp) as expected, open("build.ninja") as current:
        exp = expected.read()
        cur = current.read()
        cur = re.sub(r"\S+/tests/data", "[SOMEDIRECTORY]/tests/data", cur)
        assert exp == cur


@pytest.mark.parametrize(
    """kwargs,expected_fp""",
    [
        # standard
        (
            dict(
                fonts=[DFont(mavenpro_vf)],
            ),
            os.path.join(DATA_FP, "ninja_files", "proof-standard.txt")
        ),
        # imgs
        (
            dict(
                fonts=[DFont(mavenpro_vf)],
                imgs=True,
            ),
            os.path.join(DATA_FP, "ninja_files", "proof-imgs.txt")
        ),
        # include filter_styles
        (
            dict(
                fonts=[DFont(mavenpro_vf)],
                imgs=True,
                filter_styles="Medium|Bold"
            ),
            os.path.join(DATA_FP, "ninja_files", "proof-filter-styles.txt")
        ),
    ]
)
def test_run_ninja_proof(kwargs, expected_fp):
    from diffenator2 import _ninja_proof

    _ninja_proof(**kwargs)
    with open(expected_fp) as expected, open("build.ninja") as current:
        exp = expected.read()
        cur = current.read()
        cur = re.sub(r"\S+/tests/data", "[SOMEDIRECTORY]/tests/data", cur)
        assert exp == cur
