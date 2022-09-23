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
from diffenator.shape import px_diff, test_words
import numpy as np
from diffenator.shape import test_fonts
from jinja2 import Environment, FileSystemLoader
from diffenator import html
from diffenator.font import DFont
import os
import shutil
from diffenator import jfont
from pkg_resources import resource_filename
import uharfbuzz as hb
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DiffFonts:
    def __init__(self, old_font: DFont, new_font: DFont):
        self.old_font = old_font
        self.new_font = new_font

    def diff_all(self):
        skip = frozenset(["diff_strings", "diff_all"])
        diff_funcs = [f for f in dir(self) if f.startswith("diff_") if f not in skip]
        for f in diff_funcs:
            eval(f"self.{f}()")

    def diff_tables(self):
        self.tables = jfont.Diff(self.old_font.jFont, self.new_font.jFont)

    def diff_fea(self):
        pass
        # TODO readd this!
        #        old_fea = self.old_font.glyph_combinator.ff.asFea()
        #        new_fea = self.new_font.glyph_combinator.ff.asFea()
        #        if old_fea != new_fea:
        #            self.features = HtmlDiff(wrapcolumn=80).make_file(
        #                old_fea.split("\n"),
        #                new_fea.split("\n"),
        #            )

    def diff_strings(self, fp):
        self.strings = test_words(fp, self.old_font, self.new_font, threshold=0.0)

    def diff_words(self):
        self.glyph_diff = test_fonts(self.old_font, self.new_font)
    
    def to_html(self, out):
        from diffenator.html2 import diffenator_report
        diffenator_report(self.diff, dst=out)


class Reporter:
    def __init__(self, diff: DiffFonts, pt_size=32):
        self.diff = diff
        self.pt_size = pt_size
        self.template_dir = resource_filename("diffenator", "templates")
        self.jinja = Environment(
            loader=FileSystemLoader(self.template_dir),
        )

    def save(self, fp: str):
        # create a dir which contains the html doc and fonts for easy distro
        if os.path.exists(fp):
            shutil.rmtree(fp)
        os.mkdir(fp)

        old_font_fp = os.path.join(fp, "before.ttf")
        new_font_fp = os.path.join(fp, "after.ttf")
        shutil.copyfile(self.diff.old_font.path, old_font_fp)
        shutil.copyfile(self.diff.new_font.path, new_font_fp)

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

        template = self.jinja.get_template("diffenator/diffenator.html")
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
