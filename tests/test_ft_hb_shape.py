from . import *
import pytest
from diffenator.ft_hb_shape import render_text
from diffenator.font import DFont
import numpy as np


def test_output():
    font = DFont(mavenpro_vf)
    img = render_text(font, "a", fontSize=12)
    # Image is currenty flipped vertically.
    arr = np.array(img)
    arr == np.array([[  0,   0,  33,  39,  11,   0],
       [  7, 191, 186, 155, 193,  95],
       [ 58, 177,   0,   0,  49, 174],
       [ 32, 213,  53,  37, 133, 180],
       [  0,  63, 156, 163, 146, 176],
       [  0,  18,   0,   0,  84, 161],
       [  0, 128, 196, 186, 219,  50],
       [  0,   0,   2,  17,   1,   0]], dtype=int)



def test_variations():
    font = DFont(mavenpro_vf)
    reg_img = render_text(font, "a", fontSize=12)
    reg_arr = np.array(reg_img)

    font.set_variations({"wght": 700})
    bold_img = render_text(font, "a", fontSize=12)
    bold_arr = np.array(bold_img)
    assert reg_arr != bold_arr