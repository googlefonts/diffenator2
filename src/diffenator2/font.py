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
from itertools import product
from diffenator2.template_elements import CSSFontFace, CSSFontStyle
from diffenator2.utils import dict_coords_to_string
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Style:
    def __init__(self, font, name, coords):
        self.font = font
        self.name = name
        self.coords = coords
        self.css_font_style = CSSFontStyle(
            self.font.family_name,
            self.name,
            self.coords,
            self.font.suffix,
        )
    
    def set_font_variations(self):
        self.font.set_variations(self.coords)


def get_font_styles(fonts, method, filter_styles=None):
    results = []
    for font in fonts:
        for style in getattr(font, method)():
            if filter_styles and not re.match(filter_styles, style.name):
                    continue
            results.append(style)
    return results


class DFont:
    def __init__(self, path: str, font_size: int = 1000, suffix=""):
        self.path = path
        self.suffix = suffix
        self.ttFont: TTFont = TTFont(self.path, recalcTimestamp=False)
        self.family_name = self.ttFont["name"].getBestFamilyName()
        self.blackFont: BlackRendererFont = BlackRendererFont(path)
        self.ftFont: ft.Face = ft.Face(self.path)
        with open(path, "rb") as fontfile:
            fontdata = fontfile.read()
        self.hbFont: hb.Font = hb.Font(hb.Face(fontdata))
        self.jFont = jfont.TTJ(self.ttFont)

        self.css_font_face = CSSFontFace(self.ttFont, self.suffix)

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

    @lru_cache()
    def instances(self):
        results = []
        ttfont = self.ttFont
        name = ttfont["name"]
        if self.is_variable():
            instances = self.ttFont["fvar"].instances
            for inst in instances:
                inst_name = name.getName(inst.subfamilyNameID, 3, 1, 0x409)
                results.append(Style(self, inst_name.toUnicode(), inst.coordinates))
        else:
            results.append(
                Style(
                    self,
                    name.getBestSubFamilyName(),
                    {
                        "wght": ttfont["OS/2"].usWeightClass,
                    }                
                )
            )
        return sorted(results, key=lambda k: k.coords["wght"])
    
    def masters(self):
        pass
    
    def cross_product(self):
        assert self.is_variable(), "Needs to be a variable font"
        results = []
        axis_values = [
            (
                a.minValue,
                (a.minValue+a.maxValue)/2,
                a.maxValue
            ) for a in self.ttFont["fvar"].axes
        ]
        axis_tags = [a.axisTag for a in self.ttFont["fvar"].axes]

        cross = list(product(*axis_values))
        combinations = [dict(zip(axis_tags, c)) for c in cross]

        for coords in combinations:
            name = dict_coords_to_string(coords).replace(".", "_").replace(",", "_").replace("=", "-")
            results.append(Style(self, name, coords))
        return results

    def __repr__(self):
        return f"<DFont: {self.path}>"


def match_fonts(
    old_font: DFont, new_font: DFont, variations: dict = None, scale_upm: bool = True
):
    logger.info(
        f"Matching {os.path.basename(old_font.path)} to {os.path.basename(new_font.path)}"
    )
    if scale_upm and new_font.ttFont["head"].unitsPerEm != old_font.ttFont["head"].unitsPerEm:
        scale_upem(old_font.ttFont, new_font.ttFont["head"].unitsPerEm)

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
