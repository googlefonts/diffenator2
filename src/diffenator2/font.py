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
from diffenator2.masters import find_masters
from diffenator2.utils import dict_coords_to_string
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Style:
    def __init__(self, font, coords, name=None):
        self.font = font
        self.coords = coords
        if name:
            self.name = name
        else:
            self.name = self._make_name()
        self.css_font_style = CSSFontStyle(
            self.font.family_name,
            self.name,
            self.coords,
            self.font.suffix,
        )

    def _make_name(self):
        name = dict_coords_to_string(self.coords)
        return name.replace(".", "_").replace(",", "_").replace("=", "-")

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

        self.css_font_face = CSSFontFace(self.ttFont, self.suffix)

        self.font_size: int = font_size
        self.set_font_size(self.font_size)

    @property
    @lru_cache()
    def jFont(self):
        return jfont.TTJ(self.ttFont)

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
    
    def closest_style(self, coords):
        fvar_axes = {a.axisTag: (a.minValue, a.maxValue) for a in self.ttFont["fvar"].axes}
        found_coords = {}
        for axis, value in coords.items():
            if axis not in fvar_axes:
                continue
            if value >= fvar_axes[axis][0] and value <= fvar_axes[axis][1]:
                found_coords[axis] = value
            else:
                return None
        # TODO need to refactor this. Perhaps if no name is provided, the class will work it out
        return Style(self, found_coords)

    def set_variations_from_static_font(self, font: DFont):
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
                results.append(Style(self, inst.coordinates, inst_name.toUnicode()))
        else:
            results.append(
                Style(
                    self,
                    {"wght": ttfont["OS/2"].usWeightClass},
                    name.getBestSubFamilyName(),
                )
            )
        return results
    
    def masters(self):
        assert self.is_variable(), "Needs to be a variable font"
        results = []
        master_coords = find_masters(self.ttFont)
        for coords in master_coords:
            results.append(Style(self, coords))
        return results
    
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
            results.append(Style(self, coords))
        return results

    def __repr__(self):
        return f"<DFont: {self.path}>"
