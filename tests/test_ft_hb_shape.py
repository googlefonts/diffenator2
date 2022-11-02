from . import *
import pytest
from diffenator.ft_hb_shape import render_text
from diffenator.font import DFont


def test_variations():
    import numpy as np
    font = DFont(mavenpro_vf)
    reg_img = render_text(font, "a", fontSize=12)
    reg_arr = np.array(reg_img)

    font.set_variations({"wght": 700})
    bold_img = render_text(font, "a", fontSize=12)
    bold_arr = np.array(bold_img)
    assert reg_arr != bold_arr