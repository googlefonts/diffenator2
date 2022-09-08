from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.ttLib.scaleUpem import scale_upem
import os
from diffenator import jfont
import uharfbuzz as hb
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DFont:
    def __init__(
        self, path: str, font_size: int = 1000
    ):
        self.path = path
        self.ttFont: TTFont = TTFont(self.path, recalcTimestamp=False)
        with open(path, "rb") as fontfile:
            fontdata = fontfile.read()
        self.hbFont: hb.Font = hb.Font(hb.Face(fontdata))
        self.jFont = jfont.TTJ(self.ttFont)

        self.font_size: int = font_size
        self.set_font_size(self.font_size)
    
    def is_variable(self):
        return "fvar" in self.ttFont

    def set_font_size(self, size: int):
        self.font_size = size

    def set_variations(self, coords: dict[str, float]):
        self.variation = coords
        self.ttFont = instantiateVariableFont(self.ttFont, coords)

    def set_variations_from_font(self, font: any):
        # Parse static font into a variations dict
        # TODO improve this
        coords = {"wght": font.ttFont["OS/2"].usWeightClass, "wdth": font.ttFont["OS/2"].usWidthClass}
        self.set_variations(coords)

    def __repr__(self):
        return f"<DFont: {self.path}>"


# Key feature of diffenator is to compare a static font against a VF instance.
# We need to retain this
def match_fonts(old_font: DFont, new_font: DFont, variations: dict = None, scale_upm: bool = True):
    logger.info(f"Matching {os.path.basename(old_font.path)} to {os.path.basename(new_font.path)}")
    # diffing fonts with different upms was in V1 so we should retain it.
    # previous implementation was rather messy. It is much easier to scale
    # the whole font
    if scale_upm:
        ratio = new_font.ttFont["head"].unitsPerEm / old_font.ttFont["head"].unitsPerEm
        if ratio != 1.0:
            # TODO use scaler in font tools
            scale_upem(old_font.ttFont, ratio)

    if old_font.is_variable() and new_font.is_variable():
        # todo allow user to specify coords
        return old_font, new_font
    elif not old_font.is_variable() and new_font.is_variable():
        new_font.set_variations_from_font(old_font)
    elif old_font.is_variable() and not new_font.is_variable():
        old_font.set_variations_from_font(new_font)
    return old_font, new_font

