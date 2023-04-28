from __future__ import annotations
from dataclasses import dataclass, field
import os

from fontTools.ttLib import TTFont
from jinja2 import pass_environment
import unicodedata2 as uni

from .utils import font_family_name


class Renderable:
    @pass_environment
    def render(self, jinja):
        classname = self.__class__.__name__
        template = jinja.get_template(f"{classname}.partial.html")
        return template.render(self.__dict__)

@dataclass
class WordDiff(Renderable):
    string: str
    hb_a: str
    hb_b: str
    ot_features: tuple
    lang: str
    direction: str
    changed_pixels: str

    def __hash__(self):
        return hash((self.string, self.hb_a, self.hb_b, self.ot_features))


@dataclass
class Glyph(Renderable):
    string: str
    name: str=None
    unicode: str=None

    def __post_init__(self):
        if self.name is None:
            try:
                self.name = uni.name(self.string)
            except Exception:
                self.name = ""
        if self.unicode is None:
            self.unicode = "U+%04X" % ord(self.string)

    def __hash__(self):
        return hash((self.string, self.name, self.unicode))


@dataclass
class GlyphDiff(Renderable):
    string: str
    changed_pixels: str
    diff_map: list[int]
    name: str=None
    unicode: str=None

    def __post_init__(self):
        if self.name is None:
            try:
                self.name = uni.name(self.string)
            except Exception:
                self.name = ""
        if self.unicode is None:
            self.unicode = "U+%04X" % ord(self.string)

    def __hash__(self):
        return hash((self.string, self.name, self.unicode))


@dataclass
class CSSFontStyle(Renderable):
    familyname: str
    stylename: str
    coords: dict
    suffix: str = ""

    def __post_init__(self):
        self.full_name = f"{self.familyname} {self.stylename}"
        self.font_variation_settings = ", ".join(f'"{k}" {v}' for k, v in self.coords.items())
        if self.suffix:
            self.cssfamilyname = f"{self.suffix} {self.familyname}"
            self.class_name = (
                f"{self.suffix} {self.stylename}".replace(" ", "-")
            )
        else:
            self.cssfamilyname = self.familyname
            self.class_name = f"{self.stylename}".replace(" ", "-")


@dataclass
class CSSFontFace(Renderable):
    ttfont: TTFont
    suffix: str = ""
    filename: str = field(init=False)
    familyname: str = field(init=False)
    classname: str = field(init=False)

    def __post_init__(self):
        ttf_filename = os.path.basename(self.ttfont.reader.file.name)
        if self.suffix:
            self.filename = f"{self.suffix}-{ttf_filename}"
        else:
            self.filename = ttf_filename
        self.cssfamilyname = font_family_name(self.ttfont, self.suffix)
        self.familyname = self.cssfamilyname
        self.stylename = self.ttfont["name"].getBestSubFamilyName()
        self.classname = self.cssfamilyname.replace(" ", "-")
        self.font_style = "normal" if "Italic" not in self.stylename else "italic"
        self.font_weight = self.ttfont["OS/2"].usWeightClass

        if "fvar" in self.ttfont:
            fvar = self.ttfont["fvar"]
            axes = {a.axisTag: a for a in fvar.axes}
            if "wght" in axes:
                min_weight = int(axes["wght"].minValue)
                max_weight = int(axes["wght"].maxValue)
                self.font_weight = f"{min_weight} {max_weight}"
            if "wdth" in axes:
                min_width = int(axes["wdth"].minValue)
                max_width = int(axes["wdth"].maxValue)
                self.font_stretch = f"{min_width}% {max_width}%"
            if "ital" in axes:
                pass
            if "slnt" in axes:
                min_angle = int(axes["slnt"].minValue)
                max_angle = int(axes["slnt"].maxValue)
                self.font_style = f"oblique {min_angle}deg {max_angle}deg"

    def __hash__(self):
        return hash((self.cssfamilyname, self.classname))
