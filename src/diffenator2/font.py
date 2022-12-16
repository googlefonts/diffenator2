from __future__ import annotations
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
import os
from diffenator2 import jfont
import uharfbuzz as hb
import logging
from blackrenderer.font import BlackRendererFont
import freetype as ft
from functools import lru_cache

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DFont:
    def __init__(self, path: str, font_size: int = 1000):
        self.path = path
        self.ttFont: TTFont = TTFont(self.path, recalcTimestamp=False)
        self.blackFont: BlackRendererFont = BlackRendererFont(path)
        self.ftFont: ft.Face = ft.Face(self.path)
        with open(path, "rb") as fontfile:
            fontdata = fontfile.read()
        self.hbFont: hb.Font = hb.Font(hb.Face(fontdata))
        self.jFont = jfont.TTJ(self.ttFont)

        self.font_size: int = font_size
        self.set_font_size(self.font_size)

    @lru_cache()
    def is_color(self):
        return any(t in ["SVG ", "COLR", "CBDT"] for t in self.ttFont.keys())

    def is_variable(self):
        return "fvar" in self.ttFont

    def set_font_size(self, size: int):
        self.font_size = size

    def set_variations(self, coords: dict[str, float]):
        if coords == {}:
            return
        # freetype-py's api uses a tuple/list
        ft_coords = [
            a.defaultValue if a.axisTag not in coords else coords[a.axisTag]
            for a in self.ttFont["fvar"].axes
        ]
        self.ftFont.set_var_design_coords(ft_coords)
        self.variations = coords
        self.hbFont.set_variations(coords)

    def set_variations_from_static_font(self, font: any):
        assert "fvar" not in font.ttFont, "Must be a static font"
        name_table = font.ttFont["name"]
        name_to_find = name_table.getBestSubFamilyName()
        for inst in self.ttFont["fvar"].instances:
            name_id = inst.subfamilyNameID
            inst_name = self.ttFont["name"].getName(name_id, 3, 1, 0x409).toUnicode()
            if inst_name == name_to_find:
                self.set_variations(inst.coordinates)
                return
        raise ValueError(f"{self} does not have an instance named {name_to_find}")

    def __repr__(self):
        return f"<DFont: {self.path}>"


def match_fonts(
    old_font: DFont, new_font: DFont, variations: dict = None, scale_upm: bool = True
):
    logger.info(
        f"Matching {os.path.basename(old_font.path)} to {os.path.basename(new_font.path)}"
    )
    if scale_upm:
        ratio = new_font.ttFont["head"].unitsPerEm / old_font.ttFont["head"].unitsPerEm
        if ratio != 1.0:
            scale_upem(old_font.ttFont, ratio)

    if variations and old_font.is_variable() and new_font.is_variable():
        old_font.set_variations(variations)
        new_font.set_variations(variations)
        return
    elif variations and any([not old_font.is_variable(), new_font.is_variable()]):
        logger.warn(
            f"Both fonts must be variable fonts in order to use the variations argument. "
            "Matching by stylename instead."
        )
    # Match VFs against statics
    if not old_font.is_variable() and new_font.is_variable():
        new_font.set_variations_from_static_font(old_font)
    elif old_font.is_variable() and not new_font.is_variable():
        old_font.set_variations_from_static_font(new_font)
