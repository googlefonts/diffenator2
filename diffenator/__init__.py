"""
Diffenator is primarily a visual differ. Its main job is to stop users reporting visual issues to google/fonts.

What should be checked:

- Essential tables e.g OS/2, hhea attribs (Simon seemed keen on this so discuss implementation of this in the context of what I've found here)

Output:
- A single html page. No images, just pure html and js.
"""
from difflib import HtmlDiff
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from diffenator.shape import px_diff
import numpy as np
from diffenator.scale import scale_font
from diffenator.shape import test_fonts as test_shaping
from jinja2 import Environment, FileSystemLoader
from diffenator import html
import os
import shutil
from diffenator import jfont
from pkg_resources import resource_filename
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
            old_font.ttFont = scale_font(old_font.ttFont, ratio)

    if old_font.is_variable() and new_font.is_variable():
        # todo allow user to specify coords
        return old_font, new_font
    elif not old_font.is_variable() and new_font.is_variable():
        new_font.set_variations_from_font(old_font)
    elif old_font.is_variable() and not new_font.is_variable():
        old_font.set_variations_from_font(new_font)
    return old_font, new_font


class DiffFonts:
    def __init__(
        self, old_font: DFont, new_font: DFont, strings=None
    ):
        self.old_font = old_font
        self.new_font = new_font

        self.strings = strings
        self.build()

    def build(self):
        if self.strings:
            self.diffstrings = px_diff(self.old_font, self.new_font, self.strings)

        self.tables = jfont.Diff(self.old_font.jFont, self.new_font.jFont)

# TODO readd this!
#        old_fea = self.old_font.glyph_combinator.ff.asFea()
#        new_fea = self.new_font.glyph_combinator.ff.asFea()
#        if old_fea != new_fea:
#            self.features = HtmlDiff(wrapcolumn=80).make_file(
#                old_fea.split("\n"),
#                new_fea.split("\n"),
#            )
        
        self.glyph_diff = test_shaping(
            self.old_font,
            self.new_font,
        )


class Reporter:
    def __init__(self, diff: DiffFonts, pt_size=32):
        self.diff = diff
        self.pt_size = pt_size
        self.template_dir = resource_filename("diffenator", "templates")
        self.jinja = Environment(
            loader=FileSystemLoader(self.template_dir),
        )

    def save(self, fp: str, old_font: str, new_font: str):
        # create a dir which contains the html doc and fonts for easy distro
        if os.path.exists(fp):
            shutil.rmtree(fp)
        os.mkdir(fp)

        old_font_fp = os.path.join(fp, "before.ttf")
        new_font_fp = os.path.join(fp, "after.ttf")
        shutil.copyfile(old_font, old_font_fp)
        shutil.copyfile(new_font, new_font_fp)
        
        # TODO set more properties if VF
        old_css_font_face = html.CSSElement(
            "@font-face",
            font_family="before",
            src=f"url(before.ttf)",
        )
        old_css_font_class = html.CSSElement(
            "before",
            font_family="before",
        )

        new_css_font_face = html.CSSElement(
            "@font-face",
            font_family="after",
            src=f"url(after.ttf)",
        )
        new_css_font_class = html.CSSElement(
            "after",
            font_family="after",
        )

        template = self.jinja.get_template("report.html")
        doc = template.render(
            include_ui=True,
            pt_size=self.pt_size,
            diff=self.diff,
            css_font_faces_before=[old_css_font_face],
            css_font_faces_after=[new_css_font_face],
            css_font_classes_before=[old_css_font_class],
            css_font_classes_after=[new_css_font_class],
        )
        report_out = os.path.join(fp, "report.html")
        with open(report_out, "w") as f:
            logger.info(f"Saving {report_out}")
            f.write(doc)
